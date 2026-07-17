from datetime import date

from engines.catalyst_engine import CatalystEngine
from engines.daily_cycle_engine import DailyCycleEngine
from engines.macro_engine import MacroEngine
from engines.performance_observatory import PerformanceObservatory
from engines.runtime_scheduler import RuntimeScheduler
from engines.runtime_state import RuntimeState, utc_now_iso
from market.data import data_provider_health


class RuntimeEngine:
    def __init__(self, scheduler=None, daily_cycle_engine=None):
        self.scheduler = scheduler or RuntimeScheduler()
        self.daily_cycle_engine = daily_cycle_engine or DailyCycleEngine()

    def build_state(
        self,
        current_state="INITIALIZING",
        market_date=None,
        paper_portfolio=None,
        recommendations=None,
        provider_health=None,
        persist=False,
    ):
        market_date = market_date or date.today().isoformat()
        provider_health = provider_health or data_provider_health()
        macro = MacroEngine().analyze()
        catalyst = CatalystEngine().analyze(
            tickers=self._watchlist_tickers(),
            as_of_date=market_date,
        )
        watchlist = recommendations or self.daily_cycle_engine.watchlist_recommendations(
            market_date,
        )
        observatory = PerformanceObservatory().generate()
        paper = paper_portfolio or self._latest_paper_portfolio()
        paper_value = paper.get("portfolio_value")
        open_positions = len(paper.get("positions", {}))
        alerts = self._alerts(provider_health, macro, catalyst, paper)
        next_cycle = self.scheduler.next_cycle(current_state)
        timeline = self.scheduler.timeline(
            current_state,
            last_successful_cycle=market_date if current_state != "ERROR" else None,
            uptime="0 days",
        )
        operations_summary = self.operations_summary(
            macro,
            catalyst,
            observatory,
        )
        state = RuntimeState.build(
            current_state=current_state,
            market_date=market_date,
            market_phase=self._market_phase(current_state),
            last_cycle_time=utc_now_iso(),
            next_cycle=next_cycle,
            provider_health=provider_health,
            paper_portfolio_value=paper_value,
            active_watchlist_size=len(watchlist),
            open_positions=open_positions,
            recommendations_today=len(watchlist),
            alerts=alerts,
            tasks=timeline,
            operations_summary=operations_summary,
        )

        if persist:
            self.persist_state(state)

        return state

    def runtime_status(self, state):
        return {
            "runtime_id": state["runtime_id"],
            "current_state": state["current_state"],
            "market_phase": state["market_phase"],
            "last_update": state["last_cycle_time"],
            "next_task": state["tasks"]["next_scheduled_task"],
            "recommendations_today": state["recommendations_today"],
            "paper_portfolio_value": state["paper_portfolio_value"],
            "provider_health": state["provider_health"],
            "system_health": state["health"],
            "alerts": state["alerts"],
            "policy": state["policy"],
        }

    def runtime_tasks(self, state):
        return state["tasks"] | {
            "next_cycle": state["next_cycle"],
            "policy": state["policy"],
        }

    def market_overview(self, as_of=None):
        """Read-only market data overview for Operations.

        Reuses the Market Data Manager for provider, freshness, market status,
        health, and fallback status. Does not change recommendations or trade.
        """
        from market.market_data_manager import MarketDataManager
        from market.provider_health import data_freshness

        manager = MarketDataManager()
        snapshot = manager.snapshot(as_of=as_of)
        health = manager.health()
        cache = manager.cache_status()
        latest_age = cache["stats"].get("latest_age")

        return {
            "current_provider": snapshot["provider"],
            "requested_provider": manager.provider_name,
            "fallback_used": snapshot["fallback_used"],
            "validated": snapshot["validated"],
            "market_status": snapshot["market_status"],
            "data_freshness": data_freshness(latest_age),
            "provider_health": health,
            "cache_stats": cache["stats"],
            "policy": manager.policy(),
        }

    def persist_state(self, state):
        from database.repository import save_runtime_state

        save_runtime_state(state)

    def operations_summary(self, macro, catalyst, observatory):
        scientific = observatory.get("scientific_validation_summary", {})
        paper = observatory.get("paper_trading_dashboard", {})

        return {
            "macro_regime": macro.get("current_macro_regime", "Unavailable"),
            "macro_risk_score": macro.get("macro_risk_score", 0),
            "catalyst_summary": catalyst.get("summary", {}),
            "paper_trading": paper,
            "scientific_validation": scientific,
            "controlled_learning": observatory.get("controlled_learning", {}),
            "policy": RuntimeState.policy(),
        }

    def _alerts(self, provider_health, macro, catalyst, paper):
        alerts = []

        if provider_health.get("healthy") is False:
            alerts.append("Provider warning: data provider is unhealthy.")

        if macro.get("macro_risk_score", 0) >= 75:
            alerts.append("Macro risk warning: elevated macro risk score.")

        if "high" in str(catalyst.get("summary", {})).lower():
            alerts.append("Catalyst warning: high-risk catalyst context.")

        if paper.get("total_return", 0) <= -5:
            alerts.append("Paper drawdown warning: paper return is below threshold.")

        alerts.append("Safety notice: paper trading only, no broker connected.")

        return alerts

    def _latest_paper_portfolio(self):
        from database.repository import get_paper_portfolio_history

        history = get_paper_portfolio_history(limit=1)

        return history[0] if history else {
            "portfolio_value": 0,
            "positions": {},
            "total_return": 0,
        }

    def _market_phase(self, current_state):
        return current_state.lower()

    def _watchlist_tickers(self):
        from core.settings import APPROVED_TICKERS

        return APPROVED_TICKERS[:4]
