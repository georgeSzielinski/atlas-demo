from datetime import datetime


class ReliabilityEngine:
    """Deterministic, read-only measurement of Atlas' operational reliability.

    ReliabilityEngine does not observe Atlas directly. It composes the existing
    read-only OperationsEngine report (which already aggregates the scheduler,
    Market Data Manager, Live Paper Fund, database, and learning surfaces) plus
    read-only historical evidence (persisted ``runtime_states`` and
    ``market_data_snapshots``) into a single reliability picture. It owns no
    business logic of its own and never re-implements a subsystem.

    It is strictly observational and deterministic. It never writes to the
    database, never runs a scheduler tick or a paper-fund cycle, never changes
    recommendations, risk limits, portfolio construction, providers, or
    thresholds, and never connects a broker. Every collaborator is injectable so
    tests drive deterministic offline reports. Missing evidence is reported as
    ``NOT_EVALUATED`` with a reason and excluded from the weighted score by
    renormalizing the remaining weights; values are never fabricated and an
    unavailable subsystem is never scored as zero.
    """

    VERSION = "reliability-framework-v1"

    # Subsystems in deterministic order. Weights sum to 1.0 and are the base
    # weights before renormalization over the evaluated subsystems.
    SUBSYSTEMS = [
        "scheduler",
        "market_data",
        "provider",
        "database",
        "paper_fund",
        "api",
        "learning",
    ]
    DEFAULT_WEIGHTS = {
        "scheduler": 0.20,
        "market_data": 0.20,
        "provider": 0.15,
        "database": 0.15,
        "paper_fund": 0.15,
        "api": 0.10,
        "learning": 0.05,
    }

    # Deterministic incident penalties applied to a subsystem's 100 baseline.
    PENALTIES = {"WARNING": 10, "ERROR": 40, "CRITICAL": 60}
    SEVERITY_RANK = {"WARNING": 1, "ERROR": 2, "CRITICAL": 3}

    DEFAULT_THRESHOLDS = {
        "consecutive_failure_threshold": 3,
        "trend_min_samples": 4,
        "runtime_history_limit": 30,
        "market_history_limit": 30,
        "fund_activity_limit": 50,
    }

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def report(
        self,
        operations=None,
        runtime_history=None,
        market_history=None,
        fund_activity=None,
        now=None,
        weights=None,
        thresholds=None,
    ):
        moment = self._moment(now)
        weights = self._resolve_weights(weights)
        thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}

        ops = self._fetch(lambda: self._operations_report(operations))
        ops_report = ops["value"] if ops["ok"] else {}

        runtime_states = self._fetch(
            lambda: self._resolve_runtime_history(runtime_history, thresholds)
        )
        runtime_states = runtime_states["value"] if runtime_states["ok"] else []
        market_snaps = self._fetch(
            lambda: self._resolve_market_history(market_history, thresholds)
        )
        market_snaps = market_snaps["value"] if market_snaps["ok"] else []
        activity = self._fetch(
            lambda: self._resolve_fund_activity(fund_activity, thresholds)
        )
        activity = activity["value"] if activity["ok"] else []

        consecutive = self._consecutive_failures(activity)
        incidents = self._incidents(ops_report, activity, consecutive, thresholds)
        counts = self._incident_counts(incidents)

        subsystems = self._subsystem_reports(ops_report, incidents)
        overall, contributors = self._overall(subsystems, weights)

        availability = self._availability(runtime_states)
        trend = self._trend(runtime_states, thresholds)
        uptime = self._uptime(ops_report)
        confidence = self._confidence(subsystems, availability)
        recommendations = self._recommendations(
            overall, subsystems, incidents, consecutive, confidence, thresholds
        )

        return {
            "generated_at": moment.isoformat(),
            "version": self.VERSION,
            "overall_reliability": overall,
            "confidence": confidence,
            "subsystem_scores": {
                name: subsystems[name]["score"] for name in self.SUBSYSTEMS
            },
            "subsystem_weights": {name: weights[name] for name in self.SUBSYSTEMS},
            "contributors": contributors,
            "scheduler_reliability": subsystems["scheduler"],
            "market_data_reliability": self._enrich_market(
                subsystems["market_data"], market_snaps
            ),
            "provider_reliability": subsystems["provider"],
            "database_reliability": subsystems["database"],
            "paper_fund_reliability": subsystems["paper_fund"],
            "learning_reliability": subsystems["learning"],
            "api_reliability": subsystems["api"],
            "warning_count": counts["WARNING"],
            "error_count": counts["ERROR"],
            "critical_count": counts["CRITICAL"],
            "consecutive_failures": consecutive,
            "uptime": uptime,
            "availability": availability,
            "recent_incidents": incidents,
            "reliability_recommendations": recommendations,
            "reliability_trend": trend,
            "operational_policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Subsystem scoring
    # ------------------------------------------------------------------
    def _subsystem_reports(self, ops_report, incidents):
        scheduler = self._section(ops_report, "scheduler")
        market = self._section(ops_report, "market_data")
        database = self._section(ops_report, "database")
        fund = self._section(ops_report, "paper_fund")
        learning = self._section(ops_report, "learning")

        by_subsystem = {}
        for name in self.SUBSYSTEMS:
            by_subsystem[name] = [
                inc for inc in incidents if inc["subsystem"] == name
            ]

        reports = {}
        reports["scheduler"] = self._score_section(
            "scheduler", scheduler, by_subsystem["scheduler"]
        )
        reports["market_data"] = self._score_section(
            "market_data", market, by_subsystem["market_data"]
        )
        # Provider shares the market-data section (provider/fallback facet).
        reports["provider"] = self._score_section(
            "provider", market, by_subsystem["provider"]
        )
        reports["database"] = self._score_section(
            "database", database, by_subsystem["database"]
        )
        reports["paper_fund"] = self._score_section(
            "paper_fund", fund, by_subsystem["paper_fund"]
        )
        reports["learning"] = self._score_section(
            "learning", learning, by_subsystem["learning"]
        )
        reports["api"] = self._api_report(ops_report)
        return reports

    def _score_section(self, name, section, incidents):
        if section.get("status") != "EVALUATED":
            return self._not_evaluated_subsystem(
                name,
                section.get("reason")
                or f"The {name} operational section is unavailable.",
            )

        score = self._score_from_incidents(incidents)
        return {
            "status": "EVALUATED",
            "score": score,
            "grade": self._grade(score),
            "incident_count": len(incidents),
            "incidents": incidents,
            "reason": None,
        }

    def _api_report(self, ops_report):
        # API reliability is a telemetry-availability proxy: whether the
        # read-only operational surfaces resolve. It never invents request
        # metrics Atlas does not collect.
        if not ops_report or "overall_health" not in ops_report:
            return self._not_evaluated_subsystem(
                "api",
                "The operations report was unavailable, so API reliability "
                "cannot be evaluated.",
            )

        core = ["scheduler", "market_data", "paper_fund", "database", "learning"]
        unavailable = [
            name
            for name in core
            if self._section(ops_report, name).get("status") != "EVALUATED"
        ]
        score = max(0, 100 - 10 * len(unavailable))
        return {
            "status": "EVALUATED",
            "score": score,
            "grade": self._grade(score),
            "unavailable_sections": unavailable,
            "reason": None,
        }

    def _score_from_incidents(self, incidents):
        penalty = sum(self.PENALTIES.get(inc["severity"], 0) for inc in incidents)
        return max(0, 100 - penalty)

    def _not_evaluated_subsystem(self, name, reason):
        return {
            "status": "NOT_EVALUATED",
            "score": None,
            "grade": "NOT_EVALUATED",
            "reason": reason,
        }

    # ------------------------------------------------------------------
    # Overall score, grade, status, contributors
    # ------------------------------------------------------------------
    def _overall(self, subsystems, weights):
        evaluated = [
            name
            for name in self.SUBSYSTEMS
            if subsystems[name]["status"] == "EVALUATED"
        ]
        total_weight = sum(weights[name] for name in evaluated)

        contributors = []
        if not evaluated or total_weight <= 0:
            for name in self.SUBSYSTEMS:
                contributors.append({
                    "subsystem": name,
                    "score": subsystems[name]["score"],
                    "weight": 0.0,
                    "base_weight": weights[name],
                    "impact": None,
                    "excluded": True,
                })
            overall = {
                "score": None,
                "grade": "NOT_EVALUATED",
                "status": "NOT_EVALUATED",
                "reason": "No subsystem had enough evidence to be evaluated.",
                "evaluated_subsystems": 0,
                "total_subsystems": len(self.SUBSYSTEMS),
            }
            return overall, contributors

        raw = 0.0
        for name in self.SUBSYSTEMS:
            subsystem = subsystems[name]
            if subsystem["status"] != "EVALUATED":
                contributors.append({
                    "subsystem": name,
                    "score": None,
                    "weight": 0.0,
                    "base_weight": weights[name],
                    "impact": None,
                    "excluded": True,
                })
                continue
            normalized = weights[name] / total_weight
            impact = normalized * (subsystem["score"] - 100)
            raw += normalized * subsystem["score"]
            contributors.append({
                "subsystem": name,
                "score": subsystem["score"],
                "weight": round(normalized, 4),
                "base_weight": weights[name],
                "impact": round(impact, 1),
                "excluded": False,
            })

        score = int(round(raw))
        score = max(0, min(100, score))
        overall = {
            "score": score,
            "grade": self._grade(score),
            "status": self._status(score),
            "evaluated_subsystems": len(evaluated),
            "total_subsystems": len(self.SUBSYSTEMS),
        }
        return overall, contributors

    def _grade(self, score):
        if score is None:
            return "NOT_EVALUATED"
        bands = [
            (98, "A+"),
            (93, "A"),
            (90, "A-"),
            (87, "B+"),
            (83, "B"),
            (80, "B-"),
            (77, "C+"),
            (73, "C"),
            (70, "C-"),
            (67, "D+"),
            (63, "D"),
            (60, "D-"),
        ]
        for threshold, grade in bands:
            if score >= threshold:
                return grade
        return "F"

    def _status(self, score):
        if score is None:
            return "NOT_EVALUATED"
        if score >= 90:
            return "Reliable"
        if score >= 75:
            return "Watch"
        if score >= 50:
            return "Degraded"
        return "Critical"

    # ------------------------------------------------------------------
    # Incident model
    # ------------------------------------------------------------------
    def _incidents(self, ops_report, activity, consecutive, thresholds):
        incidents = []

        scheduler = self._section(ops_report, "scheduler")
        if scheduler.get("status") == "EVALUATED":
            error_count = scheduler.get("error_count") or 0
            if error_count:
                self._add(
                    incidents,
                    "scheduler",
                    "ERROR",
                    f"{error_count} scheduler tick error(s) recorded.",
                    scheduler.get("last_error_at"),
                    "scheduler",
                )

        market = self._section(ops_report, "market_data")
        if market.get("status") == "EVALUATED":
            if market.get("last_error"):
                self._add(
                    incidents,
                    "market_data",
                    "ERROR",
                    str(market.get("last_error")),
                    None,
                    "market_data",
                )
            if market.get("healthy") is False:
                self._add(
                    incidents,
                    "market_data",
                    "ERROR",
                    "Market data provider reported unhealthy.",
                    None,
                    "market_data",
                )
            if market.get("validated") is False:
                self._add(
                    incidents,
                    "market_data",
                    "WARNING",
                    "Latest market prices are not validated.",
                    None,
                    "market_data",
                )
            if (market.get("data_freshness") or {}).get("is_stale"):
                self._add(
                    incidents,
                    "market_data",
                    "WARNING",
                    "Market data cache is stale.",
                    None,
                    "market_data",
                )
            if market.get("fallback_used"):
                self._add(
                    incidents,
                    "provider",
                    "WARNING",
                    "Market data fell back to a non-primary provider.",
                    None,
                    "provider",
                )

        database = self._section(ops_report, "database")
        if database.get("status") == "EVALUATED" and database.get("exists") is False:
            self._add(
                incidents,
                "database",
                "CRITICAL",
                "Application database file is missing.",
                None,
                "database",
            )

        fund = self._section(ops_report, "paper_fund")
        if fund.get("status") == "EVALUATED":
            if fund.get("fund_status") == "ERROR":
                self._add(
                    incidents,
                    "paper_fund",
                    "CRITICAL",
                    fund.get("last_error")
                    or "Live paper fund is in an ERROR state.",
                    fund.get("last_update"),
                    "paper_fund",
                )
            elif fund.get("last_error"):
                self._add(
                    incidents,
                    "paper_fund",
                    "ERROR",
                    str(fund.get("last_error")),
                    fund.get("last_update"),
                    "paper_fund",
                )

        for entry in activity:
            if entry.get("activity_type") == "CYCLE_FAILED":
                self._add(
                    incidents,
                    "paper_fund",
                    "ERROR",
                    entry.get("message") or "Paper fund cycle failed.",
                    entry.get("at"),
                    "paper_fund_activity",
                )

        if consecutive["status"] == "EVALUATED":
            threshold = thresholds["consecutive_failure_threshold"]
            if consecutive["count"] >= threshold:
                self._add(
                    incidents,
                    "paper_fund",
                    "CRITICAL",
                    f"{consecutive['count']} consecutive paper-fund cycle "
                    "failures recorded.",
                    None,
                    "paper_fund_activity",
                )

        return self._dedupe(incidents)

    def _add(self, incidents, subsystem, severity, message, at, source):
        incidents.append({
            "subsystem": subsystem,
            "severity": severity,
            "message": message,
            "at": at,
            "source": source,
        })

    def _dedupe(self, incidents):
        # Keep the most severe incident per (subsystem, message), then order
        # deterministically by subsystem, descending severity, and message.
        best = {}
        for incident in incidents:
            key = (incident["subsystem"], incident["message"])
            current = best.get(key)
            if current is None or (
                self.SEVERITY_RANK[incident["severity"]]
                > self.SEVERITY_RANK[current["severity"]]
            ):
                best[key] = incident

        order = {name: index for index, name in enumerate(self.SUBSYSTEMS)}
        return sorted(
            best.values(),
            key=lambda inc: (
                order.get(inc["subsystem"], len(order)),
                -self.SEVERITY_RANK[inc["severity"]],
                inc["message"],
            ),
        )

    def _incident_counts(self, incidents):
        counts = {"WARNING": 0, "ERROR": 0, "CRITICAL": 0}
        for incident in incidents:
            counts[incident["severity"]] += 1
        return counts

    # ------------------------------------------------------------------
    # Degradation model: consecutive failures, availability, trend, uptime
    # ------------------------------------------------------------------
    def _consecutive_failures(self, activity):
        terminal = [
            entry.get("activity_type")
            for entry in activity
            if entry.get("activity_type") in {"CYCLE_COMPLETED", "CYCLE_FAILED"}
        ]
        if not terminal:
            return {
                "status": "NOT_EVALUATED",
                "count": None,
                "reason": "No completed or failed paper-fund cycles are recorded.",
            }

        count = 0
        for activity_type in terminal:  # activity is newest-first
            if activity_type == "CYCLE_FAILED":
                count += 1
            else:
                break
        return {"status": "EVALUATED", "count": count}

    def _availability(self, runtime_states):
        if not runtime_states:
            return {
                "status": "NOT_EVALUATED",
                "availability_percent": None,
                "reason": "No runtime state history is available.",
            }

        up = sum(1 for state in runtime_states if self._state_up(state))
        total = len(runtime_states)
        return {
            "status": "EVALUATED",
            "availability_percent": round(up / total * 100, 2),
            "states_sampled": total,
            "up_states": up,
        }

    def _state_up(self, state):
        if str(state.get("current_state")) == "ERROR":
            return False
        health = state.get("health") or {}
        if str(health.get("status")) == "Offline":
            return False
        return True

    def _trend(self, runtime_states, thresholds):
        minimum = thresholds["trend_min_samples"]
        if len(runtime_states) < minimum:
            return {
                "status": "NOT_EVALUATED",
                "direction": None,
                "reason": (
                    "At least "
                    f"{minimum} runtime state samples are required to measure a "
                    "reliability trend."
                ),
            }

        half = len(runtime_states) // 2
        recent = runtime_states[:half]  # newest-first, so this is the recent window
        older = runtime_states[half:2 * half]
        recent_ratio = self._up_ratio(recent)
        older_ratio = self._up_ratio(older)

        if recent_ratio > older_ratio:
            direction = "IMPROVING"
        elif recent_ratio < older_ratio:
            direction = "DEGRADING"
        else:
            direction = "STABLE"

        return {
            "status": "EVALUATED",
            "direction": direction,
            "recent_up_ratio": round(recent_ratio, 4),
            "older_up_ratio": round(older_ratio, 4),
            "samples": 2 * half,
        }

    def _up_ratio(self, states):
        if not states:
            return 0.0
        return sum(1 for state in states if self._state_up(state)) / len(states)

    def _uptime(self, ops_report):
        section = self._section(ops_report, "uptime")
        if section.get("status") in {"EVALUATED", "NOT_STARTED"}:
            return section
        return {
            "status": "NOT_EVALUATED",
            "reason": section.get("reason")
            or "Uptime is unavailable because the operations report is missing.",
        }

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------
    def _confidence(self, subsystems, availability):
        evaluated = [
            name
            for name in self.SUBSYSTEMS
            if subsystems[name]["status"] == "EVALUATED"
        ]
        total = len(self.SUBSYSTEMS)
        coverage = len(evaluated) / total if total else 0
        history_available = availability.get("status") == "EVALUATED"

        if not evaluated:
            level = "LOW"
            reason = "No subsystem telemetry was available."
        elif coverage >= 0.85 and history_available:
            level = "HIGH"
            reason = (
                "Nearly all subsystems reported and runtime history is available."
            )
        elif coverage >= 0.5:
            level = "MEDIUM"
            reason = (
                "Most subsystems reported, but historical telemetry is limited."
                if not history_available
                else "Most subsystems reported."
            )
        else:
            level = "LOW"
            reason = "Only a minority of subsystems reported telemetry."

        return {
            "level": level,
            "reason": reason,
            "coverage": f"{len(evaluated)}/{total}",
            "history_available": history_available,
        }

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------
    def _recommendations(
        self, overall, subsystems, incidents, consecutive, confidence, thresholds
    ):
        recommendations = []

        if any(inc["severity"] == "CRITICAL" for inc in incidents):
            recommendations.append(
                "Investigate critical reliability incidents immediately "
                "(see recent_incidents)."
            )

        fund = subsystems["paper_fund"]
        if fund.get("status") == "EVALUATED" and any(
            inc["subsystem"] == "paper_fund" and inc["severity"] == "CRITICAL"
            for inc in incidents
        ):
            recommendations.append(
                "Investigate and resume the live paper fund after resolving the "
                "underlying error."
            )

        if (
            consecutive["status"] == "EVALUATED"
            and consecutive["count"] >= thresholds["consecutive_failure_threshold"]
        ):
            recommendations.append(
                "Halt automatic paper-fund cycles until the failure streak is "
                "resolved."
            )

        if any(
            inc["subsystem"] == "provider" for inc in incidents
        ):
            recommendations.append(
                "Configure a validated real market data provider to reduce "
                "fallback reliance."
            )

        if any(
            inc["subsystem"] == "market_data" and inc["severity"] == "WARNING"
            for inc in incidents
        ):
            recommendations.append(
                "Refresh market data; latest prices are stale or unvalidated."
            )

        if any(
            inc["subsystem"] == "scheduler" for inc in incidents
        ):
            recommendations.append(
                "Review recorded scheduler tick errors (see recent_incidents)."
            )

        unavailable = [
            name
            for name in self.SUBSYSTEMS
            if subsystems[name]["status"] != "EVALUATED"
        ]
        if unavailable:
            recommendations.append(
                "Restore reliability telemetry for: " + ", ".join(unavailable) + "."
            )

        if confidence["level"] == "LOW":
            recommendations.append(
                "Reliability confidence is LOW; more subsystem telemetry and "
                "runtime history are required for a trustworthy score."
            )

        if not recommendations and overall.get("status") == "Reliable":
            recommendations.append("No reliability action required.")

        return recommendations

    # ------------------------------------------------------------------
    # Enrichment (uses injected market history without fabricating values)
    # ------------------------------------------------------------------
    def _enrich_market(self, market_section, market_snaps):
        section = dict(market_section)
        if not market_snaps:
            section["historical_validation"] = {
                "status": "NOT_EVALUATED",
                "reason": "No market data snapshot history is available.",
            }
            return section

        validated = sum(1 for snap in market_snaps if snap.get("validated"))
        fallbacks = sum(1 for snap in market_snaps if snap.get("fallback_used"))
        total = len(market_snaps)
        section["historical_validation"] = {
            "status": "EVALUATED",
            "validated_rate": round(validated / total * 100, 2),
            "fallback_rate": round(fallbacks / total * 100, 2),
            "snapshots_sampled": total,
        }
        return section

    # ------------------------------------------------------------------
    # Collaborator resolution (lazy imports; each read-only)
    # ------------------------------------------------------------------
    def _operations_report(self, operations):
        if operations is None:
            from engines.operations_engine import OperationsEngine

            return OperationsEngine().report()
        if isinstance(operations, dict):
            return operations
        report = getattr(operations, "report", None)
        if callable(report):
            return report()
        return {}

    def _resolve_runtime_history(self, runtime_history, thresholds):
        if runtime_history is not None:
            return list(runtime_history)
        from database.repository import get_runtime_states

        return get_runtime_states(limit=thresholds["runtime_history_limit"])

    def _resolve_market_history(self, market_history, thresholds):
        if market_history is not None:
            return list(market_history)
        from database.repository import get_market_data_snapshots

        return get_market_data_snapshots(limit=thresholds["market_history_limit"])

    def _resolve_fund_activity(self, fund_activity, thresholds):
        if fund_activity is not None:
            return list(fund_activity)
        from database.repository import get_paper_fund_activity

        return get_paper_fund_activity(limit=thresholds["fund_activity_limit"])

    def _resolve_weights(self, weights):
        if not weights:
            return dict(self.DEFAULT_WEIGHTS)
        merged = dict(self.DEFAULT_WEIGHTS)
        for name, value in weights.items():
            if name in merged:
                merged[name] = float(value)
        return merged

    # ------------------------------------------------------------------
    # Small utilities
    # ------------------------------------------------------------------
    def _section(self, ops_report, name):
        section = (ops_report or {}).get(name)
        if isinstance(section, dict):
            return section
        return {
            "status": "Unavailable",
            "reason": f"The operations report did not include a {name} section.",
        }

    def _fetch(self, producer):
        try:
            return {"ok": True, "value": producer()}
        except Exception as error:  # never propagate a subsystem failure
            return {"ok": False, "error": str(error)}

    def _moment(self, now):
        if isinstance(now, datetime):
            return now
        if now:
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(str(now)[:len(fmt) + 2].strip(), fmt)
                except ValueError:
                    continue
            try:
                return datetime.fromisoformat(str(now))
            except ValueError:
                pass
        return datetime.now()

    def policy(self):
        return {
            "read_only": True,
            "deterministic": True,
            "paper_only": True,
            "writes": False,
            "broker_integration": False,
            "real_money": False,
            "modifies_scheduler": False,
            "modifies_recommendations": False,
            "modifies_portfolio": False,
            "modifies_paper_fund": False,
            "modifies_risk_limits": False,
        }
