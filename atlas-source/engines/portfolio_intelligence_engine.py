from engines.risk_management_engine import RiskManagementEngine


class PortfolioIntelligenceEngine:
    """Read-only portfolio health analysis for the Live Paper Fund."""

    DEFAULT_LIMIT = 200
    CASH_PASS_RATIO = 0.20
    CASH_WARN_RATIO = 0.05
    CONCENTRATION_WARN_RATIO = 0.25
    CONCENTRATION_FAIL_RATIO = 0.40
    SECTOR_WARN_RATIO = 0.40
    SECTOR_FAIL_RATIO = 0.50

    def generate(
        self,
        state=None,
        snapshots=None,
        risk_decisions=None,
        learning=None,
        activity=None,
        limit=None,
    ):
        limit = limit or self.DEFAULT_LIMIT
        data = self._load(
            state=state,
            snapshots=snapshots,
            risk_decisions=risk_decisions,
            learning=learning,
            activity=activity,
            limit=limit,
        )
        latest_snapshot = self._latest_snapshot(data["snapshots"])
        portfolio = self._portfolio(data["state"], latest_snapshot)
        sector_map = self._sector_map(data["learning"], data["activity"])

        cash_reserve = self.cash_reserve_status(portfolio)
        concentration = self.largest_position_concentration(portfolio)
        risk_utilization = self.risk_utilization(data["risk_decisions"])
        sector_exposure = self.sector_exposure_summary(portfolio, sector_map)
        risks = self.top_portfolio_risks(
            portfolio,
            cash_reserve,
            concentration,
            risk_utilization,
            sector_exposure,
        )
        watch_items = self.suggested_watch_items(risks, portfolio)
        health_score = self.portfolio_health_score(
            portfolio,
            cash_reserve,
            concentration,
            risk_utilization,
            sector_exposure,
        )

        return {
            "generated_at": self._generated_at(data["state"], latest_snapshot),
            "portfolio_status": {
                "fund_status": data["state"].get("fund_status", "OFF"),
                "last_update": data["state"].get("last_update"),
                "latest_snapshot_at": (
                    latest_snapshot.get("as_of") if latest_snapshot else None
                ),
            },
            "portfolio_health_score": health_score,
            "cash_reserve_status": cash_reserve,
            "risk_utilization": risk_utilization,
            "largest_position_concentration": concentration,
            "sector_exposure_summary": sector_exposure,
            "top_portfolio_risks": risks,
            "suggested_watch_items": watch_items,
            "source_counts": {
                "paper_fund_snapshots": len(data["snapshots"]),
                "risk_decisions": len(data["risk_decisions"]),
                "paper_fund_learning": len(data["learning"]),
                "paper_fund_activity": len(data["activity"]),
            },
            "policy": self.policy(),
        }

    def portfolio_health_score(
        self,
        portfolio,
        cash_reserve,
        concentration,
        risk_utilization,
        sector_exposure,
    ):
        score = 100

        cash_status = cash_reserve.get("status")
        if cash_status == "FAIL":
            score -= 25
        elif cash_status == "WARN":
            score -= 10
        elif cash_status == "NOT_EVALUATED":
            score -= 5

        concentration_ratio = concentration.get("concentration_ratio")
        if concentration.get("status") == "NOT_EVALUATED":
            score -= 5
        elif concentration_ratio is not None:
            if concentration_ratio > self.CONCENTRATION_FAIL_RATIO:
                score -= 20
            elif concentration_ratio > self.CONCENTRATION_WARN_RATIO:
                score -= 10

        rejected_count = risk_utilization.get("rejected_decisions", 0)
        repeated_count = len([
            row for row in risk_utilization.get("by_rule", [])
            if row.get("rejected_count", 0) > 1
        ])
        score -= min(30, rejected_count * 8 + repeated_count * 4)

        if sector_exposure.get("status") == "NOT_EVALUATED":
            score -= 5
        else:
            largest_sector = sector_exposure.get("largest_sector") or {}
            sector_ratio = largest_sector.get("exposure_ratio")
            if sector_ratio is not None:
                if sector_ratio > self.SECTOR_FAIL_RATIO:
                    score -= 15
                elif sector_ratio > self.SECTOR_WARN_RATIO:
                    score -= 10

        if self._number(portfolio.get("unrealized_pl")) < 0:
            score -= 10
        if self._number(portfolio.get("total_return")) < 0:
            score -= 10

        return {
            "score": max(0, min(100, int(round(score)))),
            "scale": "0-100",
            "status": self._score_status(score),
            "deterministic": True,
            "reason": (
                "Score starts at 100 and deducts for cash pressure, "
                "concentration, risk rejections, sector concentration, and "
                "negative paper P/L signals."
            ),
        }

    def cash_reserve_status(self, portfolio):
        cash = portfolio.get("cash")
        portfolio_value = portfolio.get("portfolio_value")
        if cash is None or not portfolio_value:
            return {
                "status": "NOT_EVALUATED",
                "reason": "Cash or portfolio value is unavailable.",
                "cash": cash,
                "portfolio_value": portfolio_value,
                "cash_ratio": None,
                "cash_percent": None,
            }

        cash_ratio = self._number(cash) / self._number(portfolio_value)
        if cash_ratio >= self.CASH_PASS_RATIO:
            status = "PASS"
            reason = "Cash reserve is at or above the pass threshold."
        elif cash_ratio >= self.CASH_WARN_RATIO:
            status = "WARN"
            reason = "Cash reserve is below the pass threshold but above fail level."
        else:
            status = "FAIL"
            reason = "Cash reserve is below the minimum warning threshold."

        return {
            "status": status,
            "cash": round(self._number(cash), 4),
            "portfolio_value": round(self._number(portfolio_value), 4),
            "cash_ratio": round(cash_ratio, 6),
            "cash_percent": round(cash_ratio * 100, 4),
            "pass_threshold_percent": round(self.CASH_PASS_RATIO * 100, 4),
            "warn_threshold_percent": round(self.CASH_WARN_RATIO * 100, 4),
            "reason": reason,
        }

    def risk_utilization(self, risk_decisions):
        if not risk_decisions:
            return {
                "status": "NOT_EVALUATED",
                "reason": "No persisted risk decisions are available.",
                "limits": dict(RiskManagementEngine.DEFAULT_LIMITS),
                "decision_count": 0,
                "rejected_decisions": 0,
                "by_rule": [],
            }

        by_rule = {}
        rejected_decisions = 0
        for decision in risk_decisions:
            verdict = str(decision.get("verdict", "")).upper()
            if verdict == "REJECTED":
                rejected_decisions += 1
            for check in self._checks(decision):
                rule = check.get("rule", "unknown")
                status = str(check.get("status", "")).upper()
                entry = by_rule.setdefault(
                    rule,
                    {
                        "rule": rule,
                        "check_count": 0,
                        "rejected_count": 0,
                        "max_utilization": None,
                        "max_utilization_percent": None,
                        "latest_limit": None,
                        "latest_measured": None,
                        "reasons": set(),
                    },
                )
                entry["check_count"] += 1
                if status == "REJECTED":
                    entry["rejected_count"] += 1
                utilization = self._utilization(
                    check.get("limit"),
                    check.get("measured"),
                )
                if utilization is not None and (
                    entry["max_utilization"] is None
                    or utilization > entry["max_utilization"]
                ):
                    entry["max_utilization"] = utilization
                    entry["max_utilization_percent"] = round(utilization * 100, 4)
                    entry["latest_limit"] = check.get("limit")
                    entry["latest_measured"] = check.get("measured")
                if check.get("reason"):
                    entry["reasons"].add(check["reason"])

        rows = []
        for entry in by_rule.values():
            rows.append({
                "rule": entry["rule"],
                "check_count": entry["check_count"],
                "rejected_count": entry["rejected_count"],
                "max_utilization": entry["max_utilization"],
                "max_utilization_percent": entry["max_utilization_percent"],
                "latest_limit": entry["latest_limit"],
                "latest_measured": entry["latest_measured"],
                "reasons": sorted(entry["reasons"]),
                "status": (
                    "REJECTED" if entry["rejected_count"] else "EVALUATED"
                ),
            })

        return {
            "status": "EVALUATED",
            "limits": dict(RiskManagementEngine.DEFAULT_LIMITS),
            "decision_count": len(risk_decisions),
            "rejected_decisions": rejected_decisions,
            "rejection_rate_percent": round(
                rejected_decisions / len(risk_decisions) * 100,
                4,
            ),
            "by_rule": sorted(rows, key=lambda row: row["rule"]),
        }

    def largest_position_concentration(self, portfolio):
        positions = portfolio.get("positions", {})
        portfolio_value = self._number(portfolio.get("portfolio_value"))
        if not positions or portfolio_value <= 0:
            return {
                "status": "NOT_EVALUATED",
                "reason": "No positions or portfolio value are available.",
                "symbol": None,
                "current_value": None,
                "portfolio_value": portfolio.get("portfolio_value"),
                "concentration_ratio": None,
                "concentration_percent": None,
            }

        largest = max(
            positions.values(),
            key=lambda row: (self._number(row.get("current_value")), row["symbol"]),
        )
        ratio = self._number(largest.get("current_value")) / portfolio_value
        if ratio > self.CONCENTRATION_FAIL_RATIO:
            status = "FAIL"
            reason = "Largest position exceeds the concentration fail threshold."
        elif ratio > self.CONCENTRATION_WARN_RATIO:
            status = "WARN"
            reason = "Largest position exceeds the concentration warning threshold."
        else:
            status = "PASS"
            reason = "Largest position is within concentration thresholds."

        return {
            "status": status,
            "symbol": largest["symbol"],
            "current_value": round(self._number(largest.get("current_value")), 4),
            "portfolio_value": round(portfolio_value, 4),
            "concentration_ratio": round(ratio, 6),
            "concentration_percent": round(ratio * 100, 4),
            "warn_threshold_percent": round(
                self.CONCENTRATION_WARN_RATIO * 100,
                4,
            ),
            "fail_threshold_percent": round(
                self.CONCENTRATION_FAIL_RATIO * 100,
                4,
            ),
            "reason": reason,
        }

    def sector_exposure_summary(self, portfolio, sector_map):
        positions = portfolio.get("positions", {})
        portfolio_value = self._number(portfolio.get("portfolio_value"))
        if not positions or portfolio_value <= 0:
            return {
                "status": "NOT_EVALUATED",
                "reason": "No positions or portfolio value are available.",
                "items": [],
                "missing_sector": [],
                "largest_sector": None,
            }

        sectors = {}
        missing = []
        for symbol, position in sorted(positions.items()):
            sector = position.get("sector") or sector_map.get(symbol)
            value = self._number(position.get("current_value"))
            if not sector:
                missing.append({
                    "symbol": symbol,
                    "status": "NOT_EVALUATED",
                    "reason": "Sector metadata is unavailable for this position.",
                })
                continue
            entry = sectors.setdefault(
                sector,
                {"sector": sector, "symbols": [], "current_value": 0},
            )
            entry["symbols"].append(symbol)
            entry["current_value"] += value

        items = []
        for entry in sectors.values():
            ratio = entry["current_value"] / portfolio_value
            if ratio > self.SECTOR_FAIL_RATIO:
                status = "FAIL"
                reason = "Sector exposure exceeds the fail threshold."
            elif ratio > self.SECTOR_WARN_RATIO:
                status = "WARN"
                reason = "Sector exposure exceeds the warning threshold."
            else:
                status = "PASS"
                reason = "Sector exposure is within thresholds."
            items.append({
                "sector": entry["sector"],
                "status": status,
                "symbols": sorted(entry["symbols"]),
                "current_value": round(entry["current_value"], 4),
                "exposure_ratio": round(ratio, 6),
                "exposure_percent": round(ratio * 100, 4),
                "reason": reason,
            })

        items = sorted(items, key=lambda row: row["sector"])
        largest = max(
            items,
            key=lambda row: (row["exposure_ratio"], row["sector"]),
            default=None,
        )
        if not items:
            status = "NOT_EVALUATED"
            reason = "Sector metadata is unavailable for all positions."
        elif missing:
            status = "PARTIAL"
            reason = "Some positions are missing sector metadata."
        else:
            status = "EVALUATED"
            reason = "Sector exposure was calculated from construction metadata."

        return {
            "status": status,
            "reason": reason,
            "items": items,
            "missing_sector": missing,
            "largest_sector": largest,
        }

    def top_portfolio_risks(
        self,
        portfolio,
        cash_reserve,
        concentration,
        risk_utilization,
        sector_exposure,
    ):
        risks = []

        if cash_reserve["status"] in {"WARN", "FAIL"}:
            risks.append(self._risk(
                "cash_reserve",
                cash_reserve["status"],
                cash_reserve["reason"],
                cash_reserve.get("cash_percent"),
                "cash_percent",
            ))

        if concentration["status"] in {"WARN", "FAIL"}:
            risks.append(self._risk(
                "position_concentration",
                concentration["status"],
                concentration["reason"],
                concentration.get("concentration_percent"),
                "largest_position_percent",
                symbol=concentration.get("symbol"),
            ))

        for rule in risk_utilization.get("by_rule", []):
            if rule.get("rejected_count", 0) > 0:
                severity = "FAIL" if rule["rejected_count"] > 1 else "WARN"
                risks.append(self._risk(
                    "risk_rule_blocker",
                    severity,
                    f"Risk rule {rule['rule']} rejected proposed trade(s).",
                    rule["rejected_count"],
                    "rejected_count",
                    rule=rule["rule"],
                    reasons=rule.get("reasons", []),
                ))

        largest_sector = sector_exposure.get("largest_sector")
        if largest_sector and largest_sector.get("status") in {"WARN", "FAIL"}:
            risks.append(self._risk(
                "sector_concentration",
                largest_sector["status"],
                largest_sector["reason"],
                largest_sector.get("exposure_percent"),
                "sector_exposure_percent",
                sector=largest_sector.get("sector"),
            ))

        for item in sector_exposure.get("missing_sector", []):
            risks.append(self._risk(
                "missing_sector_data",
                "NOT_EVALUATED",
                item["reason"],
                None,
                "sector",
                symbol=item["symbol"],
            ))

        if self._number(portfolio.get("unrealized_pl")) < 0:
            risks.append(self._risk(
                "negative_unrealized_pl",
                "WARN",
                "Portfolio has negative unrealized paper P/L.",
                portfolio.get("unrealized_pl"),
                "unrealized_pl",
            ))

        return sorted(
            risks,
            key=lambda row: (
                self._severity_rank(row["severity"]),
                row["risk_type"],
                row.get("symbol") or row.get("rule") or row.get("sector") or "",
            ),
        )

    def suggested_watch_items(self, risks, portfolio):
        items = []
        for risk in risks:
            if risk["risk_type"] == "risk_rule_blocker":
                items.append({
                    "type": "RISK_RULE",
                    "status": risk["severity"],
                    "rule": risk.get("rule"),
                    "message": (
                        f"Watch repeated {risk.get('rule')} rejections before "
                        "the next paper-fund cycle."
                    ),
                    "reasons": risk.get("reasons", []),
                })
            elif risk["risk_type"] == "position_concentration":
                items.append({
                    "type": "POSITION_CONCENTRATION",
                    "status": risk["severity"],
                    "symbol": risk.get("symbol"),
                    "message": (
                        f"Watch largest position {risk.get('symbol')} for "
                        "concentration drift."
                    ),
                })
            elif risk["risk_type"] == "cash_reserve":
                items.append({
                    "type": "CASH_RESERVE",
                    "status": risk["severity"],
                    "message": "Watch cash reserve before approving new buys.",
                })
            elif risk["risk_type"] == "missing_sector_data":
                items.append({
                    "type": "MISSING_SECTOR_DATA",
                    "status": "NOT_EVALUATED",
                    "symbol": risk.get("symbol"),
                    "message": (
                        f"Add sector metadata for {risk.get('symbol')} before "
                        "sector exposure can be fully evaluated."
                    ),
                })
            elif risk["risk_type"] == "sector_concentration":
                items.append({
                    "type": "SECTOR_CONCENTRATION",
                    "status": risk["severity"],
                    "sector": risk.get("sector"),
                    "message": (
                        f"Watch {risk.get('sector')} sector concentration."
                    ),
                })

        if not items and portfolio.get("positions"):
            items.append({
                "type": "ROUTINE_MONITORING",
                "status": "PASS",
                "message": "Continue monitoring validated prices and allocation drift.",
            })

        return items

    def policy(self):
        return {
            "read_only": True,
            "deterministic": True,
            "descriptive_only": True,
            "does_not_modify_recommendations": True,
            "does_not_modify_trades": True,
            "does_not_modify_risk_limits": True,
            "does_not_place_orders": True,
            "broker_integration": False,
            "paper_only": True,
            "real_money": False,
        }

    def _load(self, state, snapshots, risk_decisions, learning, activity, limit):
        if state is None:
            from database.repository import get_latest_paper_fund_state

            state = get_latest_paper_fund_state()
        if snapshots is None:
            from database.repository import get_paper_fund_snapshots

            snapshots = get_paper_fund_snapshots(limit=limit)
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
            "risk_decisions": risk_decisions or [],
            "learning": learning or [],
            "activity": activity or [],
        }

    def _portfolio(self, state, latest_snapshot):
        snapshot = latest_snapshot or {}
        raw_positions = snapshot.get("positions") or state.get("positions") or {}
        positions = {}
        current_value = 0
        for symbol, raw in sorted(raw_positions.items()):
            symbol = str(symbol).upper()
            quantity = self._number(raw.get("quantity"))
            price = self._number(
                raw.get("current_price")
                or raw.get("price")
                or raw.get("cost_basis")
            )
            value = raw.get("current_value")
            if value is None:
                value = quantity * price
            value = self._number(value)
            current_value += value
            positions[symbol] = {
                **raw,
                "symbol": symbol,
                "quantity": quantity,
                "current_price": price,
                "current_value": round(value, 4),
            }

        cash = snapshot.get("cash")
        if cash is None:
            cash = state.get("cash")
        portfolio_value = snapshot.get("portfolio_value")
        if portfolio_value is None:
            portfolio_value = self._number(cash) + current_value

        return {
            "cash": None if cash is None else round(self._number(cash), 4),
            "positions": positions,
            "current_value": round(self._number(snapshot.get("current_value", current_value)), 4),
            "realized_pl": self._number(
                snapshot.get("realized_pl", state.get("realized_pl", 0))
            ),
            "unrealized_pl": self._number(snapshot.get("unrealized_pl", 0)),
            "portfolio_value": round(self._number(portfolio_value), 4),
            "daily_return": self._number(snapshot.get("daily_return", 0)),
            "total_return": self._number(snapshot.get("total_return", 0)),
        }

    def _sector_map(self, learning, activity):
        sectors = {}
        for entry in learning:
            summary = (entry.get("details", {}) or {}).get("learning_summary", {})
            for target in summary.get("construction_targets", []):
                self._record_sector(sectors, target)

        for entry in activity:
            details = entry.get("details", {}) or {}
            summary = details.get("construction_summary", {})
            for target in summary.get("recommended_allocations", []):
                self._record_sector(sectors, target)

        return sectors

    def _record_sector(self, sectors, target):
        symbol = str(
            target.get("symbol")
            or target.get("ticker")
            or target.get("Ticker")
            or ""
        ).upper()
        sector = target.get("sector") or target.get("Sector")
        if symbol and sector:
            sectors[symbol] = sector

    def _checks(self, decision):
        checks = decision.get("checks", {}) or {}
        if isinstance(checks, list):
            return checks
        return (checks.get("checks", []) or []) + (checks.get("rejections", []) or [])

    def _utilization(self, limit, measured):
        limit_number = self._optional_number(limit)
        measured_number = self._optional_number(measured)
        if limit_number is None or measured_number is None or limit_number == 0:
            return None
        return round(abs(measured_number) / abs(limit_number), 6)

    def _latest_snapshot(self, snapshots):
        if not snapshots:
            return None
        return max(
            snapshots,
            key=lambda row: str(row.get("as_of") or row.get("date") or ""),
        )

    def _generated_at(self, state, latest_snapshot):
        return (
            (latest_snapshot or {}).get("as_of")
            or state.get("updated_at")
            or state.get("last_update")
            or ""
        )

    def _risk(self, risk_type, severity, reason, measured, measured_field, **extra):
        return {
            "risk_type": risk_type,
            "severity": severity,
            "reason": reason,
            "measured": measured,
            "measured_field": measured_field,
            **extra,
        }

    def _severity_rank(self, severity):
        return {
            "FAIL": 0,
            "WARN": 1,
            "NOT_EVALUATED": 2,
            "PASS": 3,
        }.get(severity, 4)

    def _score_status(self, score):
        if score >= 80:
            return "HEALTHY"
        if score >= 60:
            return "WATCH"
        return "AT_RISK"

    def _number(self, value):
        if value is None:
            return 0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0

    def _optional_number(self, value):
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
