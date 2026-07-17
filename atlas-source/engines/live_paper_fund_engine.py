import math
import threading
from datetime import datetime, timedelta

from engines.correlation_engine import CorrelationEngine
from engines.portfolio_construction_engine import PortfolioConstructionEngine
from engines.risk_management_engine import RiskManagementEngine


# Single-flight guard shared across engine instances so a cycle never runs
# concurrently with another. Both the autonomous path (run_due_cycle) and the
# manual override (run_manual_cycle) wrap the full cycle in this lock.
_CYCLE_LOCK = threading.Lock()


class LivePaperFundEngine:
    """Continuously running paper fund. Simulated execution only.

    The fund holds a watchlist and virtual cash, and each cycle: checks market
    status, refreshes validated prices, generates deterministic recommendation
    snapshots, computes target allocations, creates simulated virtual orders,
    fills them at current validated prices, snapshots the portfolio, and
    records activity and learning entries.

    Safety: no broker is connected, no real money exists, fills are simulated
    only, and real (non-mock, non-fallback, validated) market prices are
    required — the cycle fails loudly into ERROR instead of using fake prices.
    Recommendation engine behavior is never changed by this layer.
    """

    MODE = "live_paper_fund"
    STATES = ["OFF", "READY", "RUNNING", "PAUSED", "ERROR"]
    DEFAULT_STARTING_CASH = 100000
    DEFAULT_INTERVAL_MINUTES = 30
    REBALANCE_THRESHOLD = 0.01
    DISALLOWED_PRICE_PROVIDERS = {"mock", "unknown", ""}
    # Providers that must never drive automatic cycles. Mock/test/unknown or a
    # missing provider are unsafe: automatic operation requires a real provider.
    UNSAFE_AUTO_PROVIDERS = {"mock", "unknown", "test", ""}
    CYCLE_IN_PROGRESS_REASON = "another cycle is already running"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self, watchlist, starting_cash=None, interval_minutes=None, now=None):
        tickers = sorted({
            str(ticker).strip().upper()
            for ticker in (watchlist or [])
            if str(ticker).strip()
        })
        if not tickers:
            raise ValueError("Live paper fund requires at least one watchlist ticker.")

        try:
            cash = float(starting_cash or self.DEFAULT_STARTING_CASH)
        except (TypeError, ValueError):
            cash = float(self.DEFAULT_STARTING_CASH)
        if cash <= 0:
            raise ValueError("Live paper fund starting cash must be positive.")

        try:
            interval = int(interval_minutes or self.DEFAULT_INTERVAL_MINUTES)
        except (TypeError, ValueError):
            interval = self.DEFAULT_INTERVAL_MINUTES
        interval = max(1, interval)

        moment = self._moment(now)
        state = {
            "updated_at": moment.isoformat(),
            "fund_status": "READY",
            "watchlist": tickers,
            "starting_cash": cash,
            "cash": cash,
            "positions": {},
            "realized_pl": 0,
            "interval_minutes": interval,
            "last_update": None,
            "next_update": moment.isoformat(),
            "last_error": None,
            "price_provider": None,
            "policy": self.policy(),
        }
        self._save_state(state)
        self._activity(
            moment,
            None,
            "FUND_STARTED",
            f"Live paper fund started with watchlist {', '.join(tickers)} "
            f"and ${cash:,.0f} virtual cash. Simulated only.",
            {"watchlist": tickers, "starting_cash": cash, "interval_minutes": interval},
        )

        return state

    def pause(self, now=None):
        return self._transition(now, "PAUSED", "FUND_PAUSED", "Live paper fund paused.")

    def resume(self, now=None):
        return self._transition(now, "READY", "FUND_RESUMED", "Live paper fund resumed.")

    def stop(self, now=None):
        return self._transition(
            now,
            "OFF",
            "FUND_STOPPED",
            "Live paper fund stopped. Records are kept for review.",
        )

    # ------------------------------------------------------------------
    # Cycle loop
    # ------------------------------------------------------------------
    def run_cycle(self, manager=None, now=None):
        from database.repository import get_latest_paper_fund_state

        state = get_latest_paper_fund_state()
        if state is None or state.get("fund_status") == "OFF":
            raise ValueError("Live paper fund is not started. Start it first.")
        if state.get("fund_status") == "PAUSED":
            raise ValueError("Live paper fund is paused. Resume it to run a cycle.")

        if manager is None:
            from market.market_data_manager import MarketDataManager

            manager = MarketDataManager()

        moment = self._moment(now)
        cycle_id = f"fund-{moment.strftime('%Y%m%d%H%M%S')}"
        watchlist = state["watchlist"]
        self._activity(
            moment,
            cycle_id,
            "CYCLE_STARTED",
            f"Analysis cycle started for {len(watchlist)} watchlist tickers.",
            {"watchlist": watchlist},
        )

        market_status = manager.market_status(self._market_moment(moment))
        self._activity(
            moment,
            cycle_id,
            "MARKET_STATUS",
            f"Market session is {market_status.get('session', 'unknown')}.",
            {"is_open": market_status.get("is_open")},
        )

        price_report = manager.latest_prices(watchlist)
        failure = self._price_failure(price_report)
        if failure:
            return self._fail_cycle(state, moment, cycle_id, market_status, failure)

        prices = price_report["prices"]
        provider = self._dominant_provider(price_report)
        self._activity(
            moment,
            cycle_id,
            "PRICES_REFRESHED",
            f"Validated prices refreshed from {provider} for {len(prices)} tickers.",
            {"provider": provider, "validated": True, "fallback_used": False},
        )

        recommendations = self._recommendation_snapshots(watchlist, prices, moment)
        stored_count = sum(
            1 for item in recommendations
            if item.get("status") == "STORED_RECOMMENDATION"
        )
        self._activity(
            moment,
            cycle_id,
            "SNAPSHOTS_GENERATED",
            f"Generated {len(recommendations)} recommendation snapshots "
            "for deterministic portfolio construction.",
            {
                "tickers": watchlist,
                "stored_recommendations": stored_count,
                "hold_fallbacks": len(recommendations) - stored_count,
            },
        )

        construction = self._construction_report(state, prices, recommendations)
        construction_summary = self._construction_summary(construction)
        self._save_construction_report(construction)
        self._activity(
            moment,
            cycle_id,
            "CONSTRUCTION_BUILT",
            "Portfolio construction produced deterministic target allocations.",
            {"construction_summary": construction_summary},
        )

        orders, risk_summary = self._rebalance_orders(
            state,
            prices,
            provider,
            moment,
            cycle_id,
            construction,
            manager,
        )
        for order in orders:
            order["recommendation_id"] = self._exact_order_recommendation_id(
                order, recommendations
            )
            self._save_order(order)
        self._activity(
            moment,
            cycle_id,
            "ORDERS_FILLED",
            (
                f"Proposed {risk_summary['proposed']} orders; approved "
                f"{risk_summary['approved']} and filled {len(orders)} "
                "simulated virtual orders at validated prices. No broker involved."
                if orders
                else (
                    f"Proposed {risk_summary['proposed']} orders; approved 0 "
                    f"and rejected {risk_summary['rejected']}. No simulated "
                    "orders filled."
                    if risk_summary["proposed"]
                    else "No rebalancing needed; portfolio is within target allocation."
                )
            ),
            {
                "orders": len(orders),
                "risk_summary": risk_summary,
                "construction_summary": construction_summary,
            },
        )

        snapshot = self._snapshot(state, prices, provider, moment, cycle_id)
        self._save_snapshot(snapshot)
        self._activity(
            moment,
            cycle_id,
            "PORTFOLIO_UPDATED",
            f"Paper portfolio value ${snapshot['portfolio_value']:,.2f} "
            f"(total return {snapshot['total_return']}%).",
            {
                "portfolio_value": snapshot["portfolio_value"],
                "total_return": snapshot["total_return"],
            },
        )

        learning = self._learning_entry(
            recommendations,
            market_status,
            construction_summary,
            orders,
            risk_summary,
            snapshot,
            prices,
            moment,
            cycle_id,
        )
        self._save_learning(learning)
        self._activity(
            moment,
            cycle_id,
            "ANALYTICS_UPDATED",
            "Fund analytics and learning log updated from this cycle.",
            {"lesson": learning["lesson"]},
        )

        next_update = moment + timedelta(minutes=state["interval_minutes"])
        new_state = {
            **state,
            "updated_at": moment.isoformat(),
            "fund_status": "RUNNING",
            "last_update": moment.isoformat(),
            "next_update": next_update.isoformat(),
            "last_error": None,
            "price_provider": provider,
            "policy": self.policy(),
        }
        self._save_state(new_state)
        self._activity(
            moment,
            cycle_id,
            "CYCLE_COMPLETED",
            f"Cycle completed. Next scheduled update {next_update.isoformat()}.",
            {"next_update": next_update.isoformat()},
        )

        return {
            "cycle_id": cycle_id,
            "cycle_status": "COMPLETED",
            "fund_status": "RUNNING",
            "market_status": market_status,
            "price_provider": provider,
            "price_backed": True,
            "validated": True,
            "recommendations": recommendations,
            "construction_summary": construction_summary,
            "orders": orders,
            "risk_summary": risk_summary,
            "snapshot": snapshot,
            "learning": learning,
            "last_update": moment.isoformat(),
            "next_update": next_update.isoformat(),
            "error": None,
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Automatic operation
    # ------------------------------------------------------------------
    def is_cycle_due(self, state, now=None):
        """Whether a scheduled cycle should run now.

        Due only when the fund is READY or RUNNING and the stored next_update
        has been reached. A fund with no next_update has never cycled and is
        due. OFF/PAUSED/ERROR are never due.
        """
        if not state:
            return False
        if state.get("fund_status") not in {"READY", "RUNNING"}:
            return False

        next_update = state.get("next_update")
        if not next_update:
            return True

        try:
            due_at = datetime.fromisoformat(str(next_update))
        except (TypeError, ValueError):
            return True

        return self._moment(now) >= due_at

    def can_auto_run(self, manager=None):
        """Whether the configured market data provider is safe to automate.

        Mock, test, unknown, or missing providers are unsafe: automatic
        operation requires a real market data provider so cycles are backed by
        validated real prices instead of deterministic mock data.
        """
        provider = self._configured_provider(manager)
        if not provider:
            return False

        name = str(provider).strip().lower()
        if name in self.UNSAFE_AUTO_PROVIDERS:
            return False

        return not any(token in name for token in ("mock", "test", "unknown"))

    def run_due_cycle(self, manager=None, now=None):
        """Run a cycle only if it is safe and due; otherwise skip without writes.

        Skips (returning {"status": "SKIPPED", "reason": ...} and writing
        nothing) when automation is disabled, another cycle is already running,
        the provider is unsafe, the fund is off/paused/in error, the cycle is
        not due, or the market is closed. When it does run, it delegates to the
        unchanged run_cycle, which alone advances next_update and persists
        records.
        """
        from core import settings
        from database.repository import get_latest_paper_fund_state

        if not settings.AUTO_FUND_ENABLED:
            return self._skip("automatic paper fund operation is disabled")

        if manager is None:
            from market.market_data_manager import MarketDataManager

            manager = MarketDataManager()

        if not _CYCLE_LOCK.acquire(blocking=False):
            return self._skip(self.CYCLE_IN_PROGRESS_REASON)

        try:
            if not self.can_auto_run(manager):
                return self._skip(
                    "configured market data provider is unsafe for automatic "
                    "operation"
                )

            moment = self._moment(now)
            state = get_latest_paper_fund_state()
            fund_status = (state or {}).get("fund_status", "OFF")
            if state is None or fund_status == "OFF":
                return self._skip("fund is off")
            if fund_status == "PAUSED":
                return self._skip("fund is paused")
            if fund_status == "ERROR":
                # ERROR must never be a dead end for unattended operation:
                # after one interval of cooldown the fund re-arms itself and
                # the tick continues through the normal gates. OFF and PAUSED
                # stay manual — they record human intent.
                recovered = self._recover_error_state(state, moment)
                if recovered is None:
                    return self._skip(
                        "fund is in an error state; automatic recovery is "
                        "scheduled after the cycle interval cooldown"
                    )
                state = recovered

            if not self.is_cycle_due(state, moment):
                return self._skip("cycle is not due yet")

            if settings.AUTO_FUND_MARKET_HOURS_ONLY and not manager.market_status(
                self._market_moment(moment)
            ).get("is_open"):
                return self._skip("market is closed")

            result = self.run_cycle(manager=manager, now=moment)
            if (result or {}).get("cycle_status") == "FAILED":
                # Every autonomous failure schedules a retry instead of
                # latching ERROR: run_cycle already recorded the failure
                # loudly, and the next due tick tries again.
                return self._recover_failed_cycle(state, result, moment)
            return result
        finally:
            _CYCLE_LOCK.release()

    def run_manual_cycle(self, manager=None, now=None):
        """Manual override with the same single-flight guard as autonomous ticks.

        Delegates to the unchanged run_cycle, but only after acquiring the
        shared cycle lock without blocking: if any other cycle (manual or
        scheduled) is already running, it returns the standard
        {"status": "SKIPPED", "reason": CYCLE_IN_PROGRESS_REASON} immediately
        instead of overlapping it. Unlike run_due_cycle it applies none of the
        automation gates (enabled/due/market-hours) — it is the human
        "run one cycle now" path, and run_cycle itself still enforces every
        price-validation and risk gate.
        """
        if not _CYCLE_LOCK.acquire(blocking=False):
            return self._skip(self.CYCLE_IN_PROGRESS_REASON)

        try:
            return self.run_cycle(manager=manager, now=now)
        finally:
            _CYCLE_LOCK.release()

    def _skip(self, reason):
        return {"status": "SKIPPED", "reason": reason}

    def _market_moment(self, moment):
        """The real instant for market-session checks.

        Fund timestamps are naive LOCAL wall-clock throughout (stored,
        compared, and displayed as such), but the exchange calendar interprets
        naive input as New York wall-clock — so on a machine outside Eastern
        time a naive `datetime.now()` asks the calendar about the wrong
        instant (e.g. 20:00 Warsaw read as 20:00 ET -> "closed" while the
        market is open). Attaching the system-local timezone makes the
        calendar evaluate the actual instant, which is exactly what the
        preflight check (market_status with no argument) already does. Aware
        moments pass through unchanged.
        """
        if moment.tzinfo is not None:
            return moment
        return moment.astimezone()

    def _configured_provider(self, manager):
        if manager is not None:
            return getattr(manager, "provider_name", None)

        import os

        from core.settings import DATA_PROVIDER

        return os.environ.get("MARKET_DATA_PROVIDER") or DATA_PROVIDER

    def _recover_error_state(self, state, moment):
        """Re-arm an ERROR fund once the cycle-interval cooldown has passed.

        Returns the recovered state (persisted, with an activity record), or
        None while the cooldown is still running. Only ERROR is recovered;
        OFF and PAUSED are human decisions and are never auto-resumed.
        """
        interval = timedelta(
            minutes=state.get("interval_minutes") or self.DEFAULT_INTERVAL_MINUTES
        )
        errored_at = self._parse_time(state.get("updated_at"))
        if errored_at is not None and moment - errored_at < interval:
            return None

        recovered_state = {
            **state,
            "updated_at": moment.isoformat(),
            "fund_status": "RUNNING" if state.get("last_update") else "READY",
            "next_update": moment.isoformat(),
            "policy": self.policy(),
        }
        self._save_state(recovered_state)
        self._activity(
            moment,
            None,
            "AUTO_RECOVERY_FROM_ERROR",
            (
                "Automatic recovery re-armed the paper fund after an error "
                "cooldown; the previous error is kept on record and the next "
                "due cycle will retry. Paper only; no trades were changed."
            ),
            {
                "recovery_status": "re_armed",
                "previous_error": state.get("last_error"),
                "fund_status": recovered_state["fund_status"],
            },
        )
        return recovered_state

    def recover_after_failure(self, now=None):
        """Re-arm the fund after a failed manual cycle latched ERROR.

        The manual /paper-fund/cycle path bypasses run_due_cycle, so its
        failures used to leave the fund in ERROR until a human resumed it —
        killing autonomous operation. This runs the same recovery pass the
        autonomous path uses. It only acts on ERROR; OFF/PAUSED/READY/RUNNING
        are returned unchanged.
        """
        from database.repository import get_latest_paper_fund_state

        state = get_latest_paper_fund_state()
        if not state or state.get("fund_status") != "ERROR":
            return {
                "status": "SKIPPED",
                "reason": "fund is not in an error state",
                "fund_status": (state or {}).get("fund_status", "OFF"),
            }

        moment = self._moment(now)
        next_update = moment + timedelta(
            minutes=state.get("interval_minutes") or self.DEFAULT_INTERVAL_MINUTES
        )
        recovered_state = {
            **state,
            "updated_at": moment.isoformat(),
            "fund_status": "RUNNING" if state.get("last_update") else "READY",
            "next_update": next_update.isoformat(),
            "policy": self.policy(),
        }
        self._save_state(recovered_state)
        self._activity(
            moment,
            None,
            "AUTO_RECOVERY_SCHEDULED",
            (
                "Manual cycle failure recovered: the paper fund is re-armed "
                "and the next scheduled tick will retry. Paper only; no "
                "trades were changed."
            ),
            {
                "recovery_status": "scheduled_retry",
                "previous_error": state.get("last_error"),
                "next_update": next_update.isoformat(),
            },
        )
        return {
            "status": "RECOVERED",
            "fund_status": recovered_state["fund_status"],
            "next_update": next_update.isoformat(),
            "previous_error": state.get("last_error"),
        }

    def _recover_failed_cycle(self, previous_state, result, moment):
        """Keep unattended operation eligible for the next scheduled retry.

        run_cycle records the failed attempt loudly. Automatic operation then
        transitions back to RUNNING/READY and advances next_update so the next
        scheduler tick can retry instead of requiring manual recovery.
        """
        next_update = moment + timedelta(
            minutes=previous_state.get("interval_minutes") or self.DEFAULT_INTERVAL_MINUTES
        )
        recovered_state = {
            **previous_state,
            "updated_at": moment.isoformat(),
            "fund_status": (
                "RUNNING" if previous_state.get("last_update") else "READY"
            ),
            "last_error": result.get("error"),
            "next_update": next_update.isoformat(),
            "policy": self.policy(),
        }
        self._save_state(recovered_state)
        self._activity(
            moment,
            result.get("cycle_id"),
            "AUTO_RECOVERY_SCHEDULED",
            (
                "Automatic paper-fund cycle failed on transient market data; "
                "Atlas scheduled the next paper-only retry without changing "
                "recommendations, risk limits, or trades."
            ),
            {
                "recovery_status": "scheduled_retry",
                "next_update": next_update.isoformat(),
                "error": result.get("error"),
            },
        )
        return {
            **result,
            "cycle_status": "RECOVERING",
            "fund_status": recovered_state["fund_status"],
            "next_update": next_update.isoformat(),
            "recovery": {
                "status": "scheduled_retry",
                "reason": result.get("error"),
                "next_update": next_update.isoformat(),
                "paper_only": True,
                "real_money": False,
            },
        }

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    def status(self):
        from database.repository import (
            get_latest_paper_fund_state,
            get_paper_fund_activity,
            get_paper_fund_learning,
            get_paper_fund_orders,
            get_paper_fund_snapshots,
        )

        state = get_latest_paper_fund_state()
        snapshots = get_paper_fund_snapshots(limit=60)
        orders = get_paper_fund_orders(limit=100)
        activity = get_paper_fund_activity(limit=100)
        learning = get_paper_fund_learning(limit=50)
        cycle_state = self._cycle_state(state, activity)

        return {
            "mode": self.MODE,
            "fund_status": (state or {}).get("fund_status", "OFF"),
            "watchlist": (state or {}).get("watchlist", []),
            "starting_cash": (state or {}).get("starting_cash"),
            "cash": (state or {}).get("cash"),
            "realized_pl": (state or {}).get("realized_pl"),
            "interval_minutes": (state or {}).get("interval_minutes"),
            "last_update": (state or {}).get("last_update"),
            "next_update": (state or {}).get("next_update"),
            "last_error": (state or {}).get("last_error"),
            "price_provider": (state or {}).get("price_provider"),
            "open_positions": (state or {}).get("positions", {}),
            "latest_snapshot": snapshots[0] if snapshots else None,
            "snapshots": snapshots,
            "virtual_orders": orders[:50],
            "activity_log": activity[:50],
            "learning_log": learning[:20],
            "cycle_state": cycle_state,
            "trading_history": self._trading_history(snapshots, orders),
            "cycle_journal": self._cycle_journal(learning, activity),
            "policy": self.policy(),
        }

    def policy(self):
        return {
            "mode": self.MODE,
            "paper_only": True,
            "broker_integration": False,
            "broker_disabled": True,
            "real_money": False,
            "execution": "simulated_only",
            "automatic_execution": True,
            "automatic_execution_scope": "simulated_paper_only_when_enabled",
            "manual_approval_required_for_simulated_trades": False,
            "changes_recommendation_behavior": False,
            "human_approval_required_for_real_trading": True,
        }

    # ------------------------------------------------------------------
    # Status analytics (read-only projections from persisted fund history)
    # ------------------------------------------------------------------
    def _cycle_state(self, state, activity):
        events = [entry for entry in (activity or []) if entry.get("cycle_id")]
        if not events:
            return {
                "state": "Idle",
                "cycle_id": None,
                "started_at": None,
                "last_event_at": None,
                "duration_seconds": 0,
                "last_successful_cycle_time": (state or {}).get("last_update"),
                "recovery_status": None,
            }

        cycle_id = events[0]["cycle_id"]
        cycle_events = [
            entry for entry in events if entry.get("cycle_id") == cycle_id
        ]
        event_types = {entry.get("activity_type") for entry in cycle_events}
        newest = cycle_events[0]
        oldest = cycle_events[-1]
        started_at = next(
            (
                entry.get("at")
                for entry in reversed(cycle_events)
                if entry.get("activity_type") == "CYCLE_STARTED"
            ),
            oldest.get("at"),
        )
        last_event_at = newest.get("at")
        duration = self._duration_seconds(started_at, last_event_at)

        if "CYCLE_COMPLETED" in event_types:
            state_name = "Complete"
        elif "CYCLE_FAILED" in event_types:
            state_name = "Recovery"
        elif "ANALYTICS_UPDATED" in event_types:
            state_name = "Learning"
        elif "PORTFOLIO_UPDATED" in event_types:
            state_name = "Learning"
        elif "ORDERS_FILLED" in event_types:
            state_name = "Executing Paper Orders"
        elif "CORRELATION_EVALUATED" in event_types:
            state_name = "Risk"
        elif "CONSTRUCTION_BUILT" in event_types:
            state_name = "Risk"
        elif "SNAPSHOTS_GENERATED" in event_types:
            state_name = "Portfolio Construction"
        elif "PRICES_REFRESHED" in event_types:
            state_name = "Research"
        elif "MARKET_STATUS" in event_types:
            state_name = "Gathering Data"
        else:
            state_name = "Idle"

        recovery = next(
            (
                entry for entry in cycle_events
                if entry.get("activity_type") == "AUTO_RECOVERY_SCHEDULED"
            ),
            None,
        )

        return {
            "state": state_name,
            "cycle_id": cycle_id,
            "started_at": started_at,
            "last_event_at": last_event_at,
            "duration_seconds": duration,
            "last_successful_cycle_time": (state or {}).get("last_update"),
            "recovery_status": (
                (recovery.get("details") or {}).get("recovery_status")
                if recovery else None
            ),
        }

    def _trading_history(self, snapshots, orders):
        rows = list(reversed(snapshots or []))
        equity_curve = [
            {
                "date": row.get("as_of") or row.get("date"),
                "portfolio_value": row.get("portfolio_value"),
                "cash": row.get("cash"),
                "current_value": row.get("current_value"),
                "daily_return": row.get("daily_return"),
                "total_return": row.get("total_return"),
            }
            for row in rows
            if row.get("portfolio_value") is not None
        ]
        values = [
            (self._parse_time(row["date"]), float(row["portfolio_value"]))
            for row in equity_curve
            if row.get("date") and row.get("portfolio_value") is not None
        ]
        values = [item for item in values if item[0] is not None]

        returns = []
        for index in range(1, len(values)):
            previous = values[index - 1][1]
            current = values[index][1]
            if previous:
                returns.append((current - previous) / previous)

        return {
            "equity_curve": equity_curve,
            "cash_history": [
                {"date": row["date"], "cash": row["cash"]}
                for row in equity_curve
                if row.get("cash") is not None
            ],
            "daily_pl": self._period_pl(values, "day"),
            "weekly_pl": self._period_pl(values, "week"),
            "monthly_pl": self._period_pl(values, "month"),
            "statistics": {
                "cagr": self._cagr(values),
                "drawdown": self._drawdown(values),
                "win_rate": self._win_rate(returns),
                "sharpe": self._sharpe(returns),
            },
            "source_counts": {
                "snapshots": len(snapshots or []),
                "orders": len(orders or []),
            },
        }

    def _cycle_journal(self, learning, activity):
        if not learning:
            return {
                "status": "NOT_EVALUATED",
                "reason": "No completed paper-fund cycle learning entries exist yet.",
                "latest": None,
            }
        latest = learning[0]
        details = latest.get("details") or {}
        journal = details.get("cycle_journal")
        if journal:
            return {"status": "EVALUATED", "latest": journal}
        summary = details.get("learning_summary") or {}
        return {
            "status": "EVALUATED",
            "latest": {
                "cycle_id": latest.get("cycle_id"),
                "completed_at": latest.get("at"),
                "market_conditions": {"status": "NOT_EVALUATED"},
                "recommendations_considered": summary.get("recommended_symbols", []),
                "accepted_trades": (
                    summary.get("bought_symbols", []) + summary.get("sold_symbols", [])
                ),
                "rejected_trades": summary.get("rejected_orders", []),
                "portfolio_changes": summary.get("portfolio", {}),
                "learning_summary": summary,
                "execution_time": self._cycle_execution_time(
                    latest.get("cycle_id"), activity
                ),
            },
        }

    def _period_pl(self, values, period):
        if len(values) < 2:
            return {
                "status": "NOT_EVALUATED",
                "reason": "At least two snapshots are required.",
                "items": [],
            }
        buckets = {}
        for moment, value in values:
            if period == "day":
                key = moment.strftime("%Y-%m-%d")
            elif period == "week":
                year, week, _ = moment.isocalendar()
                key = f"{year}-W{week:02d}"
            else:
                key = moment.strftime("%Y-%m")
            bucket = buckets.setdefault(key, {"start": value, "end": value})
            bucket["end"] = value

        items = []
        for key, bucket in sorted(buckets.items()):
            change = round(bucket["end"] - bucket["start"], 4)
            items.append({
                "period": key,
                "start_value": round(bucket["start"], 4),
                "end_value": round(bucket["end"], 4),
                "pl": change,
                "return_percent": self._percentage(bucket["end"], bucket["start"]),
            })
        return {"status": "EVALUATED", "items": items}

    def _cagr(self, values):
        if len(values) < 2:
            return self._not_enough_history("CAGR requires at least two snapshots.")
        start_date, start_value = values[0]
        end_date, end_value = values[-1]
        days = (end_date - start_date).days
        if days < 30 or start_value <= 0:
            return self._not_enough_history(
                "CAGR requires at least 30 days of positive portfolio history."
            )
        years = days / 365.25
        return {
            "status": "EVALUATED",
            "value": round(((end_value / start_value) ** (1 / years) - 1) * 100, 4),
        }

    def _drawdown(self, values):
        if len(values) < 2:
            return self._not_enough_history("Drawdown requires at least two snapshots.")
        peak = values[0][1]
        max_drawdown = 0.0
        for _, value in values:
            peak = max(peak, value)
            if peak:
                max_drawdown = min(max_drawdown, (value - peak) / peak)
        return {"status": "EVALUATED", "value": round(max_drawdown * 100, 4)}

    def _win_rate(self, returns):
        if not returns:
            return self._not_enough_history("Win rate requires at least two snapshots.")
        wins = len([value for value in returns if value > 0])
        return {
            "status": "EVALUATED",
            "value": round(wins / len(returns) * 100, 4),
            "periods": len(returns),
        }

    def _sharpe(self, returns):
        if len(returns) < 3:
            return self._not_enough_history(
                "Sharpe ratio requires at least three return periods."
            )
        mean = sum(returns) / len(returns)
        variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
        stddev = math.sqrt(variance)
        if stddev == 0:
            return self._not_enough_history(
                "Sharpe ratio requires non-zero return volatility."
            )
        return {
            "status": "EVALUATED",
            "value": round((mean / stddev) * math.sqrt(252), 4),
            "periods": len(returns),
        }

    def _not_enough_history(self, reason):
        return {"status": "NOT_EVALUATED", "reason": reason, "value": None}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _price_failure(self, price_report):
        providers = {
            result.get("provider", "unknown")
            for result in price_report.get("results", {}).values()
        }
        problems = []

        if not price_report.get("validated"):
            problems.append("market prices failed validation")
        if price_report.get("fallback_used"):
            problems.append("price provider fallback was used")
        if providers & self.DISALLOWED_PRICE_PROVIDERS:
            problems.append("mock/demo prices are not allowed in the live paper fund")

        if not problems:
            return None

        return (
            "Validated real market prices unavailable: "
            + "; ".join(problems)
            + ". Configure a real market data provider "
            "(for example MARKET_DATA_PROVIDER=yahoo) and try again."
        )

    def _fail_cycle(self, state, moment, cycle_id, market_status, failure):
        failed_state = {
            **state,
            "updated_at": moment.isoformat(),
            "fund_status": "ERROR",
            "last_error": failure,
            "policy": self.policy(),
        }
        self._save_state(failed_state)
        self._activity(
            moment,
            cycle_id,
            "CYCLE_FAILED",
            failure,
            {"fund_status": "ERROR"},
        )

        return {
            "cycle_id": cycle_id,
            "cycle_status": "FAILED",
            "fund_status": "ERROR",
            "market_status": market_status,
            "price_provider": None,
            "price_backed": False,
            "validated": False,
            "recommendations": [],
            "orders": [],
            "snapshot": None,
            "learning": None,
            "error": failure,
            "policy": self.policy(),
        }

    # Stored recommendations older than this are treated as missing so stale
    # research never masquerades as a current view.
    STORED_RECOMMENDATION_MAX_AGE_DAYS = 7

    # Signal fields copied from a stored recommendation record onto the cycle's
    # research snapshot (never onto the construction input, which stays HOLD).
    STORED_RECOMMENDATION_SIGNALS = (
        "confidence",
        "overall_conviction",
        "overall_score",
        "technical_score",
        "fundamental_score",
        "forecast_score",
        "news_confidence",
        "signal_quality_score",
        "committee_agreement",
        "stability_score",
        "knowledge_score",
    )

    def _recommendation_snapshots(self, watchlist, prices, moment):
        """Research snapshots for the cycle, one per watchlist ticker.

        When a fresh stored recommendation exists (written by explicit
        watchlist research runs), the snapshot carries its real deterministic
        action and signal scores for the activity/learning record. Otherwise
        it falls back to the conservative HOLD shape with a clear reason.

        Trading behavior is unchanged either way: _construction_recommendations
        maps every snapshot to the same HOLD-shaped construction input (ticker,
        HOLD, sector defaults, cycle price), so portfolio construction, risk,
        and orders never see stored actions or scores.
        """
        snapshots = []
        for ticker in watchlist:
            stored, miss_reason = self._stored_recommendation(ticker, moment)
            if stored:
                snapshots.append({
                    "ticker": ticker,
                    "action": stored.get("action") or "HOLD",
                    "price": prices.get(ticker),
                    **{
                        signal: stored.get(signal)
                        for signal in self.STORED_RECOMMENDATION_SIGNALS
                    },
                    "recommendation_id": stored.get("id"),
                    "run_id": stored.get("run_id"),
                    "recommended_at": stored.get("run_time"),
                    "reason": (
                        "Latest stored deterministic recommendation record "
                        "(research only; construction input remains HOLD)."
                    ),
                    "status": "STORED_RECOMMENDATION",
                    "as_of": moment.isoformat(),
                })
            else:
                snapshots.append({
                    "ticker": ticker,
                    "action": "HOLD",
                    "price": prices.get(ticker),
                    "reason": (
                        f"No usable stored recommendation ({miss_reason}); "
                        "defaulting to HOLD. Run a watchlist research run to "
                        "generate real records."
                    ),
                    "status": "LIVE_PAPER_SNAPSHOT",
                    "as_of": moment.isoformat(),
                })
        return snapshots

    def _stored_recommendation(self, ticker, moment):
        """Read-only, freshness-checked lookup of a stored recommendation.

        Returns (record, None) when a fresh record exists, else
        (None, reason). Never raises: a failed lookup degrades to the HOLD
        fallback so the cycle is never blocked by the research path.
        """
        try:
            from database.repository import get_latest_recommendation_for_ticker

            record = get_latest_recommendation_for_ticker(ticker)
        except Exception as error:
            return None, f"lookup unavailable: {error}"

        if not record:
            return None, "none stored"

        run_time = record.get("run_time")
        if not run_time:
            return None, "stored recommendation has no run time"
        try:
            recorded_at = datetime.fromisoformat(str(run_time))
        except ValueError:
            return None, "stored recommendation has an unparseable run time"

        age = moment - recorded_at
        if age > timedelta(days=self.STORED_RECOMMENDATION_MAX_AGE_DAYS):
            return None, (
                f"stored recommendation is stale ({age.days} days old, "
                f"limit {self.STORED_RECOMMENDATION_MAX_AGE_DAYS})"
            )

        return record, None

    def _construction_report(self, state, prices, recommendations):
        return PortfolioConstructionEngine().build(
            recommendations=self._construction_recommendations(recommendations),
            paper_portfolio=self._construction_portfolio(state, prices),
        )

    def _construction_recommendations(self, recommendations):
        return [
            {
                "ticker": recommendation["ticker"],
                "action": "HOLD",
                "sector": recommendation.get("sector", "Unknown"),
                "industry": recommendation.get("industry", "Unknown"),
                "country": recommendation.get("country", "US"),
                "price": recommendation.get("price"),
            }
            for recommendation in recommendations
        ]

    def _exact_order_recommendation_id(self, order, recommendations):
        """Return an explicitly causal recommendation link, never a ticker guess.

        Current construction deliberately normalizes stored research to HOLD and
        emits rebalance orders without recommendation identity, so those orders
        remain unlinked. If an order path supplies both an exact recommendation
        id and its run id, they must match the cycle snapshot for the same ticker.
        """
        recommendation_id = order.get("recommendation_id")
        run_id = order.get("recommendation_run_id")
        if recommendation_id is None or run_id is None:
            return None

        for snapshot in recommendations:
            if (
                snapshot.get("ticker") == order.get("ticker")
                and snapshot.get("recommendation_id") == recommendation_id
                and snapshot.get("run_id") == run_id
            ):
                return recommendation_id
        return None

    def _construction_portfolio(self, state, prices):
        positions = []
        current_value = 0
        for ticker, position in state["positions"].items():
            price = prices.get(ticker, position["cost_basis"])
            value = round(position["quantity"] * price, 2)
            current_value += value
            positions.append({
                "ticker": ticker,
                "quantity": position["quantity"],
                "cost_basis": position["cost_basis"],
                "current_price": price,
                "current_value": value,
            })

        return {
            "cash": state["cash"],
            "portfolio_value": round(state["cash"] + current_value, 2),
            "positions": positions,
        }

    def _construction_summary(self, construction):
        return {
            "engine": "PortfolioConstructionEngine",
            "recommended_allocations": [
                {
                    "ticker": allocation["ticker"],
                    "suggested_allocation": allocation["suggested_allocation"],
                    "current_allocation": allocation["current_allocation"],
                    "capital_required": allocation["capital_required"],
                    "position_priority": allocation["position_priority"],
                }
                for allocation in construction.get("recommended_allocations", [])
            ],
            "risk_summary": construction.get("risk_summary", {}),
            "diversification": construction.get("diversification", {}),
            "policy": construction.get("policy", {}),
        }

    def _rebalance_orders(
        self,
        state,
        prices,
        provider,
        moment,
        cycle_id,
        construction,
        manager=None,
    ):
        proposed_orders = self._propose_orders(
            state,
            prices,
            provider,
            moment,
            cycle_id,
            construction,
        )
        correlation = self._correlation_evidence(
            state,
            proposed_orders,
            manager,
            provider,
            moment,
        )
        market_data = (
            {"correlations": correlation["correlations"]}
            if correlation.get("correlations")
            else {}
        )
        self._activity(
            moment,
            cycle_id,
            "CORRELATION_EVALUATED",
            self._correlation_message(correlation),
            {
                "status": correlation["status"],
                "reason": correlation.get("reason"),
                "threshold": correlation.get("threshold"),
                "symbols_evaluated": correlation.get("symbols_evaluated", []),
                "pairs_evaluated": correlation.get("pairs_evaluated", 0),
                "data_source": correlation.get("data_source"),
            },
        )
        risk_decisions = self._risk_validate_orders(
            proposed_orders,
            state,
            prices,
            cycle_id,
            moment,
            market_data,
        )
        approved_decisions = [
            decision for decision in risk_decisions
            if decision["risk_decision"]["status"] == "APPROVED"
        ]
        rejected_decisions = [
            decision for decision in risk_decisions
            if decision["risk_decision"]["status"] == "REJECTED"
        ]

        orders = []
        for decision in approved_decisions:
            orders.append(
                self._execute_approved_order(
                    state,
                    decision["order"],
                    provider,
                    moment,
                    cycle_id,
                    decision["decision_id"],
                )
            )

        return orders, {
            "proposed": len(proposed_orders),
            "approved": len(approved_decisions),
            "rejected": len(rejected_decisions),
            "correlation": {
                "status": correlation["status"],
                "reason": correlation.get("reason"),
                "threshold": correlation.get("threshold"),
                "symbols_evaluated": correlation.get("symbols_evaluated", []),
                "pairs_evaluated": correlation.get("pairs_evaluated", 0),
                "data_source": correlation.get("data_source"),
            },
            "decision_ids": [decision["decision_id"] for decision in risk_decisions],
            "rejections": [
                {
                    "decision_id": decision["decision_id"],
                    "order": decision["order"],
                    "reasons": [
                        item["reason"]
                        for item in decision["risk_decision"]["rejections"]
                    ],
                    "checks": decision["risk_decision"]["checks"],
                }
                for decision in rejected_decisions
            ],
            "policy": self.policy(),
        }

    def _propose_orders(self, state, prices, provider, moment, cycle_id, construction):
        positions = state["positions"]
        portfolio_value = round(state["cash"] + sum(
            position["quantity"] * prices.get(ticker, position["cost_basis"])
            for ticker, position in positions.items()
        ), 2)
        threshold = portfolio_value * self.REBALANCE_THRESHOLD
        plans = []
        allocations = {
            allocation["ticker"]: allocation
            for allocation in construction.get("recommended_allocations", [])
        }

        for ticker in state["watchlist"]:
            allocation = allocations.get(ticker)
            if not allocation:
                continue
            price = prices.get(ticker)
            if price is None or price <= 0:
                continue
            target_value = round(
                portfolio_value * allocation["suggested_allocation"] / 100,
                2,
            )
            held = positions.get(ticker, {}).get("quantity", 0)
            drift = target_value - held * price
            if abs(drift) <= threshold:
                continue
            side = "BUY" if drift > 0 else "SELL"
            quantity = math.floor(abs(drift) / price)
            if quantity >= 1:
                plans.append({
                    "order_id": f"{cycle_id}-{side}-{ticker}",
                    "cycle_id": cycle_id,
                    "ticker": ticker,
                    "symbol": ticker,
                    "side": side,
                    "quantity": quantity,
                    "price": price,
                    "fill_price": price,
                    "price_source": provider,
                    "created_at": moment.isoformat(),
                    "target_allocation": allocation["suggested_allocation"],
                    "target_value": target_value,
                    "current_value": round(held * price, 2),
                    "construction_allocation": allocation,
                    "reason": (
                        "PortfolioConstructionEngine rebalance toward "
                        "suggested allocation."
                    ),
                    "policy": self.policy(),
                })

        # Validate and fill SELLs first so approved sale proceeds can fund BUYs.
        return sorted(plans, key=lambda plan: (plan["side"] != "SELL", plan["ticker"]))

    def _risk_validate_orders(
        self, proposed_orders, state, prices, cycle_id, moment, market_data=None
    ):
        from database.repository import save_risk_decision

        market_data = market_data or {}
        risk_engine = RiskManagementEngine()
        risk_portfolio = self._risk_portfolio(state, prices)
        decisions = []

        for order in proposed_orders:
            decision = risk_engine.evaluate(
                {
                    "symbol": order["ticker"],
                    "side": order["side"],
                    "quantity": order["quantity"],
                    "price": order["price"],
                },
                portfolio=risk_portfolio,
                limits=self._risk_limits(),
                market_data=market_data,
            )
            decision_id = f"{cycle_id}-RISK-{order['side']}-{order['ticker']}"
            save_risk_decision({
                **decision,
                "decision_id": decision_id,
                "cycle_id": cycle_id,
                "created_at": moment.isoformat(),
            })
            wrapped = {
                "decision_id": decision_id,
                "order": order,
                "risk_decision": decision,
            }
            decisions.append(wrapped)
            if decision["status"] == "APPROVED":
                self._apply_order_to_risk_portfolio(risk_portfolio, order)

        return decisions

    def _execute_approved_order(
        self,
        state,
        order,
        provider,
        moment,
        cycle_id,
        risk_decision_id,
    ):
        positions = state["positions"]
        ticker = order["ticker"]
        side = order["side"]
        quantity = order["quantity"]
        price = order["price"]

        if side == "BUY":
            cost = round(quantity * price, 2)
            state["cash"] = round(state["cash"] - cost, 2)
            position = positions.get(ticker)
            if position:
                total_quantity = position["quantity"] + quantity
                total_cost = (
                    position["quantity"] * position["cost_basis"] + cost
                )
                position["quantity"] = total_quantity
                position["cost_basis"] = round(total_cost / total_quantity, 4)
            else:
                positions[ticker] = {
                    "ticker": ticker,
                    "quantity": quantity,
                    "cost_basis": price,
                    "entry_date": moment.isoformat(),
                }
        else:
            position = positions[ticker]
            proceeds = round(quantity * price, 2)
            basis = round(quantity * position["cost_basis"], 2)
            state["cash"] = round(state["cash"] + proceeds, 2)
            state["realized_pl"] = round(
                state["realized_pl"] + proceeds - basis, 2
            )
            if quantity == position["quantity"]:
                del positions[ticker]
            else:
                position["quantity"] -= quantity

        return {
            "order_id": order["order_id"],
            "cycle_id": cycle_id,
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "status": "FILLED_SIMULATED",
            "created_at": order["created_at"],
            "filled_at": moment.isoformat(),
            "fill_price": price,
            "price_source": provider,
            "validated": True,
            "simulated": True,
            "reason": order["reason"],
            "risk_decision_id": risk_decision_id,
            "target_allocation": order.get("target_allocation"),
            "target_value": order.get("target_value"),
            "current_value": order.get("current_value"),
            "construction_allocation": order.get("construction_allocation"),
            "policy": self.policy(),
        }

    def _risk_portfolio(self, state, prices):
        return {
            "cash": state["cash"],
            "positions": {
                ticker: {
                    "quantity": position["quantity"],
                    "price": prices.get(ticker, position["cost_basis"]),
                }
                for ticker, position in state["positions"].items()
            },
        }

    def _apply_order_to_risk_portfolio(self, portfolio, order):
        positions = portfolio["positions"]
        ticker = order["ticker"]
        quantity = order["quantity"]
        price = order["price"]
        value = round(quantity * price, 2)

        if order["side"] == "BUY":
            portfolio["cash"] = round(portfolio["cash"] - value, 2)
            position = positions.get(ticker, {"quantity": 0, "price": price})
            position["quantity"] += quantity
            position["price"] = price
            positions[ticker] = position
        else:
            portfolio["cash"] = round(portfolio["cash"] + value, 2)
            position = positions[ticker]
            position["quantity"] -= quantity
            if position["quantity"] <= 0:
                del positions[ticker]

    def _risk_limits(self):
        return {
            "max_position_size": 1,
            "max_portfolio_exposure": 1,
            "minimum_cash_reserve": 0,
            "max_sector_exposure": 1,
            "max_position_count": max(1, 10_000),
            "max_correlation": 0.80,
        }

    # ------------------------------------------------------------------
    # Correlation risk evidence
    # ------------------------------------------------------------------
    def _correlation_evidence(self, state, proposed_orders, manager, provider, moment):
        """Real, price-backed correlation evidence for the risk gate.

        Covers held positions plus candidate order symbols so a not-yet-held
        BUY is still evaluated against existing holdings. Uses only real
        price-backed history; when history is unavailable the result is
        NOT_EVALUATED with empty correlations (never fabricated values).
        """
        universe = self._correlation_universe(state, proposed_orders)
        price_history = self._correlation_price_history(
            universe, manager, provider, moment
        )
        return CorrelationEngine().risk_matrix(
            universe,
            state=state,
            price_history=price_history,
            as_of=moment.isoformat(),
        )

    def _correlation_universe(self, state, proposed_orders):
        symbols = set()
        for ticker in state.get("watchlist", []):
            symbols.add(str(ticker).strip().upper())
        for ticker in state.get("positions", {}):
            symbols.add(str(ticker).strip().upper())
        for order in proposed_orders:
            symbols.add(
                str(order.get("ticker") or order.get("symbol") or "").strip().upper()
            )
        symbols.discard("")
        return sorted(symbols)

    def _correlation_price_history(self, universe, manager, provider, moment):
        fetch = getattr(manager, "historical_prices", None)
        if not callable(fetch) or len(universe) < 2:
            return {"provider": provider, "rows": [], "fallback_used": False}

        end = moment
        start = end - timedelta(days=CorrelationEngine.LOOKBACK_DAYS)
        try:
            payload = fetch(
                list(universe),
                start.strftime("%Y-%m-%d"),
                end.strftime("%Y-%m-%d"),
            )
        except Exception:
            return {"provider": provider, "rows": [], "fallback_used": False}

        return {
            "provider": provider,
            "rows": (payload or {}).get("rows") or [],
            "fallback_used": bool((payload or {}).get("fallback_used", False)),
        }

    def _correlation_message(self, correlation):
        if correlation["status"] == "NOT_EVALUATED":
            return (
                "Correlation risk NOT_EVALUATED: "
                + (correlation.get("reason") or "correlation data unavailable.")
            )
        return (
            f"Correlation risk {correlation['status']} across "
            f"{len(correlation.get('symbols_evaluated', []))} symbols; "
            f"{correlation.get('pairs_evaluated', 0)} pairs measured against "
            f"max correlation limit {correlation.get('threshold')}."
        )

    def _snapshot(self, state, prices, provider, moment, cycle_id):
        current_value = 0
        unrealized = 0

        for ticker, position in state["positions"].items():
            price = prices.get(ticker, position["cost_basis"])
            value = round(position["quantity"] * price, 2)
            basis = round(position["quantity"] * position["cost_basis"], 2)
            position["current_price"] = price
            position["current_value"] = value
            position["unrealized_pl"] = round(value - basis, 2)
            current_value += value
            unrealized += value - basis

        portfolio_value = round(state["cash"] + current_value, 2)
        from database.repository import get_paper_fund_snapshots

        previous = get_paper_fund_snapshots(limit=1)
        previous_value = (
            previous[0]["portfolio_value"] if previous else state["starting_cash"]
        )

        return {
            "as_of": moment.isoformat(),
            "date": moment.isoformat(),
            "cycle_id": cycle_id,
            "cash": round(state["cash"], 2),
            "positions": state["positions"],
            "current_value": round(current_value, 2),
            "realized_pl": round(state["realized_pl"], 2),
            "unrealized_pl": round(unrealized, 2),
            "portfolio_value": portfolio_value,
            "previous_portfolio_value": previous_value,
            "portfolio_value_change": round(portfolio_value - previous_value, 2),
            "daily_return": self._percentage(portfolio_value, previous_value),
            "total_return": self._percentage(
                portfolio_value, state["starting_cash"]
            ),
            "price_source": provider,
            "policy": self.policy(),
        }

    def _learning_entry(
        self,
        recommendations,
        market_status,
        construction_summary,
        orders,
        risk_summary,
        snapshot,
        prices,
        moment,
        cycle_id,
    ):
        bought = sorted({
            order["ticker"] for order in orders if order.get("side") == "BUY"
        })
        sold = sorted({
            order["ticker"] for order in orders if order.get("side") == "SELL"
        })
        rejected = [
            {
                "symbol": item["order"]["ticker"],
                "side": item["order"]["side"],
                "quantity": item["order"]["quantity"],
                "reasons": item["reasons"],
            }
            for item in risk_summary.get("rejections", [])
        ]
        positions = snapshot["positions"]
        largest = max(
            positions.values(),
            key=lambda position: position.get("current_value", 0),
            default=None,
        )
        lesson = (
            f"Filled {len(orders)} simulated orders; portfolio value "
            f"${snapshot['portfolio_value']:,.2f} "
            f"({snapshot['total_return']}% total return)."
        )
        if largest:
            lesson += (
                f" Largest position {largest['ticker']} at "
                f"${largest['current_value']:,.2f}."
            )

        summary = {
            "recommended_symbols": sorted(
                recommendation["ticker"] for recommendation in recommendations
            ),
            "construction_targets": construction_summary.get(
                "recommended_allocations",
                [],
            ),
            "bought_symbols": bought,
            "sold_symbols": sold,
            "rejected_orders": rejected,
            "risk_summary": risk_summary,
            "portfolio": {
                "previous_value": snapshot.get("previous_portfolio_value"),
                "current_value": snapshot["portfolio_value"],
                "value_change": snapshot.get("portfolio_value_change"),
                "daily_return": snapshot["daily_return"],
                "total_return": snapshot["total_return"],
                "realized_pl": snapshot["realized_pl"],
                "unrealized_pl": snapshot["unrealized_pl"],
                "cash": snapshot["cash"],
            },
            "what_worked": self._learning_worked(orders, rejected, snapshot),
            "what_did_not_work": self._learning_did_not_work(
                orders,
                rejected,
                risk_summary,
                snapshot,
            ),
            "watch_next": self._learning_watch_next(
                construction_summary,
                rejected,
                snapshot,
            ),
            "policy": self._learning_policy(),
        }
        journal = {
            "cycle_id": cycle_id,
            "completed_at": moment.isoformat(),
            "market_conditions": {
                "session": market_status.get("session"),
                "is_open": market_status.get("is_open"),
                "as_of": market_status.get("as_of"),
            },
            "recommendations_considered": summary["recommended_symbols"],
            "accepted_trades": [
                {
                    "symbol": order["ticker"],
                    "side": order["side"],
                    "quantity": order["quantity"],
                    "fill_price": order["fill_price"],
                    "risk_decision_id": order.get("risk_decision_id"),
                }
                for order in orders
            ],
            "rejected_trades": rejected,
            "portfolio_changes": summary["portfolio"],
            "learning_summary": {
                "what_worked": summary["what_worked"],
                "what_did_not_work": summary["what_did_not_work"],
                "watch_next": summary["watch_next"],
            },
            "execution_time": {
                "started_at": moment.isoformat(),
                "completed_at": moment.isoformat(),
                "duration_seconds": 0,
            },
            "policy": summary["policy"],
        }

        return {
            "at": moment.isoformat(),
            "cycle_id": cycle_id,
            "lesson": lesson,
            "details": {
                "orders_filled": len(orders),
                "portfolio_value": snapshot["portfolio_value"],
                "total_return": snapshot["total_return"],
                "prices": prices,
                "learning_summary": summary,
                "cycle_journal": journal,
                "policy": summary["policy"],
            },
        }

    def _learning_worked(self, orders, rejected, snapshot):
        worked = []
        if orders:
            worked.append("Approved simulated orders executed at validated prices.")
        if snapshot["portfolio_value_change"] >= 0:
            worked.append("Paper portfolio value was flat or higher this cycle.")
        if not rejected:
            worked.append("No proposed orders were blocked by risk controls.")
        return worked or ["No positive cycle signal recorded."]

    def _learning_did_not_work(self, orders, rejected, risk_summary, snapshot):
        issues = []
        if rejected:
            symbols = ", ".join(sorted({item["symbol"] for item in rejected}))
            issues.append(f"Risk controls blocked proposed orders for {symbols}.")
        if risk_summary.get("proposed", 0) and not orders:
            issues.append("No proposed orders passed risk validation.")
        if snapshot["portfolio_value_change"] < 0:
            issues.append("Paper portfolio value declined this cycle.")
        return issues or ["No deterministic issue recorded this cycle."]

    def _learning_watch_next(self, construction_summary, rejected, snapshot):
        watch = []
        for item in rejected:
            watch.append(
                f"Review {item['symbol']} before the next cycle: "
                + "; ".join(item["reasons"])
            )

        largest = max(
            snapshot["positions"].values(),
            key=lambda position: position.get("current_value", 0),
            default=None,
        )
        if largest:
            watch.append(
                f"Monitor largest paper position {largest['ticker']} at "
                f"${largest['current_value']:,.2f}."
            )

        risk_budget = construction_summary.get("risk_summary", {}).get("risk_budget")
        if risk_budget:
            watch.append(f"Track construction risk budget: {risk_budget}.")

        return watch or ["Watch for new validated prices and allocation drift."]

    def _learning_policy(self):
        return {
            "descriptive_only": True,
            "does_not_modify_recommendations": True,
            "does_not_modify_trades": True,
            "paper_only": True,
            "real_money": False,
        }

    def _transition(self, now, new_status, activity_type, message):
        from database.repository import get_latest_paper_fund_state

        state = get_latest_paper_fund_state()
        if state is None:
            raise ValueError("Live paper fund is not started.")

        moment = self._moment(now)
        new_state = {
            **state,
            "updated_at": moment.isoformat(),
            "fund_status": new_status,
            "policy": self.policy(),
        }
        self._save_state(new_state)
        self._activity(moment, None, activity_type, message, {})

        return new_state

    def _dominant_provider(self, price_report):
        providers = [
            result.get("provider", "unknown")
            for result in price_report.get("results", {}).values()
        ]

        if not providers:
            return price_report.get("requested_provider", "unknown")

        return max(set(providers), key=providers.count)

    def _activity(self, moment, cycle_id, activity_type, message, details):
        from database.repository import add_paper_fund_activity

        add_paper_fund_activity({
            "at": moment.isoformat(),
            "cycle_id": cycle_id,
            "activity_type": activity_type,
            "message": message,
            "details": details,
        })

    def _save_state(self, state):
        from database.repository import save_paper_fund_state

        save_paper_fund_state(state)

    def _save_order(self, order):
        from database.repository import save_paper_fund_order

        save_paper_fund_order(order)

    def _save_snapshot(self, snapshot):
        from database.repository import save_paper_fund_snapshot

        save_paper_fund_snapshot(snapshot)

    def _save_learning(self, learning):
        from database.repository import add_paper_fund_learning

        add_paper_fund_learning(learning)

    def _save_construction_report(self, construction):
        from database.repository import save_portfolio_construction_report

        save_portfolio_construction_report(construction)

    def _percentage(self, current, previous):
        if not previous:
            return 0

        return round((current - previous) / previous * 100, 4)

    def _parse_time(self, value):
        if isinstance(value, datetime):
            return value
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    def _duration_seconds(self, started_at, completed_at):
        start = self._parse_time(started_at)
        end = self._parse_time(completed_at)
        if start is None or end is None:
            return None
        return max(0, int((end - start).total_seconds()))

    def _cycle_execution_time(self, cycle_id, activity):
        if not cycle_id:
            return {
                "started_at": None,
                "completed_at": None,
                "duration_seconds": None,
            }
        cycle_events = [
            entry for entry in (activity or [])
            if entry.get("cycle_id") == cycle_id
        ]
        started = next(
            (
                entry.get("at")
                for entry in reversed(cycle_events)
                if entry.get("activity_type") == "CYCLE_STARTED"
            ),
            None,
        )
        completed = next(
            (
                entry.get("at")
                for entry in cycle_events
                if entry.get("activity_type") in {"CYCLE_COMPLETED", "CYCLE_FAILED"}
            ),
            None,
        )
        return {
            "started_at": started,
            "completed_at": completed,
            "duration_seconds": self._duration_seconds(started, completed),
        }

    def _moment(self, now):
        if isinstance(now, datetime):
            return now

        if now:
            try:
                return datetime.fromisoformat(str(now))
            except ValueError:
                pass

        return datetime.now()
