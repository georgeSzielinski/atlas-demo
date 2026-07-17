import hashlib
import json

from engines.catalyst_engine import CatalystEngine
from engines.macro_engine import MacroEngine
from market.data import data_provider_health


class DailyJournalEngine:
    def build(
        self,
        cycle=None,
        source_data=None,
        runtime_state=None,
        provider_health=None,
        macro=None,
        catalyst=None,
    ):
        cycle = cycle or {}
        details = cycle.get("details", {})
        date = cycle.get("date") or details.get("date") or "2026-06-30"
        source_data = source_data or {}
        macro = macro or self._macro_from_cycle(details) or MacroEngine().analyze()
        catalyst = (
            catalyst
            or self._catalyst_from_cycle(details)
            or CatalystEngine().analyze(as_of_date=date)
        )
        provider_health = (
            provider_health
            or details.get("provider_health")
            or data_provider_health()
        )
        runtime_state = runtime_state or self._runtime_state(cycle)
        paper_report = details.get("paper_report", {})
        portfolio = self._latest_portfolio(paper_report, source_data)
        performance = self._latest_performance(paper_report, source_data)
        recommendations = self._recommendations(cycle, source_data)
        trades = paper_report.get("trades") or source_data.get("paper_trades", [])

        return {
            "journal_id": self._journal_id(date, cycle),
            "date": date,
            "market_regime": macro.get("current_macro_regime", "Unavailable"),
            "runtime_state": runtime_state,
            "paper_portfolio_summary": self._paper_summary(portfolio),
            "benchmark_comparison": performance.get("benchmark_comparison", []),
            "provider_health": self._provider_summary(provider_health),
            "macro_summary": self._macro_summary(macro),
            "catalyst_summary": catalyst.get("summary", {}),
            "recommendation_summary": self._recommendation_summary(
                recommendations,
                trades,
            ),
            "performance_summary": self._performance_summary(
                portfolio,
                performance,
            ),
            "lessons_learned": self.lessons_learned(
                recommendations,
                performance,
                macro,
                catalyst,
            ),
            "research_tasks": self.research_tasks(
                performance,
                macro,
                catalyst,
            ),
            "policy": self.policy(),
        }

    def persist(self, journal):
        from database.repository import save_daily_journal

        save_daily_journal(journal)

    def lessons_learned(self, recommendations, performance, macro, catalyst):
        evidence = self._evidence_names(recommendations)
        committee = self._average(
            [
                item.get("committee_agreement", 0)
                for item in recommendations
                if item.get("committee_agreement") is not None
            ]
        )
        forecast = self._average(
            [
                item.get("forecast_score", 0)
                for item in recommendations
                if item.get("forecast_score") is not None
            ]
        )
        catalyst_summary = catalyst.get("summary", {})

        return {
            "most_useful_evidence_today": evidence[0] if evidence else "None recorded",
            "weakest_evidence_today": evidence[-1] if evidence else "None recorded",
            "most_important_catalyst": (
                catalyst_summary.get("most_common_catalyst")
                or "No catalyst concentration recorded"
            ),
            "macro_influence": (
                f"{macro.get('current_macro_regime', 'Unavailable')} regime "
                f"with risk score {macro.get('macro_risk_score', 0)}."
            ),
            "committee_observations": (
                f"Average committee agreement: {round(committee, 2)}."
            ),
            "forecast_observations": (
                f"Average forecast score: {round(forecast, 2)}."
            ),
            "performance_observation": (
                f"Paper alpha vs S&P: {performance.get('alpha_vs_sp', 0)}."
            ),
        }

    def research_tasks(self, performance, macro, catalyst):
        tasks = [
            "Review earnings reactions for active watchlist names.",
            "Study macro sensitivity against current paper positions.",
            "Investigate probability calibration for recent recommendations.",
            "Compare similar historical cases before the next cycle.",
        ]

        if performance.get("max_drawdown", 0) < 0:
            tasks.append("Review paper drawdown drivers and concentration.")

        if macro.get("macro_risk_score", 0) >= 60:
            tasks.append("Stress test recommendations against elevated macro risk.")

        if catalyst.get("summary", {}).get("event_count", 0) > 0:
            tasks.append("Review catalyst timing against entry and exit dates.")

        return tasks

    def monthly_summary(self, journals):
        """Deterministic aggregation of daily journals for monthly analytics.

        Read-only. Rolls up recorded lessons and research tasks so Performance
        Analytics can report major lessons without duplicating journal logic.
        """
        ordered = sorted(
            journals or [],
            key=lambda item: item.get("date", ""),
            reverse=True,
        )
        lessons = []
        tasks = []

        for journal in ordered:
            learned = journal.get("lessons_learned", {})
            for key in (
                "most_useful_evidence_today",
                "performance_observation",
                "macro_influence",
                "committee_observations",
            ):
                value = learned.get(key)
                if value and value not in lessons:
                    lessons.append(value)

            for task in journal.get("research_tasks", []):
                if task and task not in tasks:
                    tasks.append(task)

        return {
            "journal_count": len(ordered),
            "major_lessons": lessons[:5],
            "research_tasks": tasks[:5],
        }

    def policy(self):
        return {
            "paper_only": True,
            "broker_integration": False,
            "real_money": False,
            "automatic_execution": False,
            "changes_recommendation_behavior": False,
            "deterministic": True,
            "permanent_research_record": True,
        }

    def _journal_id(self, date, cycle):
        seed = f"{date}|{cycle.get('cycle_id', '')}|daily-journal"
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]

        return f"journal-{digest}"

    def _runtime_state(self, cycle):
        return {
            "cycle_id": cycle.get("cycle_id"),
            "phase": cycle.get("phase"),
            "status": cycle.get("status"),
            "summary": cycle.get("summary", ""),
        }

    def _macro_from_cycle(self, details):
        context = details.get("macro_context")
        if not context:
            return None

        return {
            "current_macro_regime": context.get("current_macro_regime"),
            "macro_risk_score": context.get("macro_risk_score", 0),
            "summary": context,
        }

    def _catalyst_from_cycle(self, details):
        summary = details.get("catalyst_summary")
        if not summary:
            return None

        return {"summary": summary}

    def _latest_portfolio(self, paper_report, source_data):
        if paper_report.get("portfolio"):
            return paper_report["portfolio"]

        history = source_data.get("paper_portfolio_history", [])
        return history[0] if history else {}

    def _latest_performance(self, paper_report, source_data):
        if paper_report.get("performance"):
            return paper_report["performance"]

        reports = source_data.get("paper_performance_reports", [])
        return reports[0].get("performance", {}) if reports else {}

    def _recommendations(self, cycle, source_data):
        details = cycle.get("details", {})
        recommendations = (
            details.get("recommendations")
            or details.get("watchlist_recommendations")
            or source_data.get("recommendations", [])
        )

        return [dict(item) for item in recommendations]

    def _paper_summary(self, portfolio):
        positions = portfolio.get("positions", {})

        return {
            "cash": portfolio.get("cash", 0),
            "portfolio_value": portfolio.get("portfolio_value", 0),
            "realized_pl": portfolio.get("realized_pl", 0),
            "unrealized_pl": portfolio.get("unrealized_pl", 0),
            "open_positions": len(positions),
            "status": portfolio.get("status", "PAPER"),
        }

    def _provider_summary(self, provider_health):
        return {
            "healthy": provider_health.get("healthy"),
            "provider": provider_health.get("provider", provider_health.get("name")),
            "status": provider_health.get("status", "Unknown"),
            "details": provider_health,
        }

    def _macro_summary(self, macro):
        return {
            "current_macro_regime": macro.get("current_macro_regime"),
            "macro_risk_score": macro.get("macro_risk_score", 0),
            "summary": macro.get("summary", ""),
        }

    def _recommendation_summary(self, recommendations, trades):
        actions = [
            item.get("action", "").upper()
            for item in recommendations
        ]
        highest = self._highest_conviction(recommendations)

        return {
            "recommendations_today": len(recommendations),
            "buy_count": actions.count("BUY"),
            "hold_count": actions.count("HOLD"),
            "sell_count": len([
                trade for trade in trades
                if trade.get("action", "").upper() == "SELL"
            ]),
            "avoid_count": actions.count("AVOID"),
            "highest_conviction": highest,
        }

    def _performance_summary(self, portfolio, performance):
        return {
            "daily_return": performance.get(
                "daily_return",
                portfolio.get("daily_return", 0),
            ),
            "portfolio_value": portfolio.get("portfolio_value", 0),
            "alpha_vs_sp": performance.get("alpha_vs_sp", 0),
            "win_rate": performance.get("win_rate", 0),
            "drawdown": performance.get("max_drawdown", 0),
            "open_positions": len(portfolio.get("positions", {})),
        }

    def _highest_conviction(self, recommendations):
        if not recommendations:
            return None

        return max(
            recommendations,
            key=lambda item: (
                item.get("overall_conviction")
                or item.get("confidence")
                or item.get("overall_score")
                or 0,
                item.get("ticker", ""),
            ),
        )

    def _evidence_names(self, recommendations):
        scores = {}

        for recommendation in recommendations:
            evidence = recommendation.get("evidence_breakdown", [])
            if isinstance(evidence, str):
                try:
                    evidence = json.loads(evidence)
                except ValueError:
                    evidence = []

            for item in evidence:
                name = item.get("source") or item.get("engine") or item.get("name")
                if not name:
                    continue
                scores[name] = scores.get(name, 0) + item.get("score", 0)

        return [
            name for name, _ in sorted(
                scores.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]

    def _average(self, values):
        clean = [value for value in values if value is not None]

        if not clean:
            return 0

        return sum(clean) / len(clean)
