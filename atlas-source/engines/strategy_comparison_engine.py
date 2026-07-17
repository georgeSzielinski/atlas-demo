import hashlib
import json
from datetime import datetime

from engines.strategy_registry_engine import StrategyRegistryEngine


class StrategyComparisonEngine:
    """Deterministic, read-only, on-demand comparison of registered strategies.

    Evaluates every research-only strategy spec from StrategyRegistryEngine
    against the SAME already-stored inputs — the latest run's recommendation
    records and the current paper-fund state — and reports candidate
    recommendations, expected risks, portfolio fit, and explainability per
    strategy plus a divergence view against the named baseline.

    Honesty rules: signals are read from stored recommendation fields only; a
    missing input is reported per-term and reflected in candidate coverage; a
    candidate with under half its weight covered gets NO score or action
    (NOT_EVALUATED); an empty universe, missing recommendations, or missing
    paper-fund state degrade to NOT_EVALUATED sections with reasons. Nothing
    is fabricated, nothing is persisted, no order is created, the risk gate is
    never invoked for side effects, and the Live Paper Fund never reads this
    engine.
    """

    VERSION = "strategy-comparison-v1"
    MIN_COVERAGE_PCT = 50

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def compare(
        self,
        strategy_ids=None,
        registry=None,
        recommendations=None,
        paper_fund_state=None,
        approved_tickers=None,
        construction_engine=None,
        now=None,
    ):
        registry = registry or StrategyRegistryEngine()
        moment = self._moment(now)

        inputs = self._load_inputs(
            recommendations, paper_fund_state, approved_tickers
        )
        records = self._records_by_ticker(inputs["recommendations"])

        strategies = registry.list_strategies()
        if strategy_ids:
            wanted = {str(item).strip().lower() for item in strategy_ids}
            strategies = [
                strategy for strategy in strategies
                if strategy["strategy_id"] in wanted
            ]

        results = [
            self._safe_strategy_result(strategy, records, inputs)
            for strategy in strategies
        ]

        return {
            "generated_at": moment.isoformat(),
            "version": self.VERSION,
            "inputs": {
                "recommendation_run_id": inputs["run_id"],
                "recommendation_count": len(inputs["recommendations"]),
                "recommendation_tickers": sorted(records.keys()),
                "paper_fund_status": (inputs["paper_fund_state"] or {}).get(
                    "fund_status", "OFF"
                ),
                "fingerprint": self._fingerprint(inputs),
            },
            "strategies": results,
            "baseline_divergence": self._baseline_divergence(
                results, registry.BASELINE_STRATEGY_ID
            ),
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Input loading (read-only; every collaborator injectable)
    # ------------------------------------------------------------------
    def _load_inputs(self, recommendations, paper_fund_state, approved_tickers):
        run_id = None
        if recommendations is None:
            loaded = self._fetch(self._load_latest_recommendations)
            if loaded["ok"]:
                run_id, recommendations = loaded["value"]
            else:
                recommendations = []
        recommendations = [
            record for record in (recommendations or [])
            if isinstance(record, dict) and record.get("ticker")
        ]

        if paper_fund_state is None:
            state = self._fetch(self._load_paper_fund_state)
            paper_fund_state = state["value"] if state["ok"] else None

        if approved_tickers is None:
            approved = self._fetch(self._load_approved_tickers)
            approved_tickers = approved["value"] if approved["ok"] else []

        return {
            "run_id": run_id,
            "recommendations": recommendations,
            "paper_fund_state": paper_fund_state,
            "approved_tickers": list(approved_tickers or []),
        }

    def _load_latest_recommendations(self):
        from engines.history_engine import HistoryEngine

        history = HistoryEngine()
        runs = history.recent_runs(limit=1)
        if not runs:
            return None, []
        run_id = runs[0]["id"]
        return run_id, history.recommendations_for_run(run_id) or []

    def _load_paper_fund_state(self):
        from database.repository import get_latest_paper_fund_state

        return get_latest_paper_fund_state()

    def _load_approved_tickers(self):
        from core.settings import APPROVED_TICKERS

        return APPROVED_TICKERS

    def _records_by_ticker(self, recommendations):
        # Keep the first (most recent run order) record per ticker.
        records = {}
        for record in recommendations:
            ticker = str(record.get("ticker", "")).strip().upper()
            if ticker and ticker not in records:
                records[ticker] = record
        return records

    # ------------------------------------------------------------------
    # Per-strategy evaluation
    # ------------------------------------------------------------------
    def _safe_strategy_result(self, strategy, records, inputs):
        try:
            return self._strategy_result(strategy, records, inputs)
        except Exception as error:  # never let one strategy break the report
            return {
                "strategy_id": strategy.get("strategy_id"),
                "name": strategy.get("name"),
                "definition_hash": strategy.get("definition_hash"),
                "status": "NOT_EVALUATED",
                "reason": f"Strategy evaluation failed: {error}",
                "candidates": [],
            }

    def _strategy_result(self, strategy, records, inputs):
        universe, universe_reason = self._resolve_universe(strategy, inputs)

        base = {
            "strategy_id": strategy["strategy_id"],
            "name": strategy["name"],
            "definition_hash": strategy["definition_hash"],
            "expected_holding_period": strategy["expected_holding_period"],
            "is_baseline": strategy.get("is_baseline", False),
            "universe": universe,
            "policy": strategy["policy"],
        }

        if not universe:
            return {
                **base,
                "status": "NOT_EVALUATED",
                "reason": universe_reason or "Strategy universe is empty.",
                "candidates": [],
                "expected_risks": self._expected_risks(strategy, []),
                "portfolio_fit": self._not_evaluated(
                    "No candidates were produced for portfolio fit."
                ),
                "explainability": {
                    "top_drivers": [],
                    "missing_tickers": [],
                    "notes": [universe_reason or "Strategy universe is empty."],
                },
            }

        candidates = []
        missing_tickers = []
        for ticker in universe:
            record = records.get(ticker)
            if record is None:
                missing_tickers.append(ticker)
                continue
            candidates.append(self._score_candidate(strategy, ticker, record))

        candidates.sort(
            key=lambda item: (-(item["score"] if item["score"] is not None else -1),
                              item["ticker"])
        )
        candidates = self._apply_filters(strategy, candidates)

        evaluated = [c for c in candidates if c["status"] != "NOT_EVALUATED"]
        if not candidates and missing_tickers:
            status, reason = "NOT_EVALUATED", (
                "No stored recommendation records exist for this universe; "
                "run an Atlas analysis first."
            )
        elif not evaluated:
            status, reason = "NOT_EVALUATED", (
                "No candidate had enough signal coverage to score."
            )
        elif missing_tickers or any(c["status"] == "PARTIAL" for c in evaluated):
            status, reason = "PARTIAL", (
                "Some universe tickers or signal inputs were missing."
            )
        else:
            status, reason = "EVALUATED", None

        return {
            **base,
            "status": status,
            "reason": reason,
            "candidates": candidates,
            "expected_risks": self._expected_risks(strategy, evaluated),
            "portfolio_fit": self._portfolio_fit(
                strategy, evaluated, inputs["paper_fund_state"]
            ),
            "explainability": self._explainability(
                strategy, evaluated, missing_tickers
            ),
        }

    def _resolve_universe(self, strategy, inputs):
        rules = strategy.get("universe_rules", {})
        source = rules.get("source")

        if source == "explicit":
            tickers = rules.get("tickers", [])
        elif source == "approved_tickers":
            tickers = inputs["approved_tickers"]
            if not tickers:
                return [], "Approved tickers are unavailable."
        else:  # paper_fund_watchlist
            state = inputs["paper_fund_state"]
            if not state:
                return [], (
                    "Live paper fund has not been started, so its watchlist "
                    "universe is unavailable."
                )
            tickers = state.get("watchlist", [])
            if not tickers:
                return [], "Paper fund watchlist is empty."

        return sorted({
            str(ticker).strip().upper()
            for ticker in tickers
            if str(ticker).strip()
        }), None

    # ------------------------------------------------------------------
    # Candidate scoring
    # ------------------------------------------------------------------
    def _score_candidate(self, strategy, ticker, record):
        weights = strategy["scoring_logic"]["weights"]
        bands = strategy["scoring_logic"]["action_bands"]
        catalog = StrategyRegistryEngine.SIGNAL_INPUTS

        terms = []
        available_weight = 0.0
        weighted_sum = 0.0
        missing_inputs = []

        for signal, weight in sorted(weights.items()):
            raw = record.get(signal)
            value = self._number(raw)
            if value is None:
                missing_inputs.append(signal)
                terms.append({
                    "signal": signal,
                    "status": "NOT_EVALUATED",
                    "value": None,
                    "weight": weight,
                    "contribution": None,
                })
                continue
            scale = catalog.get(signal, {}).get("scale", 100)
            normalized = max(0.0, min(100.0, value / scale * 100))
            available_weight += weight
            weighted_sum += normalized * weight
            terms.append({
                "signal": signal,
                "status": "EVALUATED",
                "value": value,
                "normalized": round(normalized, 2),
                "weight": weight,
                "contribution": round(normalized * weight, 2),
            })

        total_weight = sum(weights.values())
        coverage = round(available_weight / total_weight * 100, 2) if total_weight else 0

        if coverage < self.MIN_COVERAGE_PCT:
            return {
                "ticker": ticker,
                "status": "NOT_EVALUATED",
                "reason": (
                    f"Only {coverage}% of signal weight had stored values; "
                    "scores below 50% coverage are not assigned."
                ),
                "score": None,
                "action": None,
                "coverage_pct": coverage,
                "contributing_terms": terms,
                "missing_inputs": missing_inputs,
                "explanation": (
                    f"{ticker} was not scored: missing {', '.join(missing_inputs)}."
                ),
            }

        # Renormalize over available weight so partial coverage never deflates
        # the score; coverage is reported alongside.
        score = round(weighted_sum / available_weight, 2)
        if score >= bands["buy"]:
            action = "BUY"
        elif score >= bands["hold"]:
            action = "HOLD"
        else:
            action = "AVOID"

        drivers = [
            term for term in terms if term["status"] == "EVALUATED"
        ]
        drivers.sort(key=lambda term: -term["contribution"])
        top = drivers[0]["signal"] if drivers else "no signal"

        return {
            "ticker": ticker,
            "status": "EVALUATED" if coverage == 100 else "PARTIAL",
            "reason": None if coverage == 100 else (
                f"Signal coverage {coverage}%: missing {', '.join(missing_inputs)}."
            ),
            "score": score,
            "action": action,
            "coverage_pct": coverage,
            "contributing_terms": terms,
            "missing_inputs": missing_inputs,
            # Raw values for whitelisted universe filters — read from the
            # stored record so filters work even on signals the strategy does
            # not weight.
            "filter_values": {
                "confidence": self._number(record.get("confidence")),
                "signal_quality_score": self._number(
                    record.get("signal_quality_score")
                ),
            },
            "explanation": (
                f"{action} at score {score} (coverage {coverage}%); "
                f"strongest driver: {top}."
            ),
        }

    def _apply_filters(self, strategy, candidates):
        filters = strategy.get("universe_rules", {}).get("filters", {})
        if not filters:
            return candidates

        result = []
        for candidate in candidates:
            if candidate["status"] == "NOT_EVALUATED":
                result.append(candidate)
                continue
            values = candidate.get("filter_values", {})
            excluded = None
            minimum_confidence = filters.get("min_confidence")
            if minimum_confidence is not None:
                confidence = values.get("confidence")
                if confidence is not None and confidence < minimum_confidence:
                    excluded = f"confidence {confidence} below minimum {minimum_confidence}"
            minimum_quality = filters.get("min_signal_quality")
            if excluded is None and minimum_quality is not None:
                quality = values.get("signal_quality_score")
                if quality is not None and quality < minimum_quality:
                    excluded = f"signal quality {quality} below minimum {minimum_quality}"

            if excluded:
                result.append({
                    **candidate,
                    "action": "EXCLUDED",
                    "reason": f"Filtered out: {excluded}.",
                    "explanation": f"{candidate['ticker']} excluded — {excluded}.",
                })
            else:
                result.append(candidate)

        maximum = filters.get("max_candidates")
        if isinstance(maximum, int) and maximum > 0:
            kept, overflow = [], 0
            for candidate in result:
                if candidate.get("action") in {"BUY", "HOLD"} and len(
                    [c for c in kept if c.get("action") in {"BUY", "HOLD"}]
                ) >= maximum:
                    overflow += 1
                    kept.append({
                        **candidate,
                        "action": "EXCLUDED",
                        "reason": f"Filtered out: max_candidates {maximum} reached.",
                    })
                else:
                    kept.append(candidate)
            result = kept

        return result

    # ------------------------------------------------------------------
    # Expected risks (advisory, deterministic, no side effects)
    # ------------------------------------------------------------------
    def _expected_risks(self, strategy, evaluated_candidates):
        from engines.risk_management_engine import RiskManagementEngine

        assumptions = strategy.get("risk_assumptions", {})
        limits = dict(RiskManagementEngine.DEFAULT_LIMITS)

        checks = []
        max_position = assumptions.get("max_position_pct")
        limit_position = limits.get("max_position_size")
        if max_position is not None and isinstance(limit_position, (int, float)):
            checks.append({
                "assumption": "max_position_pct",
                "assumed": max_position,
                "risk_limit": round(limit_position * 100, 2),
                "within_limit": max_position <= limit_position * 100,
            })
        max_correlation = assumptions.get("max_correlation")
        limit_correlation = limits.get("max_correlation")
        if max_correlation is not None and isinstance(limit_correlation, (int, float)):
            checks.append({
                "assumption": "max_correlation",
                "assumed": max_correlation,
                "risk_limit": limit_correlation,
                "within_limit": max_correlation <= limit_correlation,
            })
        max_positions = assumptions.get("max_positions")
        limit_count = limits.get("max_position_count")
        if max_positions is not None and isinstance(limit_count, (int, float)):
            checks.append({
                "assumption": "max_positions",
                "assumed": max_positions,
                "risk_limit": limit_count,
                "within_limit": max_positions <= limit_count,
            })

        buys = [c for c in evaluated_candidates if c.get("action") == "BUY"]
        notes = []
        if max_positions is not None and len(buys) > max_positions:
            notes.append(
                f"{len(buys)} BUY candidates exceed the strategy's own "
                f"max_positions assumption of {max_positions}."
            )

        return {
            "status": "EVALUATED" if checks else "NOT_EVALUATED",
            "reason": None if checks else (
                "No overlapping assumption/limit pairs to compare."
            ),
            "assumptions": assumptions,
            "limit_checks": checks,
            "buy_candidate_count": len(buys),
            "notes": notes,
            "correlation": {
                "status": "NOT_EVALUATED",
                "reason": (
                    "Correlation risk requires real price history, which the "
                    "on-demand comparison does not fetch. Run the paper-fund "
                    "cycle or research replay for correlation evidence."
                ),
            },
            "advisory_only": True,
        }

    # ------------------------------------------------------------------
    # Portfolio fit (dry-run construction; read-only)
    # ------------------------------------------------------------------
    def _portfolio_fit(self, strategy, evaluated_candidates, state):
        if not state:
            return self._not_evaluated(
                "Live paper fund has not been started; there is no portfolio "
                "to fit against."
            )
        actionable = [
            candidate for candidate in evaluated_candidates
            if candidate.get("action") in {"BUY", "HOLD"}
        ]
        if not actionable:
            return self._not_evaluated(
                "Strategy produced no BUY/HOLD candidates to fit."
            )

        try:
            construction = self._dry_run_construction(actionable, state)
        except Exception as error:
            return self._not_evaluated(f"Portfolio construction failed: {error}")

        allocations = construction.get("recommended_allocations", [])
        positions = state.get("positions", {}) or {}
        fit_rows = []
        for allocation in allocations:
            ticker = allocation.get("ticker")
            fit_rows.append({
                "ticker": ticker,
                "suggested_allocation": allocation.get("suggested_allocation"),
                "current_allocation": allocation.get("current_allocation"),
                "capital_required": allocation.get("capital_required"),
                "position_priority": allocation.get("position_priority"),
                "already_held": ticker in positions,
            })

        return {
            "status": "EVALUATED",
            "reason": None,
            "suggested_allocations": fit_rows,
            "risk_summary": construction.get("risk_summary", {}),
            "diversification": construction.get("diversification", {}),
            "dry_run": True,
        }

    def _dry_run_construction(self, candidates, state):
        from engines.portfolio_construction_engine import (
            PortfolioConstructionEngine,
        )

        recommendations = [
            {
                "ticker": candidate["ticker"],
                "action": candidate["action"],
                "confidence": candidate["score"],
                "overall_conviction": candidate["score"],
                "sector": "Unknown",
                "industry": "Unknown",
                "country": "US",
            }
            for candidate in candidates
        ]
        positions = []
        current_value = 0.0
        for ticker, position in (state.get("positions", {}) or {}).items():
            quantity = self._number(position.get("quantity")) or 0
            price = self._number(
                position.get("current_price", position.get("cost_basis"))
            ) or 0
            value = round(quantity * price, 2)
            current_value += value
            positions.append({
                "ticker": ticker,
                "quantity": quantity,
                "cost_basis": position.get("cost_basis"),
                "current_price": price,
                "current_value": value,
            })
        cash = self._number(state.get("cash")) or 0
        paper_portfolio = {
            "cash": cash,
            "portfolio_value": round(cash + current_value, 2),
            "positions": positions,
        }

        return PortfolioConstructionEngine().build(
            recommendations=recommendations,
            paper_portfolio=paper_portfolio,
        )

    # ------------------------------------------------------------------
    # Explainability & divergence
    # ------------------------------------------------------------------
    def _explainability(self, strategy, evaluated_candidates, missing_tickers):
        driver_totals = {}
        for candidate in evaluated_candidates:
            for term in candidate.get("contributing_terms", []):
                if term["status"] != "EVALUATED":
                    continue
                driver_totals.setdefault(term["signal"], 0.0)
                driver_totals[term["signal"]] += term["contribution"]

        top_drivers = [
            {"signal": signal, "total_contribution": round(total, 2)}
            for signal, total in sorted(
                driver_totals.items(), key=lambda item: (-item[1], item[0])
            )
        ][:5]

        notes = [strategy.get("explanation", "")]
        if missing_tickers:
            notes.append(
                "No stored recommendation record for: "
                + ", ".join(sorted(missing_tickers)) + "."
            )

        return {
            "top_drivers": top_drivers,
            "missing_tickers": sorted(missing_tickers),
            "notes": [note for note in notes if note],
        }

    def _baseline_divergence(self, results, baseline_id):
        baseline = next(
            (item for item in results if item["strategy_id"] == baseline_id),
            None,
        )
        if baseline is None or baseline["status"] == "NOT_EVALUATED":
            return {
                "status": "NOT_EVALUATED",
                "reason": (
                    "Baseline strategy was not evaluated, so divergence "
                    "cannot be measured."
                ),
            }

        baseline_actions = {
            candidate["ticker"]: candidate.get("action")
            for candidate in baseline["candidates"]
            if candidate.get("action")
        }

        rows = []
        for result in results:
            if result["strategy_id"] == baseline_id:
                continue
            agreements = 0
            comparisons = 0
            divergent = []
            for candidate in result.get("candidates", []):
                action = candidate.get("action")
                ticker = candidate["ticker"]
                baseline_action = baseline_actions.get(ticker)
                if action is None or baseline_action is None:
                    continue
                comparisons += 1
                if action == baseline_action:
                    agreements += 1
                else:
                    divergent.append({
                        "ticker": ticker,
                        "baseline_action": baseline_action,
                        "strategy_action": action,
                    })
            rows.append({
                "strategy_id": result["strategy_id"],
                "compared_tickers": comparisons,
                "agreement_pct": (
                    round(agreements / comparisons * 100, 2)
                    if comparisons else None
                ),
                "divergent_actions": divergent,
                "status": "EVALUATED" if comparisons else "NOT_EVALUATED",
            })

        return {
            "status": "EVALUATED",
            "baseline_strategy_id": baseline_id,
            "rows": rows,
        }

    # ------------------------------------------------------------------
    # Utilities & policy
    # ------------------------------------------------------------------
    def _fingerprint(self, inputs):
        state = inputs["paper_fund_state"] or {}
        payload = json.dumps(
            {
                "run_id": inputs["run_id"],
                "tickers": sorted(
                    str(record.get("ticker", "")).upper()
                    for record in inputs["recommendations"]
                ),
                "fund_updated_at": state.get("updated_at"),
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def _not_evaluated(self, reason):
        return {"status": "NOT_EVALUATED", "reason": reason}

    def _fetch(self, producer):
        try:
            return {"ok": True, "value": producer()}
        except Exception as error:
            return {"ok": False, "error": str(error)}

    def _number(self, value):
        if value is None or isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
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

    def policy(self):
        return {
            "read_only": True,
            "on_demand_only": True,
            "persists_nothing": True,
            "deterministic": True,
            "research_only": True,
            "llm_decisions": False,
            "broker_integration": False,
            "real_money": False,
            "creates_orders": False,
            "invokes_risk_gate": False,
            "modifies_live_paper_fund": False,
            "modifies_recommendations": False,
            "activation_switch": False,
        }
