from engines.portfolio_intelligence_engine import PortfolioIntelligenceEngine
from engines.risk_management_engine import RiskManagementEngine
from engines.self_learning_analytics_engine import SelfLearningAnalyticsEngine


class ScenarioAnalysisEngine:
    """Deterministic, read-only scenario / stress analysis for the Live Paper Fund.

    The engine evaluates how the current paper-fund portfolio would behave under
    hypothetical uniform market shocks. It is analysis only: it never places
    trades, changes recommendations, mutates portfolio state, or alters risk
    limits. Every scenario applies a fixed percentage shock to the latest
    validated position values (cash held fixed) and reuses the existing
    portfolio intelligence, risk, and learning engines instead of duplicating
    their logic. Any metric that cannot be computed returns ``NOT_EVALUATED``
    with a human-readable reason; values are never fabricated.
    """

    DEFAULT_LIMIT = 200

    # Ordered most-bearish to most-bullish for deterministic, readable output.
    SCENARIOS = (
        ("Market -20%", -0.20),
        ("Market -10%", -0.10),
        ("Market -5%", -0.05),
        ("Market +5%", 0.05),
        ("Market +10%", 0.10),
        ("Market +20%", 0.20),
    )

    def __init__(self):
        self.intelligence = PortfolioIntelligenceEngine()
        self.learning = SelfLearningAnalyticsEngine()
        self.risk_limits = dict(RiskManagementEngine.DEFAULT_LIMITS)

    def generate(
        self,
        state=None,
        snapshots=None,
        orders=None,
        risk_decisions=None,
        learning=None,
        activity=None,
        limit=None,
    ):
        limit = limit or self.DEFAULT_LIMIT
        data = self._load(
            state=state,
            snapshots=snapshots,
            orders=orders,
            risk_decisions=risk_decisions,
            learning=learning,
            activity=activity,
            limit=limit,
        )

        latest_snapshot = self.intelligence._latest_snapshot(data["snapshots"])
        base_portfolio = self.intelligence._portfolio(data["state"], latest_snapshot)
        sector_map = self.intelligence._sector_map(
            data["learning"], data["activity"]
        )

        base_intelligence = self.intelligence.generate(
            state=data["state"],
            snapshots=data["snapshots"],
            risk_decisions=data["risk_decisions"],
            learning=data["learning"],
            activity=data["activity"],
            limit=limit,
        )
        learning_analytics = self.learning.generate(
            learning=data["learning"],
            orders=data["orders"],
            snapshots=data["snapshots"],
            risk_decisions=data["risk_decisions"],
            limit=limit,
        )

        base_case = self._base_case(base_portfolio, base_intelligence)
        scenarios = [
            self._evaluate_scenario(name, shock, base_portfolio, sector_map)
            for name, shock in self.SCENARIOS
        ]
        stress_summary = self._stress_summary(
            base_portfolio,
            base_case,
            scenarios,
            base_intelligence,
            learning_analytics,
        )

        return {
            "generated_at": self._generated_at(data["state"], latest_snapshot),
            "portfolio_status": {
                "fund_status": data["state"].get("fund_status", "OFF"),
                "last_update": data["state"].get("last_update"),
                "latest_snapshot_at": (
                    latest_snapshot.get("as_of") if latest_snapshot else None
                ),
                "evaluable": base_case["status"] == "EVALUATED",
            },
            "base_portfolio": {
                "status": base_case["status"],
                "reason": base_case.get("reason"),
                "cash": base_portfolio.get("cash"),
                "invested_value": base_case.get("invested_value"),
                "portfolio_value": (
                    base_portfolio.get("portfolio_value")
                    if base_case["status"] == "EVALUATED"
                    else None
                ),
                "position_count": len(base_portfolio.get("positions", {})),
            },
            "risk_limits": dict(self.risk_limits),
            "scenarios": scenarios,
            "base_case": base_case,
            "stress_summary": stress_summary,
            "source_counts": {
                "paper_fund_snapshots": len(data["snapshots"]),
                "paper_fund_orders": len(data["orders"]),
                "risk_decisions": len(data["risk_decisions"]),
                "paper_fund_learning": len(data["learning"]),
                "paper_fund_activity": len(data["activity"]),
            },
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Scenario evaluation
    # ------------------------------------------------------------------
    def _evaluate_scenario(self, name, shock, base_portfolio, sector_map):
        shock_percent = round(shock * 100, 4)
        positions = base_portfolio.get("positions", {})
        cash = base_portfolio.get("cash")
        base_pv = self._number(base_portfolio.get("portfolio_value"))

        if not positions or base_pv <= 0 or cash is None:
            reason = (
                "No positions or portfolio value are available to evaluate this "
                "scenario."
            )
            return {
                "name": name,
                "shock_percent": shock_percent,
                "status": "NOT_EVALUATED",
                "reason": reason,
                "estimated_portfolio_value": self._not_evaluated(reason),
                "estimated_portfolio_return": self._not_evaluated(reason),
                "estimated_cash_percent": self._not_evaluated(reason),
                "estimated_largest_position": self._not_evaluated(reason),
                "estimated_concentration": self._not_evaluated(reason),
                "estimated_risk_utilization": self._not_evaluated(reason),
                "estimated_drawdown": self._not_evaluated(reason),
                "constraint_violations": [],
                "summary": (
                    f"{name}: NOT_EVALUATED because {reason.lower()}"
                ),
            }

        factor = 1 + shock
        shocked_positions = {}
        shocked_invested = 0.0
        for symbol, position in sorted(positions.items()):
            shocked_value = self._number(position.get("current_value")) * factor
            shocked_invested += shocked_value
            shocked_positions[symbol] = {
                **position,
                "symbol": symbol,
                "current_value": round(shocked_value, 4),
            }

        cash_number = self._number(cash)
        scenario_pv = cash_number + shocked_invested
        shocked_portfolio = {
            "cash": round(cash_number, 4),
            "positions": shocked_positions,
            "portfolio_value": round(scenario_pv, 4),
        }

        # Reuse existing portfolio intelligence math on the shocked portfolio.
        concentration = self.intelligence.largest_position_concentration(
            shocked_portfolio
        )
        cash_reserve = self.intelligence.cash_reserve_status(shocked_portfolio)
        sector_exposure = self.intelligence.sector_exposure_summary(
            shocked_portfolio, sector_map
        )

        return_ratio = (scenario_pv - base_pv) / base_pv
        drawdown_ratio = max(0.0, (base_pv - scenario_pv) / base_pv)
        exposure_ratio = shocked_invested / scenario_pv if scenario_pv > 0 else None

        risk_utilization = self._risk_utilization(
            concentration, exposure_ratio, sector_exposure
        )
        violations = self._constraint_violations(
            concentration, exposure_ratio, sector_exposure, shocked_positions
        )

        return {
            "name": name,
            "shock_percent": shock_percent,
            "status": "EVALUATED",
            "estimated_portfolio_value": self._metric(
                round(scenario_pv, 2), "currency"
            ),
            "estimated_portfolio_return": self._metric(
                round(return_ratio * 100, 4), "percent"
            ),
            "estimated_cash_percent": {
                "status": "EVALUATED",
                "value": cash_reserve.get("cash_percent"),
                "unit": "percent",
                "reserve_status": cash_reserve.get("status"),
            },
            "estimated_largest_position": {
                "status": concentration.get("status"),
                "symbol": concentration.get("symbol"),
                "value": concentration.get("current_value"),
                "unit": "currency",
            },
            "estimated_concentration": {
                "status": concentration.get("status"),
                "value": concentration.get("concentration_percent"),
                "ratio": concentration.get("concentration_ratio"),
                "unit": "percent",
            },
            "estimated_risk_utilization": risk_utilization,
            "estimated_drawdown": self._metric(
                round(drawdown_ratio * 100, 4), "percent"
            ),
            "constraint_violations": violations,
            "summary": self._scenario_summary(
                name,
                round(return_ratio * 100, 4),
                round(drawdown_ratio * 100, 4),
                concentration,
                violations,
            ),
        }

    def _risk_utilization(self, concentration, exposure_ratio, sector_exposure):
        by_limit = []

        concentration_ratio = concentration.get("concentration_ratio")
        by_limit.append(
            self._utilization_row(
                "max_position_size",
                self.risk_limits["max_position_size"],
                concentration_ratio,
                "Largest position weight versus the maximum position size limit.",
            )
        )

        by_limit.append(
            self._utilization_row(
                "max_portfolio_exposure",
                self.risk_limits["max_portfolio_exposure"],
                exposure_ratio,
                "Invested exposure versus the maximum portfolio exposure limit.",
            )
        )

        largest_sector = sector_exposure.get("largest_sector") or {}
        sector_ratio = largest_sector.get("exposure_ratio")
        if sector_ratio is None:
            by_limit.append(
                {
                    "limit_name": "max_sector_exposure",
                    "limit": self.risk_limits["max_sector_exposure"],
                    "status": "NOT_EVALUATED",
                    "measured_ratio": None,
                    "utilization_percent": None,
                    "reason": (
                        "Sector metadata is unavailable, so sector exposure "
                        "utilization was not evaluated."
                    ),
                }
            )
        else:
            by_limit.append(
                self._utilization_row(
                    "max_sector_exposure",
                    self.risk_limits["max_sector_exposure"],
                    sector_ratio,
                    "Largest sector exposure versus the maximum sector limit.",
                    sector=largest_sector.get("sector"),
                )
            )

        evaluated = [row for row in by_limit if row["status"] != "NOT_EVALUATED"]
        return {
            "status": "EVALUATED" if evaluated else "NOT_EVALUATED",
            "limits": dict(self.risk_limits),
            "by_limit": by_limit,
        }

    def _utilization_row(self, limit_name, limit, measured_ratio, reason, sector=None):
        if measured_ratio is None or self._number(limit) == 0:
            return {
                "limit_name": limit_name,
                "limit": limit,
                "status": "NOT_EVALUATED",
                "measured_ratio": None,
                "utilization_percent": None,
                "reason": (
                    "Limit or measured value is unavailable, so utilization was "
                    "not evaluated."
                ),
            }
        utilization = self._number(measured_ratio) / self._number(limit)
        row = {
            "limit_name": limit_name,
            "limit": limit,
            "status": "BREACH" if self._number(measured_ratio) > self._number(limit) else "OK",
            "measured_ratio": round(self._number(measured_ratio), 6),
            "measured_percent": round(self._number(measured_ratio) * 100, 4),
            "utilization_percent": round(utilization * 100, 4),
            "reason": reason,
        }
        if sector is not None:
            row["sector"] = sector
        return row

    def _constraint_violations(
        self, concentration, exposure_ratio, sector_exposure, shocked_positions
    ):
        violations = []

        if concentration.get("status") == "FAIL":
            violations.append(
                {
                    "constraint": "max_position_size",
                    "status": "VIOLATED",
                    "limit": self.risk_limits["max_position_size"],
                    "measured_percent": concentration.get("concentration_percent"),
                    "symbol": concentration.get("symbol"),
                    "reason": (
                        "Largest position would exceed the maximum position size "
                        "limit under this scenario."
                    ),
                }
            )

        exposure_limit = self._number(self.risk_limits["max_portfolio_exposure"])
        if exposure_ratio is not None and self._number(exposure_ratio) > exposure_limit:
            violations.append(
                {
                    "constraint": "max_portfolio_exposure",
                    "status": "VIOLATED",
                    "limit": self.risk_limits["max_portfolio_exposure"],
                    "measured_percent": round(self._number(exposure_ratio) * 100, 4),
                    "reason": (
                        "Invested exposure would exceed the maximum portfolio "
                        "exposure limit under this scenario."
                    ),
                }
            )

        for item in sector_exposure.get("items", []):
            if item.get("status") == "FAIL":
                violations.append(
                    {
                        "constraint": "max_sector_exposure",
                        "status": "VIOLATED",
                        "limit": self.risk_limits["max_sector_exposure"],
                        "measured_percent": item.get("exposure_percent"),
                        "sector": item.get("sector"),
                        "reason": (
                            f"{item.get('sector')} sector exposure would exceed "
                            "the maximum sector limit under this scenario."
                        ),
                    }
                )

        position_count = len(shocked_positions)
        count_limit = int(self.risk_limits["max_position_count"])
        if position_count > count_limit:
            violations.append(
                {
                    "constraint": "max_position_count",
                    "status": "VIOLATED",
                    "limit": count_limit,
                    "measured": position_count,
                    "reason": (
                        "Portfolio position count exceeds the maximum position "
                        "count limit."
                    ),
                }
            )

        for missing in sector_exposure.get("missing_sector", []):
            violations.append(
                {
                    "constraint": "max_sector_exposure",
                    "status": "NOT_EVALUATED",
                    "limit": self.risk_limits["max_sector_exposure"],
                    "symbol": missing.get("symbol"),
                    "reason": (
                        "Sector exposure cannot be checked because sector "
                        f"metadata is missing for {missing.get('symbol')}."
                    ),
                }
            )

        return sorted(
            violations,
            key=lambda row: (
                0 if row["status"] == "VIOLATED" else 1,
                row["constraint"],
                str(row.get("symbol") or row.get("sector") or ""),
            ),
        )

    # ------------------------------------------------------------------
    # Base case and stress summary
    # ------------------------------------------------------------------
    def _base_case(self, base_portfolio, base_intelligence):
        positions = base_portfolio.get("positions", {})
        portfolio_value = self._number(base_portfolio.get("portfolio_value"))
        if not positions or portfolio_value <= 0:
            reason = (
                "No paper-fund positions or portfolio value are available to "
                "run scenario analysis."
            )
            return {
                "name": "Base (current market)",
                "shock_percent": 0.0,
                "status": "NOT_EVALUATED",
                "reason": reason,
            }

        invested_value = round(
            sum(
                self._number(position.get("current_value"))
                for position in positions.values()
            ),
            4,
        )
        return {
            "name": "Base (current market)",
            "shock_percent": 0.0,
            "status": "EVALUATED",
            "estimated_portfolio_value": self._metric(
                round(portfolio_value, 2), "currency"
            ),
            "invested_value": invested_value,
            "cash": base_portfolio.get("cash"),
            "portfolio_health_score": base_intelligence.get(
                "portfolio_health_score"
            ),
            "cash_reserve_status": base_intelligence.get("cash_reserve_status"),
            "largest_position_concentration": base_intelligence.get(
                "largest_position_concentration"
            ),
            "sector_exposure_summary": base_intelligence.get(
                "sector_exposure_summary"
            ),
        }

    def _stress_summary(
        self,
        base_portfolio,
        base_case,
        scenarios,
        base_intelligence,
        learning_analytics,
    ):
        evaluated = [
            scenario for scenario in scenarios if scenario["status"] == "EVALUATED"
        ]
        if not evaluated:
            reason = (
                "No scenario could be evaluated because portfolio holdings are "
                "unavailable."
            )
            return {
                "status": "NOT_EVALUATED",
                "reason": reason,
                "best_case": None,
                "base_case": base_case,
                "worst_case": None,
                "top_contributors": [],
                "largest_risks": [],
                "watch_items": [],
                "portfolio_resilience_score": self._not_evaluated(reason),
            }

        best = max(
            evaluated,
            key=lambda scenario: (
                scenario["estimated_portfolio_value"]["value"],
                scenario["shock_percent"],
            ),
        )
        worst = min(
            evaluated,
            key=lambda scenario: (
                scenario["estimated_portfolio_value"]["value"],
                scenario["shock_percent"],
            ),
        )

        top_contributors = self._top_contributors(base_portfolio)
        largest_risks = self._largest_risks(
            base_portfolio, worst, base_intelligence, learning_analytics
        )
        watch_items = self._watch_items(
            worst, base_intelligence, learning_analytics
        )
        resilience = self._resilience_score(base_portfolio, worst)

        return {
            "status": "EVALUATED",
            "best_case": self._case_reference(best),
            "base_case": base_case,
            "worst_case": self._case_reference(worst),
            "top_contributors": top_contributors,
            "largest_risks": largest_risks,
            "watch_items": watch_items,
            "portfolio_resilience_score": resilience,
        }

    def _case_reference(self, scenario):
        return {
            "name": scenario["name"],
            "shock_percent": scenario["shock_percent"],
            "estimated_portfolio_value": scenario["estimated_portfolio_value"],
            "estimated_portfolio_return": scenario["estimated_portfolio_return"],
            "estimated_drawdown": scenario["estimated_drawdown"],
            "constraint_violations": scenario["constraint_violations"],
        }

    def _top_contributors(self, base_portfolio):
        positions = base_portfolio.get("positions", {})
        invested_value = sum(
            self._number(position.get("current_value"))
            for position in positions.values()
        )
        if not positions or invested_value <= 0:
            return []

        ranked = sorted(
            positions.values(),
            key=lambda position: (
                -self._number(position.get("current_value")),
                position.get("symbol", ""),
            ),
        )
        contributors = []
        for position in ranked[:3]:
            value = self._number(position.get("current_value"))
            contributors.append(
                {
                    "symbol": position.get("symbol"),
                    "current_value": round(value, 4),
                    "weight_percent": round(value / invested_value * 100, 4),
                    "best_case_gain": round(value * 0.20, 4),
                    "worst_case_loss": round(value * 0.20, 4),
                    "reason": (
                        "Largest holdings move portfolio value the most under a "
                        "uniform market shock."
                    ),
                }
            )
        return contributors

    def _largest_risks(
        self, base_portfolio, worst, base_intelligence, learning_analytics
    ):
        risks = []

        for violation in worst.get("constraint_violations", []):
            if violation.get("status") != "VIOLATED":
                continue
            risks.append(
                {
                    "type": "STRESS_CONSTRAINT_BREACH",
                    "severity": "FAIL",
                    "scenario": worst["name"],
                    "constraint": violation.get("constraint"),
                    "symbol": violation.get("symbol"),
                    "sector": violation.get("sector"),
                    "measured_percent": violation.get("measured_percent"),
                    "reason": violation.get("reason"),
                }
            )

        for risk in base_intelligence.get("top_portfolio_risks", []):
            risks.append(
                {
                    "type": "PORTFOLIO_RISK",
                    "severity": risk.get("severity"),
                    "risk_type": risk.get("risk_type"),
                    "symbol": risk.get("symbol"),
                    "sector": risk.get("sector"),
                    "rule": risk.get("rule"),
                    "reason": risk.get("reason"),
                }
            )

        symbol_performance = learning_analytics.get("symbol_performance", {})
        for item in symbol_performance.get("items", []):
            if item.get("status") == "EVALUATED" and self._number(
                item.get("unrealized_pl")
            ) < 0:
                risks.append(
                    {
                        "type": "NEGATIVE_SYMBOL_PL",
                        "severity": "WARN",
                        "symbol": item.get("symbol"),
                        "unrealized_pl": item.get("unrealized_pl"),
                        "reason": (
                            f"{item.get('symbol')} already carries negative "
                            "unrealized paper P/L before any shock."
                        ),
                    }
                )

        return sorted(
            risks,
            key=lambda row: (
                self._severity_rank(row.get("severity")),
                row["type"],
                str(row.get("symbol") or row.get("sector") or row.get("rule") or ""),
            ),
        )

    def _watch_items(self, worst, base_intelligence, learning_analytics):
        items = list(base_intelligence.get("suggested_watch_items", []))

        for violation in worst.get("constraint_violations", []):
            if violation.get("status") != "VIOLATED":
                continue
            items.append(
                {
                    "type": "STRESS_WATCH",
                    "status": "FAIL",
                    "scenario": worst["name"],
                    "constraint": violation.get("constraint"),
                    "symbol": violation.get("symbol"),
                    "sector": violation.get("sector"),
                    "message": (
                        f"Watch {violation.get('constraint')} under a "
                        f"{worst['name']} shock."
                    ),
                }
            )

        watch_patterns = learning_analytics.get("watch_patterns", {})
        for pattern in watch_patterns.get("items", []):
            items.append(
                {
                    "type": f"LEARNING_{pattern.get('type', 'PATTERN')}",
                    "status": pattern.get("status"),
                    "symbol": pattern.get("symbol"),
                    "rule": pattern.get("rule"),
                    "message": pattern.get("message"),
                }
            )

        return items

    def _resilience_score(self, base_portfolio, worst):
        score = 100
        deductions = []

        drawdown = worst.get("estimated_drawdown", {})
        drawdown_percent = self._number(drawdown.get("value"))
        drawdown_deduction = min(40, drawdown_percent)
        score -= drawdown_deduction
        deductions.append(
            {
                "factor": "worst_case_drawdown",
                "deduction": round(drawdown_deduction, 4),
                "detail": (
                    f"Worst-case ({worst['name']}) estimated drawdown of "
                    f"{round(drawdown_percent, 4)}%."
                ),
            }
        )

        cash_ratio = self._cash_ratio(base_portfolio)
        if cash_ratio is None:
            cash_deduction = 6
            cash_detail = "Cash buffer could not be evaluated."
        elif cash_ratio < 0.05:
            cash_deduction = 20
            cash_detail = "Cash buffer is below 5% of the portfolio."
        elif cash_ratio < 0.10:
            cash_deduction = 12
            cash_detail = "Cash buffer is below 10% of the portfolio."
        elif cash_ratio < 0.20:
            cash_deduction = 6
            cash_detail = "Cash buffer is below 20% of the portfolio."
        else:
            cash_deduction = 0
            cash_detail = "Cash buffer is at or above 20% of the portfolio."
        score -= cash_deduction
        deductions.append(
            {
                "factor": "cash_buffer",
                "deduction": cash_deduction,
                "detail": cash_detail,
            }
        )

        concentration_status = worst.get("estimated_concentration", {}).get("status")
        if concentration_status == "FAIL":
            concentration_deduction = 15
        elif concentration_status == "WARN":
            concentration_deduction = 8
        else:
            concentration_deduction = 0
        score -= concentration_deduction
        deductions.append(
            {
                "factor": "worst_case_concentration",
                "deduction": concentration_deduction,
                "detail": (
                    "Worst-case largest-position concentration status is "
                    f"{concentration_status}."
                ),
            }
        )

        violation_count = len(
            [
                violation
                for violation in worst.get("constraint_violations", [])
                if violation.get("status") == "VIOLATED"
            ]
        )
        violation_deduction = min(20, violation_count * 5)
        score -= violation_deduction
        deductions.append(
            {
                "factor": "worst_case_constraint_violations",
                "deduction": violation_deduction,
                "detail": (
                    f"{violation_count} constraint(s) would be violated under "
                    f"the {worst['name']} shock."
                ),
            }
        )

        final_score = max(0, min(100, int(round(score))))
        return {
            "status": "EVALUATED",
            "score": final_score,
            "scale": "0-100",
            "rating": self._resilience_rating(final_score),
            "deterministic": True,
            "deductions": deductions,
            "reason": (
                "Resilience starts at 100 and deducts for worst-case drawdown, "
                "thin cash buffer, worst-case concentration, and worst-case "
                "constraint violations."
            ),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def policy(self):
        return {
            "read_only": True,
            "descriptive_only": True,
            "deterministic": True,
            "paper_only": True,
            "broker_integration": False,
            "real_money": False,
            "does_not_modify_recommendations": True,
            "does_not_modify_trades": True,
            "does_not_modify_risk_limits": True,
        }

    def _load(self, state, snapshots, orders, risk_decisions, learning, activity, limit):
        if state is None:
            from database.repository import get_latest_paper_fund_state

            state = get_latest_paper_fund_state()
        if snapshots is None:
            from database.repository import get_paper_fund_snapshots

            snapshots = get_paper_fund_snapshots(limit=limit)
        if orders is None:
            from database.repository import get_paper_fund_orders

            orders = get_paper_fund_orders(limit=limit)
        if risk_decisions is None:
            from database.repository import get_recent_risk_decisions

            risk_decisions = get_recent_risk_decisions(limit=limit)
        if learning is None:
            from database.repository import get_paper_fund_learning

            learning = get_paper_fund_learning(limit=limit)
        if activity is None:
            from database.repository import get_paper_fund_activity

            activity = get_paper_fund_activity(limit=limit)

        return {
            "state": state or {},
            "snapshots": snapshots or [],
            "orders": orders or [],
            "risk_decisions": risk_decisions or [],
            "learning": learning or [],
            "activity": activity or [],
        }

    def _scenario_summary(self, name, return_percent, drawdown_percent, concentration, violations):
        active = [v for v in violations if v.get("status") == "VIOLATED"]
        violation_text = (
            f"{len(active)} constraint violation(s)"
            if active
            else "no constraint violations"
        )
        return (
            f"{name}: estimated return {return_percent}% with a "
            f"{drawdown_percent}% drawdown, largest-position concentration "
            f"{concentration.get('status')}, and {violation_text}."
        )

    def _cash_ratio(self, base_portfolio):
        cash = base_portfolio.get("cash")
        portfolio_value = self._number(base_portfolio.get("portfolio_value"))
        if cash is None or portfolio_value <= 0:
            return None
        return self._number(cash) / portfolio_value

    def _generated_at(self, state, latest_snapshot):
        return (
            (latest_snapshot or {}).get("as_of")
            or state.get("updated_at")
            or state.get("last_update")
            or ""
        )

    def _metric(self, value, unit=None):
        return {"status": "EVALUATED", "value": value, "unit": unit}

    def _not_evaluated(self, reason):
        return {"status": "NOT_EVALUATED", "value": None, "reason": reason}

    def _severity_rank(self, severity):
        return {
            "FAIL": 0,
            "WARN": 1,
            "NOT_EVALUATED": 2,
            "PASS": 3,
        }.get(severity, 4)

    def _resilience_rating(self, score):
        if score >= 80:
            return "RESILIENT"
        if score >= 60:
            return "MODERATE"
        return "FRAGILE"

    def _number(self, value):
        if value is None:
            return 0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0
