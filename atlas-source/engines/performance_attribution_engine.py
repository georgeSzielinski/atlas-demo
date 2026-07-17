from engines.portfolio_intelligence_engine import PortfolioIntelligenceEngine
from engines.risk_management_engine import RiskManagementEngine
from engines.self_learning_analytics_engine import SelfLearningAnalyticsEngine


class PerformanceAttributionEngine:
    """Deterministic, read-only performance attribution for the Live Paper Fund.

    The engine explains where the current paper-fund standing came from: which
    symbols, trades, and sectors drove unrealized P/L, how risk decisions and
    cash affected the portfolio, and how realized and unrealized P/L split. It
    reads persisted paper-fund evidence only. It never writes database rows and
    never modifies recommendations, trades, risk limits, orders, or portfolio
    state. When attribution cannot be computed from stored evidence, the
    relevant section returns ``NOT_EVALUATED`` with a human-readable reason.
    P/L values and counterfactuals are never fabricated.
    """

    DEFAULT_LIMIT = 200

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
        portfolio = self.intelligence._portfolio(data["state"], latest_snapshot)
        sector_map = self.intelligence._sector_map(
            data["learning"], data["activity"]
        )

        # Reuse existing paper-fund analytics so attribution composes shared
        # evidence instead of re-deriving symbol/trade/risk math.
        learning_analytics = self.learning.generate(
            learning=data["learning"],
            orders=data["orders"],
            snapshots=data["snapshots"],
            risk_decisions=data["risk_decisions"],
            limit=limit,
        )

        symbol_stats = self._symbol_stats(portfolio, sector_map)

        symbol_contribution = self.symbol_contribution(symbol_stats)
        sector_contribution = self.sector_contribution(symbol_stats)
        trade_contribution = self.trade_contribution(
            data["orders"], portfolio, learning_analytics
        )
        risk_decision_impact = self.risk_decision_impact(
            data["risk_decisions"], learning_analytics
        )
        cash_drag = self.cash_drag(portfolio, symbol_stats)
        realized_vs_unrealized = self.realized_vs_unrealized(
            portfolio, latest_snapshot, symbol_stats
        )
        portfolio_return_drivers = self.portfolio_return_drivers(
            portfolio,
            latest_snapshot,
            symbol_stats,
            realized_vs_unrealized,
            cash_drag,
        )
        attribution_confidence = self.attribution_confidence(
            portfolio,
            latest_snapshot,
            symbol_stats,
            sector_contribution,
            trade_contribution,
            risk_decision_impact,
        )

        return {
            "generated_at": self._generated_at(data["state"], latest_snapshot),
            "portfolio_status": {
                "fund_status": data["state"].get("fund_status", "OFF"),
                "last_update": data["state"].get("last_update"),
                "latest_snapshot_at": (
                    latest_snapshot.get("as_of") if latest_snapshot else None
                ),
                "attributable": symbol_stats["status"] == "EVALUATED",
            },
            "portfolio_return_drivers": portfolio_return_drivers,
            "symbol_contribution": symbol_contribution,
            "trade_contribution": trade_contribution,
            "sector_contribution": sector_contribution,
            "risk_decision_impact": risk_decision_impact,
            "cash_drag": cash_drag,
            "realized_vs_unrealized": realized_vs_unrealized,
            "attribution_confidence": attribution_confidence,
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
    # Shared symbol statistics
    # ------------------------------------------------------------------
    def _symbol_stats(self, portfolio, sector_map):
        positions = portfolio.get("positions", {})
        portfolio_value = self._number(portfolio.get("portfolio_value"))
        if not positions or portfolio_value <= 0:
            return {
                "status": "NOT_EVALUATED",
                "reason": (
                    "No positions or portfolio value are available in the "
                    "latest paper-fund snapshot."
                ),
                "items": [],
                "total_unrealized_pl": 0,
                "total_current_value": 0,
                "portfolio_value": portfolio.get("portfolio_value"),
                "missing_unrealized": [],
                "missing_sector": [],
            }

        items = []
        missing_unrealized = []
        missing_sector = []
        total_unrealized = 0.0
        total_current_value = 0.0
        for symbol, position in sorted(positions.items()):
            current_value = self._number(position.get("current_value"))
            total_current_value += current_value
            raw_unrealized = position.get("unrealized_pl")
            has_unrealized = raw_unrealized is not None
            if not has_unrealized:
                missing_unrealized.append(symbol)
            unrealized = self._number(raw_unrealized)
            if has_unrealized:
                total_unrealized += unrealized

            sector = position.get("sector") or sector_map.get(symbol)
            if not sector:
                missing_sector.append(symbol)

            items.append({
                "symbol": symbol,
                "sector": sector,
                "quantity": position.get("quantity"),
                "cost_basis": position.get("cost_basis"),
                "current_price": position.get("current_price"),
                "current_value": round(current_value, 4),
                "unrealized_pl": (
                    round(unrealized, 4) if has_unrealized else None
                ),
                "has_unrealized": has_unrealized,
            })

        return {
            "status": "EVALUATED",
            "items": items,
            "total_unrealized_pl": round(total_unrealized, 4),
            "total_current_value": round(total_current_value, 4),
            "portfolio_value": round(portfolio_value, 4),
            "missing_unrealized": missing_unrealized,
            "missing_sector": missing_sector,
        }

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------
    def symbol_contribution(self, symbol_stats):
        if symbol_stats["status"] != "EVALUATED":
            return {
                "status": "NOT_EVALUATED",
                "reason": symbol_stats["reason"],
                "items": [],
                "best": None,
                "worst": None,
            }

        total_unrealized = symbol_stats["total_unrealized_pl"]
        portfolio_value = symbol_stats["portfolio_value"]
        items = []
        for stat in symbol_stats["items"]:
            if not stat["has_unrealized"]:
                items.append({
                    "symbol": stat["symbol"],
                    "status": "NOT_EVALUATED",
                    "reason": (
                        "Snapshot does not include unrealized P/L for this "
                        "symbol."
                    ),
                    "current_value": stat["current_value"],
                    "unrealized_pl": None,
                    "contribution_to_unrealized_percent": None,
                    "contribution_to_portfolio_percent": None,
                    "result": "NOT_EVALUATED",
                })
                continue

            unrealized = stat["unrealized_pl"]
            items.append({
                "symbol": stat["symbol"],
                "status": "EVALUATED",
                "sector": stat["sector"],
                "current_value": stat["current_value"],
                "unrealized_pl": unrealized,
                "contribution_to_unrealized_percent": self._ratio_percent(
                    unrealized, total_unrealized
                ),
                "contribution_to_portfolio_percent": self._ratio_percent(
                    unrealized, portfolio_value
                ),
                "result": self._pl_result(unrealized),
            })

        evaluated = [item for item in items if item["status"] == "EVALUATED"]
        return {
            "status": "EVALUATED" if evaluated else "NOT_EVALUATED",
            "reason": (
                None if evaluated
                else "No symbol has attributable unrealized P/L."
            ),
            "total_unrealized_pl": total_unrealized,
            "best": self._best(evaluated),
            "worst": self._worst(evaluated),
            "items": items,
        }

    def sector_contribution(self, symbol_stats):
        if symbol_stats["status"] != "EVALUATED":
            return {
                "status": "NOT_EVALUATED",
                "reason": symbol_stats["reason"],
                "items": [],
                "missing_sector": [],
                "best": None,
                "worst": None,
            }

        by_sector = {}
        missing = []
        for stat in symbol_stats["items"]:
            symbol = stat["symbol"]
            sector = stat["sector"]
            if not sector:
                missing.append({
                    "symbol": symbol,
                    "status": "NOT_EVALUATED",
                    "reason": "Sector metadata is unavailable for this symbol.",
                })
                continue

            entry = by_sector.setdefault(sector, {
                "sector": sector,
                "symbols": set(),
                "evaluated_symbols": 0,
                "unrealized_pl": 0.0,
                "current_value": 0.0,
            })
            entry["symbols"].add(symbol)
            entry["current_value"] += self._number(stat["current_value"])
            if stat["has_unrealized"]:
                entry["evaluated_symbols"] += 1
                entry["unrealized_pl"] += self._number(stat["unrealized_pl"])

        total_unrealized = symbol_stats["total_unrealized_pl"]
        items = []
        for entry in by_sector.values():
            evaluated = entry["evaluated_symbols"] > 0
            items.append({
                "sector": entry["sector"],
                "status": "EVALUATED" if evaluated else "NOT_EVALUATED",
                "reason": (
                    None if evaluated
                    else "Sector symbols have no attributable unrealized P/L."
                ),
                "symbols": sorted(entry["symbols"]),
                "evaluated_symbols": entry["evaluated_symbols"],
                "current_value": round(entry["current_value"], 4),
                "unrealized_pl": (
                    round(entry["unrealized_pl"], 4) if evaluated else None
                ),
                "contribution_to_unrealized_percent": (
                    self._ratio_percent(entry["unrealized_pl"], total_unrealized)
                    if evaluated else None
                ),
                "result": (
                    self._pl_result(entry["unrealized_pl"])
                    if evaluated else "NOT_EVALUATED"
                ),
            })

        items = sorted(items, key=lambda row: row["sector"])
        evaluated_items = [item for item in items if item["status"] == "EVALUATED"]
        if not items and missing:
            status = "NOT_EVALUATED"
            reason = "Sector metadata is unavailable for all held symbols."
        elif not evaluated_items:
            status = "NOT_EVALUATED"
            reason = "No sector has attributable unrealized P/L."
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
            "items": items,
            "missing_sector": sorted(missing, key=lambda row: row["symbol"]),
        }

    def trade_contribution(self, orders, portfolio, learning_analytics):
        if not orders:
            return {
                "status": "NOT_EVALUATED",
                "reason": "No simulated paper-fund orders are available.",
                "items": [],
                "buy_count": 0,
                "sell_count": 0,
                "unattributed_sells": 0,
            }

        positions = portfolio.get("positions", {})
        trade_impact = learning_analytics.get("trade_impact", {})
        impact_by_order = {
            item.get("order_id"): item
            for item in trade_impact.get("items", [])
            if item.get("order_id") is not None
        }

        items = []
        buy_count = 0
        sell_count = 0
        unattributed_sells = 0
        for order in sorted(
            orders,
            key=lambda row: (
                str(row.get("created_at", "")),
                str(row.get("order_id", "")),
            ),
        ):
            symbol = self._symbol(order)
            side = str(order.get("side", "")).upper()
            position = positions.get(symbol)
            impact = impact_by_order.get(order.get("order_id"))
            entry = {
                "order_id": order.get("order_id"),
                "cycle_id": order.get("cycle_id"),
                "symbol": symbol,
                "side": side,
                "quantity": order.get("quantity"),
                "fill_price": order.get("fill_price"),
                "order_status": order.get("status"),
                "attribution_status": "NOT_EVALUATED",
                "contribution": None,
                "reason": (
                    "Per-trade attribution is not available for this order."
                ),
            }

            if side == "BUY":
                buy_count += 1
                if position and position.get("unrealized_pl") is not None:
                    entry["attribution_status"] = "EVALUATED"
                    entry["contribution"] = {
                        "type": "open_position_unrealized_pl",
                        "unrealized_pl": round(
                            self._number(position.get("unrealized_pl")), 4
                        ),
                        "current_value": round(
                            self._number(position.get("current_value")), 4
                        ),
                    }
                    entry["result"] = self._pl_result(
                        position.get("unrealized_pl")
                    )
                    entry["reason"] = (
                        "Buy is attributed to the open position's unrealized "
                        "P/L from the latest snapshot."
                    )
                else:
                    entry["result"] = "NOT_EVALUATED"
                    entry["reason"] = (
                        "Buy has no matching open position with unrealized P/L "
                        "in the latest snapshot."
                    )
            elif side == "SELL":
                sell_count += 1
                unattributed_sells += 1
                entry["result"] = "NOT_EVALUATED"
                entry["reason"] = (
                    "Realized P/L is not stored per symbol, so this sell's "
                    "contribution cannot be attributed without fabricating it."
                )
            else:
                entry["result"] = "NOT_EVALUATED"

            # Prefer shared trade-impact evidence when it is richer.
            if impact and impact.get("impact_status") == "EVALUATED" and (
                entry["attribution_status"] != "EVALUATED"
            ):
                entry["attribution_status"] = "EVALUATED"
                entry["contribution"] = impact.get("impact")
                entry["reason"] = impact.get("reason", entry["reason"])

            items.append(entry)

        evaluated = [
            item for item in items
            if item["attribution_status"] == "EVALUATED"
        ]
        return {
            "status": "EVALUATED" if evaluated else "NOT_EVALUATED",
            "reason": (
                None if evaluated
                else "No order could be attributed to snapshot P/L evidence."
            ),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "unattributed_sells": unattributed_sells,
            "sell_attribution_note": (
                "Sells are marked NOT_EVALUATED because snapshots store only "
                "aggregate realized P/L, not per-symbol realized attribution."
            ),
            "items": items,
        }

    def risk_decision_impact(self, risk_decisions, learning_analytics):
        risk_blockers = learning_analytics.get("risk_blockers", {})
        if not risk_decisions:
            return {
                "status": "NOT_EVALUATED",
                "reason": "No risk decisions are available.",
                "total_decisions": 0,
                "total_rejected_decisions": 0,
                "by_rule": [],
                "by_symbol": [],
                "pl_impact": self._pl_impact_not_evaluated(),
            }

        rejected = [
            decision for decision in risk_decisions
            if str(decision.get("verdict", "")).upper() == "REJECTED"
        ]

        return {
            "status": "EVALUATED",
            "total_decisions": len(risk_decisions),
            "total_rejected_decisions": len(rejected),
            "by_rule": risk_blockers.get("by_rule", []),
            "by_symbol": risk_blockers.get("by_symbol", []),
            "prevented_exposure": {
                "status": "EVALUATED" if rejected else "NONE",
                "rejected_orders": [
                    {
                        "symbol": self._symbol(decision),
                        "side": decision.get("side"),
                        "quantity": decision.get("quantity"),
                        "cycle_id": decision.get("cycle_id"),
                    }
                    for decision in sorted(
                        rejected,
                        key=lambda row: (
                            self._symbol(row),
                            str(row.get("decision_id", "")),
                        ),
                    )
                ],
                "reason": (
                    "Rejected orders describe exposure the risk gate prevented; "
                    "they were never filled."
                ),
            },
            "pl_impact": self._pl_impact_not_evaluated(),
        }

    def cash_drag(self, portfolio, symbol_stats):
        cash = portfolio.get("cash")
        portfolio_value = self._number(portfolio.get("portfolio_value"))
        if cash is None or portfolio_value <= 0:
            return {
                "status": "NOT_EVALUATED",
                "reason": (
                    "Cash or portfolio value is unavailable, so cash drag "
                    "cannot be computed."
                ),
                "cash": cash,
                "cash_weight_percent": None,
                "invested_weight_percent": None,
                "cash_pl_contribution": None,
            }

        cash_number = self._number(cash)
        cash_weight = cash_number / portfolio_value
        invested_weight = max(0.0, 1 - cash_weight)
        return {
            "status": "EVALUATED",
            "cash": round(cash_number, 4),
            "portfolio_value": round(portfolio_value, 4),
            "cash_weight_percent": round(cash_weight * 100, 4),
            "invested_weight_percent": round(invested_weight * 100, 4),
            "cash_pl_contribution": 0.0,
            "reason": (
                "Cash contributes zero P/L. In a rising market this cash weight "
                "is the fraction of the portfolio that did not participate in "
                "gains (drag); in a falling market it is protective."
            ),
        }

    def realized_vs_unrealized(self, portfolio, latest_snapshot, symbol_stats):
        if latest_snapshot is None:
            return {
                "status": "NOT_EVALUATED",
                "reason": "No paper-fund snapshot is available.",
                "realized_pl": None,
                "unrealized_pl": None,
                "total_pl": None,
            }

        realized = self._number(portfolio.get("realized_pl"))
        # Portfolio-level unrealized comes from the snapshot; symbol-level sum is
        # provided separately for cross-checking.
        snapshot_unrealized = latest_snapshot.get("unrealized_pl")
        if snapshot_unrealized is None:
            unrealized = symbol_stats.get("total_unrealized_pl")
            unrealized_source = "symbol_sum"
        else:
            unrealized = self._number(snapshot_unrealized)
            unrealized_source = "snapshot"

        total = realized + self._number(unrealized)
        return {
            "status": "EVALUATED",
            "realized_pl": round(realized, 4),
            "unrealized_pl": round(self._number(unrealized), 4),
            "unrealized_source": unrealized_source,
            "symbol_level_unrealized_pl": symbol_stats.get("total_unrealized_pl"),
            "total_pl": round(total, 4),
            "realized_share_percent": self._ratio_percent(realized, total),
            "unrealized_share_percent": self._ratio_percent(
                self._number(unrealized), total
            ),
            "realized_attribution": {
                "status": "NOT_EVALUATED",
                "reason": (
                    "Realized P/L is stored only at the portfolio level, so it "
                    "cannot be split by symbol or trade."
                ),
            },
        }

    def portfolio_return_drivers(
        self,
        portfolio,
        latest_snapshot,
        symbol_stats,
        realized_vs_unrealized,
        cash_drag,
    ):
        if symbol_stats["status"] != "EVALUATED":
            return {
                "status": "NOT_EVALUATED",
                "reason": symbol_stats["reason"],
                "drivers": [],
            }

        drivers = []
        for stat in symbol_stats["items"]:
            if not stat["has_unrealized"]:
                continue
            drivers.append({
                "driver": "symbol_unrealized_pl",
                "symbol": stat["symbol"],
                "sector": stat["sector"],
                "value": stat["unrealized_pl"],
                "result": self._pl_result(stat["unrealized_pl"]),
            })
        drivers = sorted(
            drivers,
            key=lambda row: (-abs(self._number(row["value"])), row["symbol"]),
        )

        realized = realized_vs_unrealized.get("realized_pl")
        return {
            "status": "EVALUATED",
            "period": {
                "basis": "latest_snapshot_standing",
                "as_of": latest_snapshot.get("as_of") if latest_snapshot else None,
                "reason": (
                    "Attribution reflects the current standing of the latest "
                    "snapshot (aggregate realized plus per-symbol unrealized), "
                    "not a multi-period holding attribution."
                ),
            },
            "unrealized_total": symbol_stats["total_unrealized_pl"],
            "realized_total": realized,
            "cash_contribution": cash_drag.get("cash_pl_contribution"),
            "top_positive_driver": next(
                (d for d in drivers if d["result"] == "HELPED"), None
            ),
            "top_negative_driver": next(
                (d for d in drivers if d["result"] == "HURT"), None
            ),
            "drivers": drivers,
        }

    def attribution_confidence(
        self,
        portfolio,
        latest_snapshot,
        symbol_stats,
        sector_contribution,
        trade_contribution,
        risk_decision_impact,
    ):
        limitations = []

        limitations.append({
            "area": "realized_pl_attribution",
            "status": "NOT_EVALUATED",
            "reason": (
                "Realized P/L is stored only at the portfolio level; it cannot "
                "be attributed to individual symbols or trades."
            ),
        })
        limitations.append({
            "area": "trade_sell_attribution",
            "status": "NOT_EVALUATED",
            "reason": (
                "Sell orders have no per-symbol realized P/L, so their "
                "contribution is not attributed."
            ),
        })
        limitations.append({
            "area": "risk_decision_pl_impact",
            "status": "NOT_EVALUATED",
            "reason": (
                "Rejected orders were never filled and have no counterfactual "
                "prices, so their P/L impact is not fabricated."
            ),
        })
        limitations.append({
            "area": "multi_period_return",
            "status": "NOT_EVALUATED",
            "reason": (
                "Attribution uses the latest snapshot standing; time-weighted "
                "multi-period holding attribution is not computed."
            ),
        })
        limitations.append({
            "area": "factor_attribution",
            "status": "NOT_EVALUATED",
            "reason": "No factor or correlation data is available.",
        })

        if symbol_stats.get("missing_unrealized"):
            limitations.append({
                "area": "symbol_unrealized_pl",
                "status": "PARTIAL",
                "reason": (
                    "Some held symbols lack unrealized P/L in the snapshot."
                ),
                "symbols": sorted(symbol_stats["missing_unrealized"]),
            })
        if symbol_stats.get("missing_sector"):
            limitations.append({
                "area": "sector_attribution",
                "status": "PARTIAL",
                "reason": "Some held symbols are missing sector metadata.",
                "symbols": sorted(symbol_stats["missing_sector"]),
            })

        if symbol_stats["status"] != "EVALUATED":
            level = "NONE"
            reason = (
                "No positions with attributable P/L are available in the "
                "latest snapshot."
            )
        elif (
            sector_contribution["status"] == "EVALUATED"
            and not symbol_stats.get("missing_unrealized")
        ):
            level = "MODERATE"
            reason = (
                "Symbol and sector unrealized P/L are fully attributable; "
                "realized, per-trade, and counterfactual attribution remain "
                "unavailable by design."
            )
        else:
            level = "LOW"
            reason = (
                "Only partial symbol/sector unrealized P/L is attributable; "
                "several attribution areas are not evaluable from stored data."
            )

        return {
            "status": "EVALUATED",
            "confidence_level": level,
            "reason": reason,
            "deterministic": True,
            "limitations": limitations,
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
            "does_not_place_orders": True,
        }

    def _pl_impact_not_evaluated(self):
        return {
            "status": "NOT_EVALUATED",
            "reason": (
                "Risk decisions prevent trades rather than realize P/L; their "
                "profit impact cannot be computed without counterfactual "
                "prices, which are not stored."
            ),
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

    def _generated_at(self, state, latest_snapshot):
        return (
            (latest_snapshot or {}).get("as_of")
            or state.get("updated_at")
            or state.get("last_update")
            or ""
        )

    def _ratio_percent(self, value, total):
        total_number = self._number(total)
        if total_number == 0:
            return None
        return round(self._number(value) / total_number * 100, 4)

    def _pl_result(self, value):
        value = self._number(value)
        if value > 0:
            return "HELPED"
        if value < 0:
            return "HURT"
        return "FLAT"

    def _best(self, items):
        if not items:
            return None
        return max(
            items,
            key=lambda row: (self._number(row.get("unrealized_pl")), row["symbol"]),
        )

    def _worst(self, items):
        if not items:
            return None
        return min(
            items,
            key=lambda row: (self._number(row.get("unrealized_pl")), row["symbol"]),
        )

    def _best_sector(self, items):
        if not items:
            return None
        return max(
            items,
            key=lambda row: (self._number(row.get("unrealized_pl")), row["sector"]),
        )

    def _worst_sector(self, items):
        if not items:
            return None
        return min(
            items,
            key=lambda row: (self._number(row.get("unrealized_pl")), row["sector"]),
        )

    def _symbol(self, row):
        return str(
            row.get("symbol")
            or row.get("ticker")
            or row.get("Ticker")
            or ""
        ).upper()

    def _number(self, value):
        if value is None:
            return 0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0
