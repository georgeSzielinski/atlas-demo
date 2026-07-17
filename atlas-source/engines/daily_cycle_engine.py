import hashlib
import json
from datetime import datetime

from core.settings import APPROVED_TICKERS
from engines.catalyst_engine import CatalystEngine
from engines.macro_engine import MacroEngine
from engines.paper_trading_engine import PaperTradingEngine
from engines.performance_observatory import PerformanceObservatory
from market.data import data_provider_health


class DailyCycleEngine:
    PHASES = [
        "pre_market",
        "market_open",
        "market_close",
        "post_market",
    ]

    def __init__(self, paper_trading_engine=None):
        self.paper_trading_engine = paper_trading_engine or PaperTradingEngine()

    def run_phase(
        self,
        phase,
        cycle_date=None,
        recommendations=None,
        market_prices=None,
        portfolio=None,
        benchmark_returns=None,
        simulation_metadata=None,
        persist=False,
    ):
        if phase not in self.PHASES:
            raise ValueError(f"Unsupported daily cycle phase: {phase}")

        date = cycle_date or datetime.now().date().isoformat()

        if phase == "pre_market":
            result = self.pre_market(date, recommendations)
        elif phase == "market_close":
            result = self.market_close(
                date,
                recommendations or [],
                market_prices or {},
                portfolio or {},
                benchmark_returns or {},
                simulation_metadata=simulation_metadata,
            )
        elif phase == "post_market":
            result = self.post_market(date)
        else:
            result = self.market_open(date, recommendations or [])

        if persist:
            self.persist_cycle(result)

        return result

    def pre_market(self, date, recommendations=None):
        provider_health = data_provider_health()
        macro = MacroEngine().analyze()
        catalyst = CatalystEngine().analyze(
            tickers=APPROVED_TICKERS[:4],
            as_of_date=date,
        )
        watchlist = recommendations or self.watchlist_recommendations(date)
        warnings = self._warnings(provider_health, macro, catalyst)

        return self._cycle_record(
            date=date,
            phase="pre_market",
            status="READY" if provider_health.get("healthy") else "WARN",
            recommendations_count=len(watchlist),
            paper_portfolio_value=0,
            daily_return=0,
            alpha_vs_sp500=0,
            warnings=warnings,
            summary=(
                f"Pre-market cycle loaded {len(watchlist)} watchlist "
                "recommendations with provider, macro, and catalyst context."
            ),
            details={
                "provider_health": provider_health,
                "macro_context": {
                    "current_macro_regime": macro.get("current_macro_regime"),
                    "macro_risk_score": macro.get("macro_risk_score"),
                },
                "catalyst_summary": catalyst.get("summary", {}),
                "watchlist_recommendations": watchlist,
                "policy": self.policy(),
            },
        )

    def market_open(self, date, recommendations=None):
        return self._cycle_record(
            date=date,
            phase="market_open",
            status="MONITORING",
            recommendations_count=len(recommendations or []),
            paper_portfolio_value=0,
            daily_return=0,
            alpha_vs_sp500=0,
            warnings=[],
            summary=(
                "Market-open cycle is monitoring paper recommendations only; "
                "no broker orders are sent."
            ),
            details={"policy": self.policy()},
        )

    def market_close(
        self,
        date,
        recommendations,
        market_prices,
        portfolio,
        benchmark_returns,
        simulation_metadata=None,
    ):
        paper_report = self.paper_trading_engine.run(
            recommendations=recommendations,
            market_prices=market_prices,
            as_of_date=date,
            portfolio=portfolio,
            benchmark_returns=benchmark_returns,
            simulation_metadata=simulation_metadata,
        )
        performance = paper_report["performance"]
        warnings = []

        if performance.get("max_drawdown", 0) <= -5:
            warnings.append("Paper portfolio drawdown exceeds warning threshold.")

        return self._cycle_record(
            date=date,
            phase="market_close",
            status="COMPLETED",
            recommendations_count=len(recommendations),
            paper_portfolio_value=paper_report["portfolio"]["portfolio_value"],
            daily_return=performance.get("daily_return", 0),
            alpha_vs_sp500=performance.get("alpha_vs_sp", 0),
            warnings=warnings,
            summary=(
                "Market-close cycle updated paper portfolio prices, daily P/L, "
                "and benchmark comparison."
            ),
            details={
                "paper_report": paper_report,
                "recommendations": recommendations,
                "benchmark_returns": benchmark_returns,
                "policy": self.policy(),
            },
        )

    def post_market(self, date):
        try:
            observatory = PerformanceObservatory().generate()
        except Exception:
            observatory = PerformanceObservatory().generate(
                source_data={},
                discovery_data={
                    "recent_discoveries": [],
                    "top_discoveries": [],
                    "discovery_history": [],
                },
            )
        lessons = self.lessons_learned(observatory)
        follow_up = self.follow_up_research_items(observatory)

        return self._cycle_record(
            date=date,
            phase="post_market",
            status="REVIEW_READY",
            recommendations_count=0,
            paper_portfolio_value=0,
            daily_return=0,
            alpha_vs_sp500=0,
            warnings=[],
            summary=(
                "Post-market cycle updated observatory context and generated "
                f"{len(follow_up)} follow-up research items."
            ),
            details={
                "observatory_summary": {
                    "controlled_learning": observatory.get(
                        "controlled_learning",
                        {},
                    ),
                    "paper_trading_dashboard": observatory.get(
                        "paper_trading_dashboard",
                        {},
                    ),
                },
                "lessons_learned": lessons,
                "follow_up_research_items": follow_up,
                "policy": self.policy(),
            },
        )

    def watchlist_recommendations(self, date):
        tickers = APPROVED_TICKERS[:4]

        return [
            {
                "ticker": ticker,
                "action": "HOLD",
                "reason": f"Daily cycle watchlist review for {date}.",
                "sector": "Watchlist",
            }
            for ticker in tickers
        ]

    def run_simulated_daily_cycle(
        self,
        cycle_date,
        portfolio=None,
        step=0,
        simulation_metadata=None,
        persist=False,
    ):
        recommendations = self.paper_trading_engine.demo_recommendations()
        market_prices = self.paper_trading_engine.demo_market_prices(step)
        benchmark_returns = self.paper_trading_engine.demo_benchmark_returns(step)
        phases = [
            self.run_phase(
                "pre_market",
                cycle_date=cycle_date,
                recommendations=recommendations,
                persist=persist,
            ),
            self.run_phase(
                "market_open",
                cycle_date=cycle_date,
                recommendations=recommendations,
                persist=persist,
            ),
            self.run_phase(
                "market_close",
                cycle_date=cycle_date,
                recommendations=recommendations,
                market_prices=market_prices,
                portfolio=portfolio or {},
                benchmark_returns=benchmark_returns,
                simulation_metadata=simulation_metadata,
                persist=persist,
            ),
            self.run_phase(
                "post_market",
                cycle_date=cycle_date,
                persist=persist,
            ),
        ]

        return {
            "date": cycle_date,
            "phases": phases,
            "latest_phase": phases[-1],
            "paper_report": phases[2]["details"]["paper_report"],
            "policy": self.policy(),
        }

    def lessons_learned(self, observatory):
        paper = observatory.get("paper_trading_dashboard", {})
        rolling = paper.get("rolling_performance", {})

        return [
            (
                "Paper trading remains a validation source only; "
                f"latest total return is {rolling.get('latest_total_return', 0)}%."
            ),
            "Provider and macro context should be reviewed before the next cycle.",
        ]

    def follow_up_research_items(self, observatory):
        paper = observatory.get("paper_trading_dashboard", {})
        items = ["Review paper trade attribution before next market open."]

        if paper.get("rolling_performance", {}).get("latest_max_drawdown", 0) <= -5:
            items.append("Investigate paper drawdown drivers.")

        return items

    def persist_cycle(self, cycle):
        from database.repository import save_daily_cycle_run
        from engines.daily_journal_engine import DailyJournalEngine

        save_daily_cycle_run(cycle)

        if cycle.get("status") == "COMPLETED":
            paper_report = cycle.get("details", {}).get("paper_report")
            # Paper tables only ever hold price-backed data; simulated daily
            # cycle prices are research context, not paper trading records.
            if paper_report and paper_report.get("metadata", {}).get("price_backed") is True:
                self.paper_trading_engine.persist_report(paper_report)
            journal = DailyJournalEngine().build(cycle=cycle)
            DailyJournalEngine().persist(journal)

    def policy(self):
        return {
            "paper_only": True,
            "broker_integration": False,
            "real_money": False,
            "automatic_execution": False,
            "changes_recommendation_behavior": False,
            "human_approval_required_for_real_trading": True,
        }

    def _warnings(self, provider_health, macro, catalyst):
        warnings = []

        if provider_health.get("healthy") is False:
            warnings.append("Provider health check failed.")

        if macro.get("macro_risk_score", 0) >= 75:
            warnings.append("High macro risk score.")

        if "high" in json.dumps(catalyst.get("summary", {})).lower():
            warnings.append("High-risk catalyst context detected.")

        return warnings

    def _cycle_record(
        self,
        date,
        phase,
        status,
        recommendations_count,
        paper_portfolio_value,
        daily_return,
        alpha_vs_sp500,
        warnings,
        summary,
        details,
    ):
        return {
            "cycle_id": self._cycle_id(date, phase),
            "date": date,
            "phase": phase,
            "status": status,
            "recommendations_count": recommendations_count,
            "paper_portfolio_value": paper_portfolio_value,
            "daily_return": daily_return,
            "alpha_vs_sp500": alpha_vs_sp500,
            "warnings": warnings,
            "summary": summary,
            "details": details,
            "policy": self.policy(),
        }

    def _cycle_id(self, date, phase):
        digest = hashlib.sha1(f"{date}|{phase}".encode("utf-8")).hexdigest()[:12]

        return f"cycle-{digest}"
