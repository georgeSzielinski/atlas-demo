import threading
from datetime import datetime, timedelta


# Single-flight guard so scheduled research cycles never overlap within one
# process (the fund cycle keeps its own separate lock).
_RESEARCH_LOCK = threading.Lock()

# Process-level generation attempt tracker: failed/refused generation is not
# retried until the configured interval has passed, so a misconfigured
# provider cannot trigger per-tick retry work. Injectable in tests.
_ATTEMPT_STATE = {"last_attempt_at": None}


class ResearchCycleEngine:
    """Deterministic autonomous research cycle orchestrator (composition only).

    One scheduled tick runs five stages, each reusing an existing engine
    unchanged:

      1. research_generation — WatchlistResearchEngine.generate() when
         recommendations are stale (per AUTO_RESEARCH_INTERVAL_MINUTES) and
         AUTO_RESEARCH_ENABLED is on. The engine's own gates still apply
         (real provider only, watchlist -> approved fallback).
      2. committee_evaluation — CommitteeEngine.evaluate() over the records
         stage 1 just produced. Runs ONLY when generation actually produced
         or refreshed records; when generation was skipped as fresh this
         stage is SKIPPED with the fixed reason below — identical records are
         never re-evaluated. Evaluations are persisted per run.
      3. paper_fund — LivePaperFundEngine.run_due_cycle(), byte-for-byte the
         same guarded call the scheduler made before this engine existed.
      4. performance_recording — read-only SelfLearningAnalyticsEngine
         snapshot over the live-fund evidence the cycle just produced,
         persisted per fund cycle. Runs only when stage 3 COMPLETED.
      5. self_improvement — read-only SelfImprovementEngine findings,
         persisted as advisory research evidence only. Runs only when
         stage 3 COMPLETED. Findings NEVER change trading behavior.

    Every stage reports status (COMPLETED | SKIPPED | NOT_EVALUATED | ERROR),
    reason, started_at, and duration_seconds. A failed research stage never
    blocks the fund stage, and a failed learning stage never fails the cycle.
    When any stage did work the whole cycle is persisted as one durable
    research_cycle_records row. Activity records are written only when a
    stage actually did work (with cycle_id=None so the fund's per-cycle
    pipeline derivation is never polluted). No LLM, no randomness, no broker,
    no real money; with AUTO_RESEARCH_ENABLED off stages 1-2 skip and the
    tick reduces to the guarded paper-fund tick plus its evidence recording.
    """

    VERSION = "research-cycle-v2"

    FRESH_SKIP_REASON = (
        "Recommendations are already fresh; committee evaluation unchanged."
    )
    CYCLE_IN_PROGRESS_REASON = "another research cycle is already running"

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def run_due_cycle(
        self,
        manager=None,
        now=None,
        research_engine=None,
        committee_engine=None,
        fund_engine=None,
        last_run_loader=None,
        record_loader=None,
        activity_writer=None,
        attempt_state=None,
        clock=None,
        settings_module=None,
        performance_engine=None,
        improvement_engine=None,
        committee_saver=None,
        performance_saver=None,
        improvement_saver=None,
        cycle_record_saver=None,
    ):
        moment = self._moment(now)
        clock = clock or datetime.now
        settings = settings_module or self._default_settings()
        attempt_state = attempt_state if attempt_state is not None else _ATTEMPT_STATE
        cycle_id = f"research-{moment.strftime('%Y%m%d%H%M%S')}"

        if not _RESEARCH_LOCK.acquire(blocking=False):
            return {
                "version": self.VERSION,
                "cycle_id": cycle_id,
                "generated_at": moment.isoformat(),
                "status": "SKIPPED",
                "reason": self.CYCLE_IN_PROGRESS_REASON,
                "stages": [],
                "fund": None,
                "policy": self.policy(),
            }

        try:
            generation_stage, generation_result = self._generation_stage(
                settings,
                moment,
                clock,
                research_engine,
                last_run_loader,
                activity_writer,
                attempt_state,
            )
            committee_stage = self._committee_stage(
                generation_stage,
                generation_result,
                moment,
                clock,
                committee_engine,
                record_loader,
                activity_writer,
                cycle_id,
                committee_saver,
            )
            fund_stage, fund_result = self._fund_stage(
                fund_engine, manager, moment, clock
            )
            performance_stage = self._performance_stage(
                fund_stage,
                fund_result,
                moment,
                clock,
                performance_engine,
                performance_saver,
            )
            improvement_stage = self._improvement_stage(
                fund_stage,
                fund_result,
                moment,
                clock,
                improvement_engine,
                improvement_saver,
            )

            stages = [
                generation_stage,
                committee_stage,
                fund_stage,
                performance_stage,
                improvement_stage,
            ]
            status = (
                "COMPLETED"
                if any(stage["status"] == "COMPLETED" for stage in stages)
                else "SKIPPED"
            )
            reason = None if status == "COMPLETED" else fund_stage.get("reason")

            result = {
                "version": self.VERSION,
                "cycle_id": cycle_id,
                "generated_at": moment.isoformat(),
                "status": status,
                "reason": reason,
                "stages": stages,
                "fund": fund_result,
                "policy": self.policy(),
            }
            if status == "COMPLETED":
                # One durable row per tick that did work: per-stage status,
                # reason, and duration — the persisted pipeline record.
                result["cycle_record_persisted"] = self._persist_cycle_record(
                    result, fund_result, cycle_record_saver
                )
            return result
        finally:
            _RESEARCH_LOCK.release()

    # ------------------------------------------------------------------
    # Stage 1: recommendation generation
    # ------------------------------------------------------------------
    def _generation_stage(
        self,
        settings,
        moment,
        clock,
        research_engine,
        last_run_loader,
        activity_writer,
        attempt_state,
    ):
        if not getattr(settings, "AUTO_RESEARCH_ENABLED", False):
            return self._stage(
                "research_generation",
                "SKIPPED",
                reason="automatic research is disabled",
            ), None

        interval = timedelta(
            minutes=int(getattr(settings, "AUTO_RESEARCH_INTERVAL_MINUTES", 1440))
        )

        last_run_time = self._last_run_time(last_run_loader)
        if last_run_time is not None and moment - last_run_time <= interval:
            return self._stage(
                "research_generation",
                "SKIPPED",
                reason=(
                    "recommendations are fresh "
                    f"(last run {last_run_time.isoformat()})"
                ),
                details={"fresh": True, "last_run_time": last_run_time.isoformat()},
            ), None

        # Failed/refused attempts retry on the (much shorter) retry cooldown,
        # not the full freshness interval, so a provider hiccup cannot silence
        # research for a whole day. Successful runs are handled by the
        # freshness gate above.
        retry_interval = timedelta(
            minutes=int(getattr(settings, "AUTO_RESEARCH_RETRY_MINUTES", 30))
        )
        retry_interval = min(retry_interval, interval)

        last_attempt = attempt_state.get("last_attempt_at")
        if last_attempt is not None and moment - last_attempt <= retry_interval:
            return self._stage(
                "research_generation",
                "SKIPPED",
                reason=(
                    "generation was attempted recently "
                    f"({last_attempt.isoformat()}); retrying after the "
                    "configured retry cooldown"
                ),
            ), None

        attempt_state["last_attempt_at"] = moment

        started_at = clock()
        try:
            engine = research_engine or self._default_research_engine()
            result = engine.generate(now=moment)
        except Exception as error:
            return self._stage(
                "research_generation",
                "ERROR",
                reason=f"Recommendation generation failed: {error}",
                started_at=started_at.isoformat(),
                duration_seconds=self._elapsed(started_at, clock),
            ), None

        duration = self._elapsed(started_at, clock)
        result = result if isinstance(result, dict) else {}
        status = result.get("status")
        count = int(result.get("recommendation_count") or 0)

        if status == "COMPLETED" and count > 0:
            self._activity(
                activity_writer,
                moment,
                "RECOMMENDATIONS_GENERATED",
                (
                    f"Autonomous research generated {count} recommendation "
                    f"record(s) (run {result.get('run_id')})."
                ),
                {
                    "run_id": result.get("run_id"),
                    "recommendation_count": count,
                    "tickers_analyzed": result.get("tickers_analyzed", []),
                    "skipped": result.get("skipped", []),
                    "provider": result.get("provider"),
                    "ticker_source": result.get("ticker_source"),
                    "duration_seconds": duration,
                },
            )
            return self._stage(
                "research_generation",
                "COMPLETED",
                started_at=started_at.isoformat(),
                duration_seconds=duration,
                details={
                    "run_id": result.get("run_id"),
                    "recommendation_count": count,
                    "tickers_analyzed": result.get("tickers_analyzed", []),
                    "skipped": result.get("skipped", []),
                    # Advisory evidence from the learning loop; research
                    # context only, never used to change actions or scores.
                    "learning_context": result.get("learning_context"),
                },
            ), result

        if status == "COMPLETED":
            reason = "generation completed but produced no recommendation records"
        else:
            reason = result.get("reason") or f"generation returned {status}"
        return self._stage(
            "research_generation",
            "NOT_EVALUATED",
            reason=reason,
            started_at=started_at.isoformat(),
            duration_seconds=duration,
        ), None

    # ------------------------------------------------------------------
    # Stage 2: committee evaluation
    # ------------------------------------------------------------------
    def _committee_stage(
        self,
        generation_stage,
        generation_result,
        moment,
        clock,
        committee_engine,
        record_loader,
        activity_writer,
        cycle_id=None,
        committee_saver=None,
    ):
        if generation_stage["status"] == "SKIPPED":
            if generation_stage.get("details", {}).get("fresh"):
                # Decision: identical records are never re-evaluated.
                return self._stage(
                    "committee_evaluation",
                    "SKIPPED",
                    reason=self.FRESH_SKIP_REASON,
                )
            return self._stage(
                "committee_evaluation",
                "SKIPPED",
                reason=generation_stage.get("reason"),
            )

        if generation_result is None:
            return self._stage(
                "committee_evaluation",
                "NOT_EVALUATED",
                reason=(
                    "No fresh recommendation records to evaluate: "
                    + (generation_stage.get("reason") or "generation did not complete.")
                ),
            )

        started_at = clock()
        try:
            engine = committee_engine or self._default_committee_engine()
            loader = record_loader or self._default_record_loader()
            evaluations = []
            for ticker in generation_result.get("tickers_analyzed", []):
                record = loader(ticker)
                if not record:
                    evaluations.append({
                        "ticker": ticker,
                        "status": "NOT_EVALUATED",
                        "reason": "no stored recommendation record found",
                    })
                    continue
                verdict = engine.evaluate(record)
                recommendation = verdict.get("committee_recommendation", {})
                evaluations.append({
                    "ticker": ticker,
                    "status": verdict.get("status"),
                    "action": recommendation.get("action"),
                    "strength": recommendation.get("strength"),
                    "agreement_pct": recommendation.get("agreement_pct"),
                    "confidence": recommendation.get("confidence"),
                })
        except Exception as error:
            return self._stage(
                "committee_evaluation",
                "ERROR",
                reason=f"Committee evaluation failed: {error}",
                started_at=started_at.isoformat(),
                duration_seconds=self._elapsed(started_at, clock),
            )

        duration = self._elapsed(started_at, clock)
        evaluated = [
            item for item in evaluations if item["status"] != "NOT_EVALUATED"
        ]
        if not evaluated:
            return self._stage(
                "committee_evaluation",
                "NOT_EVALUATED",
                reason="no stored recommendation records could be evaluated",
                started_at=started_at.isoformat(),
                duration_seconds=duration,
                details={"evaluations": evaluations},
            )

        self._activity(
            activity_writer,
            moment,
            "COMMITTEE_EVALUATED",
            (
                f"Investment committee evaluated {len(evaluated)} freshly "
                "generated recommendation record(s). Research only; no orders."
            ),
            {
                "evaluations": evaluations,
                "duration_seconds": duration,
            },
        )
        persisted = True
        try:
            saver = committee_saver or self._default_committee_saver()
            saver({
                "cycle_id": cycle_id,
                "run_id": generation_result.get("run_id"),
                "evaluated_at": moment.isoformat(),
                "evaluations": evaluations,
                "duration_seconds": duration,
            })
        except Exception:
            persisted = False
        return self._stage(
            "committee_evaluation",
            "COMPLETED",
            started_at=started_at.isoformat(),
            duration_seconds=duration,
            details={"evaluations": evaluations, "persisted": persisted},
        )

    # ------------------------------------------------------------------
    # Stage 3: paper fund (unchanged guarded call)
    # ------------------------------------------------------------------
    def _fund_stage(self, fund_engine, manager, moment, clock):
        started_at = clock()
        try:
            engine = fund_engine or self._default_fund_engine()
            result = engine.run_due_cycle(manager=manager, now=moment)
        except Exception as error:
            return self._stage(
                "paper_fund",
                "ERROR",
                reason=f"Paper fund tick failed: {error}",
                started_at=started_at.isoformat(),
                duration_seconds=self._elapsed(started_at, clock),
            ), None

        duration = self._elapsed(started_at, clock)
        result = result or {}
        if result.get("status") == "SKIPPED":
            status, reason = "SKIPPED", result.get("reason")
        elif result.get("cycle_status") == "COMPLETED":
            status, reason = "COMPLETED", None
        elif result.get("cycle_status") == "FAILED":
            status, reason = "ERROR", result.get("error")
        elif result.get("cycle_status") == "RECOVERING":
            # The cycle failed and the fund already re-armed itself for the
            # next scheduled retry. Report the real failure, not an unknown
            # shape, so the persisted tick record keeps WHY.
            status = "ERROR"
            reason = (
                f"{result.get('error') or 'paper fund cycle failed'} "
                "(automatic retry scheduled for "
                f"{result.get('next_update') or 'the next due tick'})"
            )
        else:
            status, reason = "NOT_EVALUATED", "fund tick returned an unknown shape"

        return self._stage(
            "paper_fund",
            status,
            reason=reason,
            started_at=started_at.isoformat(),
            duration_seconds=duration,
            details={"cycle_id": result.get("cycle_id")},
        ), result

    # ------------------------------------------------------------------
    # Stage 4: per-cycle performance recording (read-only measurement)
    # ------------------------------------------------------------------
    def _performance_stage(
        self,
        fund_stage,
        fund_result,
        moment,
        clock,
        performance_engine,
        performance_saver,
    ):
        if fund_stage.get("status") != "COMPLETED":
            return self._stage(
                "performance_recording",
                "SKIPPED",
                reason=(
                    "no completed paper-fund cycle this tick: "
                    + (fund_stage.get("reason") or fund_stage.get("status") or "")
                ),
            )

        started_at = clock()
        try:
            engine = performance_engine or self._default_performance_engine()
            report = engine.generate()
            saver = performance_saver or self._default_performance_saver()
            saver({
                "cycle_id": (fund_result or {}).get("cycle_id"),
                "as_of": moment.isoformat(),
                "report": report,
                "policy": report.get("policy", {}),
            })
        except Exception as error:
            return self._stage(
                "performance_recording",
                "ERROR",
                reason=f"Performance recording failed: {error}",
                started_at=started_at.isoformat(),
                duration_seconds=self._elapsed(started_at, clock),
            )

        return self._stage(
            "performance_recording",
            "COMPLETED",
            started_at=started_at.isoformat(),
            duration_seconds=self._elapsed(started_at, clock),
            details={"source_counts": report.get("source_counts", {})},
        )

    # ------------------------------------------------------------------
    # Stage 5: self-improvement findings (advisory research evidence only)
    # ------------------------------------------------------------------
    def _improvement_stage(
        self,
        fund_stage,
        fund_result,
        moment,
        clock,
        improvement_engine,
        improvement_saver,
    ):
        if fund_stage.get("status") != "COMPLETED":
            return self._stage(
                "self_improvement",
                "SKIPPED",
                reason=(
                    "no completed paper-fund cycle this tick: "
                    + (fund_stage.get("reason") or fund_stage.get("status") or "")
                ),
            )

        started_at = clock()
        try:
            engine = improvement_engine or self._default_improvement_engine()
            report = engine.generate()
            saver = improvement_saver or self._default_improvement_saver()
            saver(report, cycle_id=(fund_result or {}).get("cycle_id"))
        except Exception as error:
            return self._stage(
                "self_improvement",
                "ERROR",
                reason=f"Self-improvement recording failed: {error}",
                started_at=started_at.isoformat(),
                duration_seconds=self._elapsed(started_at, clock),
            )

        return self._stage(
            "self_improvement",
            "COMPLETED",
            started_at=started_at.isoformat(),
            duration_seconds=self._elapsed(started_at, clock),
            details={
                "report_status": report.get("status"),
                "findings": len(report.get("findings", [])),
                "opportunities": len(report.get("opportunities", [])),
                "research_only": True,
            },
        )

    # ------------------------------------------------------------------
    # Durable per-cycle pipeline record
    # ------------------------------------------------------------------
    def _persist_cycle_record(self, result, fund_result, cycle_record_saver):
        try:
            saver = cycle_record_saver or self._default_cycle_record_saver()
            saver({
                "cycle_id": result["cycle_id"],
                "generated_at": result["generated_at"],
                "status": result["status"],
                "reason": result["reason"],
                "stages": [
                    {
                        "stage": stage.get("stage"),
                        "status": stage.get("status"),
                        "reason": stage.get("reason"),
                        "started_at": stage.get("started_at"),
                        "duration_seconds": stage.get("duration_seconds"),
                    }
                    for stage in result["stages"]
                ],
                "fund_cycle_id": (fund_result or {}).get("cycle_id"),
                "policy": result["policy"],
            })
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Read-only status (for the API)
    # ------------------------------------------------------------------
    def status(self, settings_module=None, last_run_loader=None, now=None):
        settings = settings_module or self._default_settings()
        moment = self._moment(now)
        interval_minutes = int(
            getattr(settings, "AUTO_RESEARCH_INTERVAL_MINUTES", 1440)
        )
        last_run_time = self._last_run_time(last_run_loader)
        due = last_run_time is None or (
            moment - last_run_time > timedelta(minutes=interval_minutes)
        )
        return {
            "version": self.VERSION,
            "enabled": bool(getattr(settings, "AUTO_RESEARCH_ENABLED", False)),
            "interval_minutes": interval_minutes,
            "last_recommendation_run_time": (
                last_run_time.isoformat() if last_run_time else None
            ),
            "research_due": due,
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _stage(
        self,
        name,
        status,
        reason=None,
        started_at=None,
        duration_seconds=None,
        details=None,
    ):
        return {
            "stage": name,
            "status": status,
            "reason": reason,
            "started_at": started_at,
            "duration_seconds": duration_seconds,
            "details": details or {},
        }

    def _last_run_time(self, last_run_loader):
        try:
            if last_run_loader is not None:
                value = last_run_loader()
            else:
                from engines.history_engine import HistoryEngine

                runs = HistoryEngine().recent_runs(limit=1)
                value = runs[0].get("run_time") if runs else None
        except Exception:
            return None
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    def _activity(self, activity_writer, moment, activity_type, message, details):
        # cycle_id stays None so per-cycle fund pipeline derivations (backend
        # cycle_state, frontend pipeline meter) never anchor on research
        # entries.
        writer = activity_writer or self._default_activity_writer()
        writer({
            "at": moment.isoformat(),
            "cycle_id": None,
            "activity_type": activity_type,
            "message": message,
            "details": details,
        })

    def _elapsed(self, started_at, clock):
        try:
            return round(max(0.0, (clock() - started_at).total_seconds()), 3)
        except Exception:
            return None

    def _moment(self, now):
        if isinstance(now, datetime):
            return now
        if now:
            try:
                return datetime.fromisoformat(str(now))
            except ValueError:
                pass
        return datetime.now()

    # ------------------------------------------------------------------
    # Defaults (lazy imports; every collaborator injectable)
    # ------------------------------------------------------------------
    def _default_settings(self):
        from core import settings

        return settings

    def _default_research_engine(self):
        from engines.watchlist_research_engine import WatchlistResearchEngine

        return WatchlistResearchEngine()

    def _default_committee_engine(self):
        from engines.committee_engine import CommitteeEngine

        return CommitteeEngine()

    def _default_fund_engine(self):
        from engines.live_paper_fund_engine import LivePaperFundEngine

        return LivePaperFundEngine()

    def _default_record_loader(self):
        from database.repository import get_latest_recommendation_for_ticker

        return get_latest_recommendation_for_ticker

    def _default_activity_writer(self):
        from database.repository import add_paper_fund_activity

        return add_paper_fund_activity

    def _default_performance_engine(self):
        from engines.self_learning_analytics_engine import (
            SelfLearningAnalyticsEngine,
        )

        return SelfLearningAnalyticsEngine()

    def _default_improvement_engine(self):
        from engines.self_improvement_engine import SelfImprovementEngine

        return SelfImprovementEngine()

    def _default_committee_saver(self):
        from database.repository import save_committee_cycle_evaluations

        return save_committee_cycle_evaluations

    def _default_performance_saver(self):
        from database.repository import save_cycle_performance_record

        return save_cycle_performance_record

    def _default_improvement_saver(self):
        from database.repository import save_self_improvement_report

        return save_self_improvement_report

    def _default_cycle_record_saver(self):
        from database.repository import save_research_cycle_record

        return save_research_cycle_record

    def policy(self):
        return {
            "composition_only": True,
            "deterministic": True,
            "paper_only": True,
            "llm_decisions": False,
            "randomness": False,
            "broker_integration": False,
            "real_money": False,
            "reuses_existing_engines_only": True,
            "modifies_portfolio_construction": False,
            "modifies_risk_management": False,
            "modifies_learning": False,
            "modifies_fund_trading_behavior": False,
        }
