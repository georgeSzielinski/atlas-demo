class SelfLearningAnalyticsEngine:
    """Read-only analytics over Live Paper Fund history.

    This engine measures persisted paper-fund evidence only. It does not write
    database rows and does not modify recommendations, trades, or risk limits.
    """

    DEFAULT_LIMIT = 200

    def generate(
        self,
        learning=None,
        orders=None,
        snapshots=None,
        risk_decisions=None,
        limit=None,
    ):
        limit = limit or self.DEFAULT_LIMIT
        data = self._load(
            learning=learning,
            orders=orders,
            snapshots=snapshots,
            risk_decisions=risk_decisions,
            limit=limit,
        )

        ordered_learning = self._ordered(data["learning"], "at")
        ordered_orders = self._ordered(data["orders"], "created_at")
        ordered_snapshots = self._ordered(data["snapshots"], "as_of")
        ordered_risk = self._ordered(data["risk_decisions"], "created_at")

        context = {
            "learning": ordered_learning,
            "orders": ordered_orders,
            "snapshots": ordered_snapshots,
            "risk_decisions": ordered_risk,
            "recommended_symbols": self._recommended_symbols(ordered_learning),
            "sector_by_symbol": self._sector_by_symbol(ordered_learning),
            "latest_positions": self._latest_positions(ordered_snapshots),
            "orders_by_symbol": self._orders_by_symbol(ordered_orders),
            "rejections_by_symbol": self._rejections_by_symbol(ordered_risk),
        }

        recommendation_outcomes = self.recommendation_outcomes(context)
        trade_impact = self.trade_impact(context)
        risk_blockers = self.risk_blockers(context)
        symbol_performance = self.symbol_performance(context)
        sector_performance = self.sector_performance(
            context,
            symbol_performance,
        )
        watch_patterns = self.watch_patterns(
            context,
            risk_blockers,
            symbol_performance,
            sector_performance,
        )

        return {
            "generated_at": self._latest_timestamp(
                ordered_learning,
                ordered_orders,
                ordered_snapshots,
                ordered_risk,
            ),
            "source_counts": {
                "paper_fund_learning": len(ordered_learning),
                "paper_fund_orders": len(ordered_orders),
                "paper_fund_snapshots": len(ordered_snapshots),
                "risk_decisions": len(ordered_risk),
            },
            "recommendation_outcomes": recommendation_outcomes,
            "trade_impact": trade_impact,
            "risk_blockers": risk_blockers,
            "symbol_performance": symbol_performance,
            "sector_performance": sector_performance,
            "watch_patterns": watch_patterns,
            "policy": self.policy(),
        }

    def recommendation_outcomes(self, context):
        symbols = context["recommended_symbols"]
        if not symbols:
            return {
                "status": "NOT_EVALUATED",
                "reason": "No paper-fund learning recommendations are available.",
                "items": [],
            }

        items = []
        for symbol in symbols:
            orders = context["orders_by_symbol"].get(symbol, [])
            rejections = context["rejections_by_symbol"].get(symbol, [])
            position = context["latest_positions"].get(symbol)
            cycle_ids = self._recommendation_cycles(context["learning"], symbol)
            status = "EVALUATED"
            reason = "Recommendation has paper-fund order, rejection, or position evidence."
            result = self._position_result(position)

            if not orders and not rejections and not position:
                status = "NOT_EVALUATED"
                reason = (
                    "Recommendation has no order, rejection, or open-position "
                    "evidence in paper-fund history."
                )
                result = "NOT_EVALUATED"

            items.append({
                "symbol": symbol,
                "status": status,
                "result": result,
                "reason": reason,
                "recommended_cycles": cycle_ids,
                "buy_count": len([
                    order for order in orders if order.get("side") == "BUY"
                ]),
                "sell_count": len([
                    order for order in orders if order.get("side") == "SELL"
                ]),
                "rejection_count": len(rejections),
                "latest_position_value": (
                    position.get("current_value") if position else None
                ),
                "latest_unrealized_pl": (
                    position.get("unrealized_pl") if position else None
                ),
            })

        return {
            "status": "EVALUATED",
            "items": items,
        }

    def trade_impact(self, context):
        orders = context["orders"]
        if not orders:
            return {
                "status": "NOT_EVALUATED",
                "reason": "No approved paper-fund orders are available.",
                "items": [],
            }

        items = []
        for order in orders:
            symbol = self._symbol(order)
            side = str(order.get("side", "")).upper()
            position = context["latest_positions"].get(symbol)
            item = {
                "order_id": order.get("order_id"),
                "cycle_id": order.get("cycle_id"),
                "symbol": symbol,
                "side": side,
                "quantity": order.get("quantity"),
                "fill_price": order.get("fill_price"),
                "status": order.get("status"),
                "impact_status": "NOT_EVALUATED",
                "impact": None,
                "reason": (
                    "Per-trade attribution is incomplete for this paper-fund "
                    "history."
                ),
            }

            if side == "BUY" and position and position.get("unrealized_pl") is not None:
                item["impact_status"] = "EVALUATED"
                item["impact"] = {
                    "type": "open_position_unrealized_pl",
                    "value": position.get("unrealized_pl"),
                    "current_value": position.get("current_value"),
                }
                item["reason"] = (
                    "Open-position unrealized P/L is available from the latest "
                    "paper-fund snapshot."
                )
            elif side == "SELL":
                item["reason"] = (
                    "Paper-fund snapshots store aggregate realized P/L, not "
                    "per-symbol realized attribution for this sell."
                )

            items.append(item)

        return {
            "status": "EVALUATED",
            "items": items,
        }

    def risk_blockers(self, context):
        rejected = [
            decision for decision in context["risk_decisions"]
            if str(decision.get("verdict", "")).upper() == "REJECTED"
        ]
        if not context["risk_decisions"]:
            return {
                "status": "NOT_EVALUATED",
                "reason": "No risk decisions are available.",
                "total_rejected_decisions": 0,
                "by_rule": [],
                "by_symbol": [],
                "decisions": [],
            }

        rule_map = {}
        symbol_map = {}
        decisions = []
        for decision in rejected:
            symbol = self._symbol(decision)
            rejection_checks = self._rejection_checks(decision)
            decision_rules = []
            decision_reasons = []
            for check in rejection_checks:
                rule = check.get("rule", "unknown")
                reason = check.get("reason", "")
                decision_rules.append(rule)
                decision_reasons.append(reason)
                entry = rule_map.setdefault(
                    rule,
                    {"rule": rule, "count": 0, "symbols": set(), "reasons": set()},
                )
                entry["count"] += 1
                entry["symbols"].add(symbol)
                if reason:
                    entry["reasons"].add(reason)

            symbol_entry = symbol_map.setdefault(
                symbol,
                {"symbol": symbol, "count": 0, "rules": set(), "reasons": set()},
            )
            symbol_entry["count"] += 1
            for rule in decision_rules:
                symbol_entry["rules"].add(rule)
            for reason in decision_reasons:
                if reason:
                    symbol_entry["reasons"].add(reason)

            decisions.append({
                "decision_id": decision.get("decision_id"),
                "cycle_id": decision.get("cycle_id"),
                "symbol": symbol,
                "side": decision.get("side"),
                "quantity": decision.get("quantity"),
                "rules": sorted(set(decision_rules)),
                "reasons": sorted(set(decision_reasons)),
            })

        return {
            "status": "EVALUATED",
            "total_rejected_decisions": len(rejected),
            "by_rule": [
                {
                    "rule": item["rule"],
                    "count": item["count"],
                    "symbols": sorted(item["symbols"]),
                    "reasons": sorted(item["reasons"]),
                }
                for item in sorted(rule_map.values(), key=lambda row: row["rule"])
            ],
            "by_symbol": [
                {
                    "symbol": item["symbol"],
                    "count": item["count"],
                    "rules": sorted(item["rules"]),
                    "reasons": sorted(item["reasons"]),
                }
                for item in sorted(symbol_map.values(), key=lambda row: row["symbol"])
            ],
            "decisions": sorted(
                decisions,
                key=lambda row: (row.get("symbol", ""), row.get("decision_id", "")),
            ),
        }

    def symbol_performance(self, context):
        symbols = sorted(set(
            context["recommended_symbols"]
            + list(context["orders_by_symbol"].keys())
            + list(context["rejections_by_symbol"].keys())
            + list(context["latest_positions"].keys())
        ))
        if not symbols:
            return {
                "status": "NOT_EVALUATED",
                "reason": "No symbol-level paper-fund history is available.",
                "items": [],
            }

        items = []
        for symbol in symbols:
            position = context["latest_positions"].get(symbol)
            status = "NOT_EVALUATED"
            reason = (
                "No open-position snapshot with symbol-level P/L is available."
            )
            unrealized = None
            current_value = None
            result = "NOT_EVALUATED"

            if position and position.get("unrealized_pl") is not None:
                status = "EVALUATED"
                reason = "Latest snapshot includes symbol-level unrealized P/L."
                unrealized = position.get("unrealized_pl")
                current_value = position.get("current_value")
                result = self._pl_result(unrealized)

            items.append({
                "symbol": symbol,
                "status": status,
                "result": result,
                "reason": reason,
                "sector": context["sector_by_symbol"].get(symbol),
                "current_value": current_value,
                "unrealized_pl": unrealized,
                "buy_count": len([
                    order for order in context["orders_by_symbol"].get(symbol, [])
                    if order.get("side") == "BUY"
                ]),
                "sell_count": len([
                    order for order in context["orders_by_symbol"].get(symbol, [])
                    if order.get("side") == "SELL"
                ]),
                "rejection_count": len(
                    context["rejections_by_symbol"].get(symbol, [])
                ),
            })

        evaluated = [item for item in items if item["status"] == "EVALUATED"]
        return {
            "status": "EVALUATED" if evaluated else "NOT_EVALUATED",
            "reason": (
                None if evaluated
                else "No symbol has attributable P/L in paper-fund snapshots."
            ),
            "best": self._best_symbol(evaluated),
            "worst": self._worst_symbol(evaluated),
            "items": items,
        }

    def sector_performance(self, context, symbol_performance):
        items = []
        missing = []
        by_sector = {}
        for item in symbol_performance.get("items", []):
            symbol = item["symbol"]
            sector = item.get("sector")
            if not sector:
                missing.append({
                    "symbol": symbol,
                    "status": "NOT_EVALUATED",
                    "reason": "Sector metadata is unavailable for this symbol.",
                })
                continue

            sector_entry = by_sector.setdefault(
                sector,
                {
                    "sector": sector,
                    "symbols": set(),
                    "evaluated_symbols": 0,
                    "unrealized_pl": 0,
                    "current_value": 0,
                },
            )
            sector_entry["symbols"].add(symbol)
            if item["status"] == "EVALUATED":
                sector_entry["evaluated_symbols"] += 1
                sector_entry["unrealized_pl"] += item.get("unrealized_pl") or 0
                sector_entry["current_value"] += item.get("current_value") or 0

        for entry in by_sector.values():
            evaluated = entry["evaluated_symbols"] > 0
            items.append({
                "sector": entry["sector"],
                "status": "EVALUATED" if evaluated else "NOT_EVALUATED",
                "reason": (
                    "Sector contains symbol-level P/L evidence."
                    if evaluated
                    else "Sector symbols have no attributable P/L."
                ),
                "symbols": sorted(entry["symbols"]),
                "evaluated_symbols": entry["evaluated_symbols"],
                "current_value": round(entry["current_value"], 4),
                "unrealized_pl": round(entry["unrealized_pl"], 4),
                "result": self._pl_result(entry["unrealized_pl"]) if evaluated else "NOT_EVALUATED",
            })

        evaluated_items = [item for item in items if item["status"] == "EVALUATED"]
        if not items and missing:
            status = "NOT_EVALUATED"
            reason = "Sector metadata is unavailable for paper-fund history."
        elif not evaluated_items:
            status = "NOT_EVALUATED"
            reason = "No sector has attributable symbol-level P/L."
        elif missing:
            status = "PARTIAL"
            reason = "Some symbols are missing sector metadata."
        else:
            status = "EVALUATED"
            reason = None

        return {
            "status": status,
            "reason": reason,
            "best": self._best_sector(evaluated_items),
            "worst": self._worst_sector(evaluated_items),
            "items": sorted(items, key=lambda row: row["sector"]),
            "missing_sector": sorted(missing, key=lambda row: row["symbol"]),
        }

    def watch_patterns(
        self,
        context,
        risk_blockers,
        symbol_performance,
        sector_performance,
    ):
        patterns = []

        for item in risk_blockers.get("by_symbol", []):
            if item["count"] >= 1:
                patterns.append({
                    "type": "RISK_REJECTION",
                    "status": "EVALUATED",
                    "symbol": item["symbol"],
                    "count": item["count"],
                    "rules": item["rules"],
                    "reasons": item["reasons"],
                    "message": (
                        f"{item['symbol']} was rejected by risk controls "
                        f"{item['count']} time(s)."
                    ),
                })

        for item in risk_blockers.get("by_rule", []):
            if item["count"] > 1:
                patterns.append({
                    "type": "REPEATED_RISK_BLOCKER",
                    "status": "EVALUATED",
                    "rule": item["rule"],
                    "count": item["count"],
                    "symbols": item["symbols"],
                    "reasons": item["reasons"],
                    "message": (
                        f"Risk rule {item['rule']} blocked "
                        f"{item['count']} proposed trades."
                    ),
                })

        for item in symbol_performance.get("items", []):
            if item["status"] == "EVALUATED" and (item.get("unrealized_pl") or 0) < 0:
                patterns.append({
                    "type": "NEGATIVE_SYMBOL_PL",
                    "status": "EVALUATED",
                    "symbol": item["symbol"],
                    "unrealized_pl": item["unrealized_pl"],
                    "message": (
                        f"{item['symbol']} has negative unrealized paper P/L."
                    ),
                })

        for item in sector_performance.get("missing_sector", []):
            patterns.append({
                "type": "MISSING_SECTOR_DATA",
                "status": "NOT_EVALUATED",
                "symbol": item["symbol"],
                "reason": item["reason"],
                "message": (
                    f"{item['symbol']} cannot be included in sector analytics "
                    "until sector metadata exists."
                ),
            })

        if not patterns:
            return {
                "status": "NOT_EVALUATED",
                "reason": "No deterministic paper-fund watch patterns found.",
                "items": [],
            }

        return {
            "status": "EVALUATED",
            "items": sorted(
                patterns,
                key=lambda row: (
                    row["type"],
                    row.get("symbol", ""),
                    row.get("rule", ""),
                ),
            ),
        }

    def policy(self):
        return {
            "read_only": True,
            "descriptive_only": True,
            "does_not_modify_recommendations": True,
            "does_not_modify_trades": True,
            "does_not_modify_risk_limits": True,
            "paper_only": True,
            "real_money": False,
        }

    def _load(self, learning, orders, snapshots, risk_decisions, limit):
        if learning is None:
            from database.repository import get_paper_fund_learning

            learning = get_paper_fund_learning(limit=limit)
        if orders is None:
            from database.repository import get_paper_fund_orders

            orders = get_paper_fund_orders(limit=limit)
        if snapshots is None:
            from database.repository import get_paper_fund_snapshots

            snapshots = get_paper_fund_snapshots(limit=limit)
        if risk_decisions is None:
            from database.repository import get_recent_risk_decisions

            risk_decisions = get_recent_risk_decisions(limit=limit)

        return {
            "learning": learning or [],
            "orders": orders or [],
            "snapshots": snapshots or [],
            "risk_decisions": risk_decisions or [],
        }

    def _ordered(self, rows, key):
        return sorted(rows or [], key=lambda row: (str(row.get(key, "")), str(row)))

    def _learning_summary(self, learning_entry):
        details = learning_entry.get("details", {}) or {}
        return details.get("learning_summary", details)

    def _recommended_symbols(self, learning):
        symbols = set()
        for entry in learning:
            for symbol in self._learning_summary(entry).get("recommended_symbols", []):
                if symbol:
                    symbols.add(str(symbol).upper())
        return sorted(symbols)

    def _sector_by_symbol(self, learning):
        sectors = {}
        for entry in learning:
            summary = self._learning_summary(entry)
            for allocation in summary.get("construction_targets", []):
                symbol = self._symbol(allocation)
                sector = (
                    allocation.get("sector")
                    or allocation.get("Sector")
                    or allocation.get("industry_sector")
                )
                if symbol and sector:
                    sectors[symbol] = sector
        return sectors

    def _latest_positions(self, snapshots):
        latest = {}
        for snapshot in snapshots:
            for symbol, position in (snapshot.get("positions", {}) or {}).items():
                symbol = str(symbol).upper()
                latest[symbol] = {
                    **position,
                    "symbol": symbol,
                    "snapshot_cycle_id": snapshot.get("cycle_id"),
                    "snapshot_as_of": snapshot.get("as_of") or snapshot.get("date"),
                }
        return latest

    def _orders_by_symbol(self, orders):
        grouped = {}
        for order in orders:
            grouped.setdefault(self._symbol(order), []).append(order)
        return grouped

    def _rejections_by_symbol(self, risk_decisions):
        grouped = {}
        for decision in risk_decisions:
            if str(decision.get("verdict", "")).upper() == "REJECTED":
                grouped.setdefault(self._symbol(decision), []).append(decision)
        return grouped

    def _recommendation_cycles(self, learning, symbol):
        cycles = []
        for entry in learning:
            recommended = [
                str(item).upper()
                for item in self._learning_summary(entry).get(
                    "recommended_symbols",
                    [],
                )
            ]
            if symbol in recommended:
                cycles.append(entry.get("cycle_id"))
        return sorted(cycle for cycle in cycles if cycle)

    def _rejection_checks(self, decision):
        checks = decision.get("checks", {}) or {}
        if isinstance(checks, list):
            return [
                check for check in checks
                if str(check.get("status", "")).upper() == "REJECTED"
            ]

        rejections = checks.get("rejections")
        if rejections is not None:
            return rejections

        return [
            check for check in checks.get("checks", [])
            if str(check.get("status", "")).upper() == "REJECTED"
        ]

    def _symbol(self, row):
        return str(
            row.get("symbol")
            or row.get("ticker")
            or row.get("Ticker")
            or ""
        ).upper()

    def _position_result(self, position):
        if not position or position.get("unrealized_pl") is None:
            return "NOT_EVALUATED"
        return self._pl_result(position.get("unrealized_pl"))

    def _pl_result(self, value):
        value = value or 0
        if value > 0:
            return "HELPED"
        if value < 0:
            return "HURT"
        return "FLAT"

    def _best_symbol(self, items):
        if not items:
            return None
        return max(items, key=lambda row: (row.get("unrealized_pl") or 0, row["symbol"]))

    def _worst_symbol(self, items):
        if not items:
            return None
        return min(items, key=lambda row: (row.get("unrealized_pl") or 0, row["symbol"]))

    def _best_sector(self, items):
        if not items:
            return None
        return max(
            items,
            key=lambda row: (row.get("unrealized_pl") or 0, row["sector"]),
        )

    def _worst_sector(self, items):
        if not items:
            return None
        return min(
            items,
            key=lambda row: (row.get("unrealized_pl") or 0, row["sector"]),
        )

    def _latest_timestamp(self, learning, orders, snapshots, risk_decisions):
        timestamps = []
        for row in learning:
            timestamps.append(row.get("at"))
        for row in orders:
            timestamps.append(row.get("created_at"))
        for row in snapshots:
            timestamps.append(row.get("as_of") or row.get("date"))
        for row in risk_decisions:
            timestamps.append(row.get("created_at"))
        return max([item for item in timestamps if item], default="")
