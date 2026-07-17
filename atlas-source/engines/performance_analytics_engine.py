from engines.paper_trading_engine import PaperTradingEngine
from engines.performance_observatory import PerformanceObservatory
from engines.research_lab_engine import ResearchLabEngine


class PerformanceAnalyticsEngine:
    """Deterministic performance analytics that measures Atlas itself.

    This engine does not change recommendations, portfolio construction, or
    execution. It reuses the Paper Trading statistics, the Performance
    Observatory, and the Research Laboratory to accumulate objective evidence
    about Atlas over time so the platform can answer, using statistics instead
    of opinion, whether it should be trusted more today than yesterday.
    """

    BENCHMARKS = ["S&P 500", "NASDAQ-100", "Equal Weight Placeholder"]
    WEEKLY_WINDOW = 5
    MONTHLY_WINDOW = 21
    ROLLING_WINDOW = 5

    def __init__(
        self,
        paper_engine=None,
        observatory=None,
        research_lab=None,
    ):
        self.paper_engine = paper_engine or PaperTradingEngine()
        self.observatory = observatory or PerformanceObservatory()
        self.research_lab = research_lab or ResearchLabEngine()

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------
    def generate(
        self,
        portfolio_history=None,
        performance_reports=None,
        experiments=None,
        validations=None,
        journals=None,
        source_data=None,
        paper_trades=None,
        as_of_date=None,
    ):
        data = self._load(
            portfolio_history=portfolio_history,
            performance_reports=performance_reports,
            experiments=experiments,
            validations=validations,
            journals=journals,
            source_data=source_data,
            paper_trades=paper_trades,
        )
        history = data["history"]
        performance_reports = data["performance_reports"]
        experiments = data["experiments"]
        validations = data["validations"]
        journals = data["journals"]
        source_data = data["source_data"]
        paper_trades = data["paper_trades"]

        equity = self.equity_curve(history)
        benchmarks = self.benchmark_comparison(performance_reports, equity)
        risk = self.risk_statistics(history, performance_reports, equity)
        recommendation = self.recommendation_analytics(source_data, paper_trades)
        learning = self.learning_curve(
            journals,
            validations,
            experiments,
            source_data,
        )
        research = self.research_progress(experiments)
        monthly = self.latest_monthly_report(
            history=history,
            performance_reports=performance_reports,
            experiments=experiments,
            validations=validations,
            journals=journals,
            paper_trades=paper_trades,
            equity=equity,
            as_of_date=as_of_date,
        )

        return {
            "as_of_date": as_of_date or self._latest_date(history),
            "demo_data": data["demo"],
            "equity_curve": equity,
            "benchmark_comparison": benchmarks,
            "risk_statistics": risk,
            "recommendation_analytics": recommendation,
            "learning_curve": learning,
            "research_progress": research,
            "monthly_report": monthly,
            "trust_assessment": self.trust_assessment(
                equity,
                benchmarks,
                learning,
                risk,
            ),
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Part 1 - Equity Curve
    # ------------------------------------------------------------------
    def equity_curve(self, history):
        ordered = self._ordered_history(history)
        points = [
            {
                "date": self._short_date(item.get("date")),
                "portfolio_value": item.get("portfolio_value", 0),
                "daily_return": item.get("daily_return", 0),
                "cumulative_return": item.get("total_return", 0),
            }
            for item in ordered
        ]
        values = [item.get("portfolio_value", 0) for item in ordered]
        daily_returns = [item.get("daily_return", 0) for item in ordered]
        latest_value = values[-1] if values else self.paper_engine.INITIAL_CASH

        return {
            "points": points,
            "sample_size": len(points),
            "latest_value": latest_value,
            "daily_return": daily_returns[-1] if daily_returns else 0,
            "weekly_return": self._window_return(values, self.WEEKLY_WINDOW),
            "monthly_return": self._window_return(values, self.MONTHLY_WINDOW),
            "rolling_return": round(sum(daily_returns[-self.ROLLING_WINDOW:]), 4),
            "cumulative_return": ordered[-1].get("total_return", 0) if ordered else 0,
        }

    # ------------------------------------------------------------------
    # Part 2 - Benchmark Comparison
    # ------------------------------------------------------------------
    def benchmark_comparison(self, performance_reports, equity):
        performances = self._performances(performance_reports)
        latest = performances[0] if performances else {}
        latest_comparison = {
            item.get("benchmark"): item
            for item in latest.get("benchmark_comparison", [])
        }
        paper_return = equity.get("cumulative_return", latest.get("total_return", 0))
        rows = []

        for benchmark in self.BENCHMARKS:
            comparison = latest_comparison.get(benchmark, {})
            benchmark_return = comparison.get("benchmark_return", 0)
            diffs = self._benchmark_diffs(performances, benchmark)

            rows.append({
                "benchmark": benchmark,
                "benchmark_return": benchmark_return,
                "paper_return": paper_return,
                "alpha": round(paper_return - benchmark_return, 4),
                "relative_return": round(paper_return - benchmark_return, 4),
                "outperformance_rate": self._rate(
                    len([value for value in diffs if value > 0]),
                    len(diffs),
                ),
                "tracking_difference": self._standard_deviation(diffs),
            })

        return {
            "benchmarks": rows,
            "best_benchmark_alpha": max(
                (row["alpha"] for row in rows),
                default=0,
            ),
            "policy": (
                "Benchmark comparison is paper-only measurement and does not "
                "change recommendations or execute trades."
            ),
        }

    # ------------------------------------------------------------------
    # Part 3 - Risk Statistics
    # ------------------------------------------------------------------
    def risk_statistics(self, history, performance_reports, equity):
        ordered = self._ordered_history(history)
        daily_returns = [item.get("daily_return", 0) for item in ordered]
        values = [item.get("portfolio_value", 0) for item in ordered]
        latest = self._performances(performance_reports)
        latest = latest[0] if latest else {}

        sharpe = latest.get("sharpe") or self.paper_engine._sharpe(daily_returns)
        sortino = latest.get("sortino") or self.paper_engine._sortino(daily_returns)
        volatility = latest.get("volatility") or self._standard_deviation(
            daily_returns,
        )
        max_drawdown = latest.get("max_drawdown")
        if max_drawdown is None:
            max_drawdown = self.paper_engine._max_drawdown(values)
        cumulative = equity.get("cumulative_return", 0)
        drawdowns = self._drawdown_series(values)

        return {
            "sharpe": sharpe,
            "sortino": sortino,
            "calmar": self._calmar(cumulative, max_drawdown),
            "volatility": volatility,
            "max_drawdown": max_drawdown,
            "average_drawdown": self._average(
                [value for value in drawdowns if value < 0]
            ),
            "best_day": max(daily_returns) if daily_returns else 0,
            "worst_day": min(daily_returns) if daily_returns else 0,
            "sample_size": len(daily_returns),
            "policy": (
                "Risk statistics are measurement only and do not change "
                "recommendation behavior."
            ),
        }

    # ------------------------------------------------------------------
    # Part 4 - Recommendation Analytics
    # ------------------------------------------------------------------
    def recommendation_analytics(self, source_data, paper_trades):
        recommendations = source_data.get("recommendations", [])
        platform = self.observatory.platform_metrics(recommendations)
        probability = self.observatory.probability_summary(recommendations)
        closed = [
            trade for trade in paper_trades
            if trade.get("exit_price") is not None
        ]

        return {
            "buy_success_rate": self._action_success_rate(
                recommendations,
                {"BUY"},
            ),
            "hold_accuracy": self._action_success_rate(
                recommendations,
                {"HOLD"},
            ),
            "avoid_accuracy": self._action_success_rate(
                recommendations,
                {"AVOID", "SELL"},
            ),
            "average_holding_period": self._average([
                trade.get("holding_period", 0) for trade in closed
            ]),
            "recommendation_frequency": {
                "total": len(recommendations),
                "distribution": platform.get("recommendation_distribution", {}),
            },
            "confidence_calibration": platform.get("confidence_calibration", 0),
            "probability_calibration": probability.get(
                "probability_calibration",
                0,
            ),
            "sample_size": len(recommendations),
            "policy": (
                "Recommendation analytics measure historical accuracy only and "
                "do not change BUY, HOLD, or AVOID logic."
            ),
        }

    # ------------------------------------------------------------------
    # Part 5 - Learning Curve
    # ------------------------------------------------------------------
    def learning_curve(self, journals, validations, experiments, source_data):
        recommendations = source_data.get("recommendations", [])
        platform = self.observatory.platform_metrics(recommendations)
        lab_metrics = self.research_lab.learning_metrics(experiments, validations)
        ordered_journals = sorted(
            journals,
            key=lambda item: item.get("date", ""),
        )
        points = [
            {
                "date": self._short_date(journal.get("date")),
                "win_rate": journal.get("performance_summary", {}).get(
                    "win_rate",
                    0,
                ),
                "alpha_vs_sp": journal.get("performance_summary", {}).get(
                    "alpha_vs_sp",
                    0,
                ),
                "drawdown": journal.get("performance_summary", {}).get(
                    "drawdown",
                    0,
                ),
            }
            for journal in ordered_journals
        ]

        metrics = [
            {
                "label": "Knowledge Score",
                "value": platform.get("average_knowledge_score", 0),
            },
            {
                "label": "Stability Score",
                "value": platform.get("average_stability_score", 0),
            },
            {
                "label": "Scientific Validation Success",
                "value": lab_metrics["scientific_validation_success_rate"],
            },
            {
                "label": "Experiment Adoption Rate",
                "value": lab_metrics["experiment_adoption_rate"],
            },
            {
                "label": "Research Completion Rate",
                "value": lab_metrics["research_completion_rate"],
            },
        ]

        return {
            "metrics": metrics,
            "points": points,
            "knowledge_score": platform.get("average_knowledge_score", 0),
            "stability_score": platform.get("average_stability_score", 0),
            "scientific_validation_success_rate": lab_metrics[
                "scientific_validation_success_rate"
            ],
            "experiment_adoption_rate": lab_metrics["experiment_adoption_rate"],
            "research_completion_rate": lab_metrics["research_completion_rate"],
            "policy": (
                "Learning-curve metrics are deterministic measurement only and "
                "do not modify Atlas behavior."
            ),
        }

    # ------------------------------------------------------------------
    # Part 6 - Research Progress
    # ------------------------------------------------------------------
    def research_progress(self, experiments):
        operations = self.research_lab.operations_summary(experiments)
        progress = operations.get("research_progress", {})
        distribution = progress.get("state_distribution", {})

        return {
            "active_experiments": operations.get("active_experiment_count", 0),
            "active_experiment_list": operations.get("active_experiments", []),
            "completed": progress.get("completed", 0),
            "rejected": distribution.get("REJECTED", 0),
            "adopted": progress.get("adopted", 0),
            "completion_rate": progress.get("completion_rate", 0),
            "adoption_rate": progress.get("adoption_rate", 0),
            "state_distribution": distribution,
            "roadmap": self.research_lab.build_roadmap(experiments),
            "policy": (
                "Research progress is a read-only research signal; adoption "
                "always requires human approval."
            ),
        }

    # ------------------------------------------------------------------
    # Part 7 - Monthly Reports
    # ------------------------------------------------------------------
    def latest_monthly_report(
        self,
        history=None,
        performance_reports=None,
        experiments=None,
        validations=None,
        journals=None,
        paper_trades=None,
        equity=None,
        as_of_date=None,
    ):
        data = self._load(
            portfolio_history=history,
            performance_reports=performance_reports,
            experiments=experiments,
            validations=validations,
            journals=journals,
            paper_trades=paper_trades,
        )
        history = data["history"]
        performance_reports = data["performance_reports"]
        experiments = data["experiments"]
        validations = data["validations"]
        journals = data["journals"]
        paper_trades = data["paper_trades"]
        ordered = self._ordered_history(history)
        equity = equity or self.equity_curve(history)
        month = as_of_date or self._latest_month(ordered, journals)
        month_history = [
            item for item in ordered
            if self._short_date(item.get("date")).startswith(month)
        ] or ordered
        month_returns = [item.get("daily_return", 0) for item in month_history]
        closed = [
            trade for trade in paper_trades
            if trade.get("exit_price") is not None
        ]
        ranked = sorted(
            closed,
            key=lambda trade: (
                trade.get("profit_loss", 0),
                trade.get("ticker", ""),
            ),
        )

        return {
            "month": month,
            "performance": {
                "month_return": self._window_return(
                    [item.get("portfolio_value", 0) for item in month_history],
                    len(month_history),
                ),
                "cumulative_return": equity.get("cumulative_return", 0),
                "best_day": max(month_returns) if month_returns else 0,
                "worst_day": min(month_returns) if month_returns else 0,
                "latest_value": equity.get("latest_value", 0),
            },
            "major_lessons": self._major_lessons(journals),
            "best_decisions": [
                self._trade_digest(trade) for trade in reversed(ranked[-3:])
            ],
            "largest_mistakes": [
                self._trade_digest(trade) for trade in ranked[:3]
            ],
            "research_progress": self.research_progress(experiments),
            "validation_summary": self._validation_summary(validations),
            "policy": self.policy(),
        }

    def persist_monthly_report(self, report):
        from database.repository import save_monthly_report

        save_monthly_report(report)

    # ------------------------------------------------------------------
    # Trust assessment (design philosophy)
    # ------------------------------------------------------------------
    def trust_assessment(self, equity, benchmarks, learning, risk):
        points = equity.get("points", [])
        evidence = []

        if len(points) < 4:
            return {
                "verdict": "Not Enough Evidence",
                "explanation": (
                    "Not enough accumulated history to statistically judge "
                    "whether Atlas has improved."
                ),
                "evidence": evidence,
            }

        midpoint = len(points) // 2
        early = self._average([
            item.get("cumulative_return", 0) for item in points[:midpoint]
        ])
        recent = self._average([
            item.get("cumulative_return", 0) for item in points[midpoint:]
        ])
        cumulative_trend = round(recent - early, 4)
        best_alpha = benchmarks.get("best_benchmark_alpha", 0)
        adoption_rate = learning.get("experiment_adoption_rate", 0)

        evidence.append(
            f"Cumulative return trend: {cumulative_trend} (recent vs early)."
        )
        evidence.append(f"Best benchmark alpha: {best_alpha}.")
        evidence.append(f"Experiment adoption rate: {adoption_rate}%.")
        evidence.append(f"Sharpe: {risk.get('sharpe', 0)}.")

        positive_signals = [
            cumulative_trend > 0,
            best_alpha > 0,
            risk.get("sharpe", 0) > 0,
        ]
        positive = len([signal for signal in positive_signals if signal])

        if positive >= 2:
            verdict = "Improving"
        elif positive == 1:
            verdict = "Mixed"
        else:
            verdict = "Not Improving"

        return {
            "verdict": verdict,
            "explanation": (
                "Deterministic evidence-based assessment. Atlas does not claim "
                "improvement; it reports measured signals only."
            ),
            "evidence": evidence,
        }

    def trust_indicators(
        self,
        recommendation=None,
        source_data=None,
        validations=None,
        experiments=None,
        market_health=None,
    ):
        """Read-only trust indicators for the Atlas Brain (Part 9).

        Reuses the Performance Observatory, Research Laboratory, scientific
        validation reports, and the Market Data Manager. It changes nothing.
        """
        recommendation = recommendation or {}

        if validations is None:
            from database.repository import get_scientific_validation_reports

            validations = get_scientific_validation_reports(limit=50)

        if source_data is None:
            from database.repository import get_discovery_source_data

            source_data = get_discovery_source_data()

        if experiments is None:
            from database.repository import get_registry_experiments

            experiments = get_registry_experiments(limit=200)
            if not experiments:
                experiments = self.research_lab.default_experiments()

        recommendations = source_data.get("recommendations", [])
        probability = self.observatory.probability_summary(recommendations)
        lab_metrics = self.research_lab.learning_metrics(experiments, validations)
        operations = self.research_lab.operations_summary(experiments)
        latest_validation = validations[0] if validations else None

        if market_health is None:
            market_health = self._market_health()

        knowledge = recommendation.get("knowledge_score", 0) or 0
        stability = recommendation.get("stability_score", 0) or 0
        research_confidence_score = round((knowledge + stability) / 2, 2)

        return {
            "validation_status": {
                "recommendation_validation": recommendation.get(
                    "validation_status",
                    "Pending",
                ),
                "latest_scientific_result": (
                    (latest_validation or {}).get("scientific_result")
                    if latest_validation
                    else "No validation yet"
                ),
                "latest_adoption_decision": (
                    (latest_validation or {}).get("adoption_decision")
                    if latest_validation
                    else "Not Enough Evidence"
                ),
                "validation_count": len(validations),
            },
            "experiment_status": {
                "active_experiments": operations.get("active_experiment_count", 0),
                "adopted": operations.get("research_progress", {}).get("adopted", 0),
                "adoption_rate": lab_metrics["experiment_adoption_rate"],
                "scientific_validation_success_rate": lab_metrics[
                    "scientific_validation_success_rate"
                ],
            },
            "probability_calibration": probability.get(
                "probability_calibration",
                0,
            ),
            "data_provider_health": {
                "active_provider": market_health.get("active_provider", "mock"),
                "healthy": market_health.get("healthy", True),
                "fallback_used": market_health.get("fallback_used", False),
            },
            "market_freshness": market_health.get(
                "freshness",
                {"label": "Unknown", "age_seconds": None},
            ),
            "research_confidence": {
                "score": research_confidence_score,
                "label": self._research_confidence_label(research_confidence_score),
                "knowledge_score": knowledge,
                "stability_score": stability,
            },
            "policy": self.policy(),
        }

    def _market_health(self):
        try:
            from market.market_data_manager import MarketDataManager
            from market.provider_health import data_freshness

            manager = MarketDataManager()
            manager.snapshot()
            health = manager.health()
            latest_age = manager.cache_status()["stats"].get("latest_age")

            return {
                "active_provider": health.get("active_provider", "mock"),
                "healthy": health.get("healthy", True),
                "fallback_used": health.get("fallback_used", False),
                "freshness": data_freshness(latest_age),
            }
        except Exception:
            return {
                "active_provider": "mock",
                "healthy": True,
                "fallback_used": False,
                "freshness": {"label": "Unknown", "age_seconds": None},
            }

    def _research_confidence_label(self, score):
        if score >= 80:
            return "High"
        if score >= 60:
            return "Moderate"
        if score > 0:
            return "Developing"
        return "Insufficient"

    def policy(self):
        return {
            "read_only": True,
            "deterministic": True,
            "paper_trading_only": True,
            "changes_recommendation_behavior": False,
            "changes_portfolio_construction": False,
            "automatic_execution": False,
            "broker_integration": False,
            "human_approval_required": True,
        }

    # ------------------------------------------------------------------
    # Data loading with graceful, deterministic demo fallbacks
    # ------------------------------------------------------------------
    def _load(
        self,
        portfolio_history=None,
        performance_reports=None,
        experiments=None,
        validations=None,
        journals=None,
        source_data=None,
        paper_trades=None,
    ):
        demo = False

        if portfolio_history is None:
            from database.repository import (
                get_demo_paper_portfolio_history,
                get_paper_portfolio_history,
            )

            portfolio_history = get_paper_portfolio_history(limit=200)
            if not portfolio_history:
                portfolio_history = get_demo_paper_portfolio_history(limit=200)
                demo = True

        if performance_reports is None:
            from database.repository import (
                get_demo_paper_performance_reports,
                get_paper_performance_reports,
            )

            performance_reports = get_paper_performance_reports(limit=200)
            if not performance_reports:
                performance_reports = get_demo_paper_performance_reports(
                    limit=200,
                )

        if paper_trades is None:
            from database.repository import (
                get_demo_paper_trades,
                get_paper_trades,
            )

            paper_trades = get_paper_trades(limit=200)
            if not paper_trades:
                paper_trades = get_demo_paper_trades(limit=200)

        if experiments is None:
            from database.repository import get_registry_experiments

            experiments = get_registry_experiments(limit=200)
            if not experiments:
                experiments = self.research_lab.default_experiments()

        if validations is None:
            from database.repository import get_scientific_validation_reports

            validations = get_scientific_validation_reports(limit=200)

        if journals is None:
            from database.repository import get_daily_journals

            journals = get_daily_journals(limit=200)

        if source_data is None:
            from database.repository import get_discovery_source_data

            source_data = get_discovery_source_data()

        return {
            "history": portfolio_history or [],
            "performance_reports": performance_reports or [],
            "experiments": experiments or [],
            "validations": validations or [],
            "journals": journals or [],
            "source_data": source_data or {},
            "paper_trades": paper_trades or [],
            "demo": demo,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ordered_history(self, history):
        return sorted(
            history or [],
            key=lambda item: (item.get("date", ""), item.get("id", 0)),
        )

    def _performances(self, performance_reports):
        return [
            report.get("performance", report)
            for report in (performance_reports or [])
        ]

    def _benchmark_diffs(self, performances, benchmark):
        diffs = []

        for performance in performances:
            for item in performance.get("benchmark_comparison", []):
                if item.get("benchmark") == benchmark:
                    diffs.append(item.get("alpha", 0))

        return diffs

    def _window_return(self, values, window):
        if len(values) < 2:
            return 0

        window = min(window, len(values) - 1)
        current = values[-1]
        previous = values[-1 - window]

        if not previous:
            return 0

        return round((current - previous) / previous * 100, 4)

    def _drawdown_series(self, values):
        if not values:
            return []

        peak = values[0]
        series = []

        for value in values:
            peak = max(peak, value)
            if peak:
                series.append(round((value - peak) / peak * 100, 4))
            else:
                series.append(0)

        return series

    def _calmar(self, cumulative_return, max_drawdown):
        if not max_drawdown:
            return 0

        return round(cumulative_return / abs(max_drawdown), 4)

    def _action_success_rate(self, recommendations, actions):
        rows = [
            item for item in recommendations
            if str(item.get("action", "")).upper() in actions
            and isinstance(item.get("validation_result"), dict)
            and item["validation_result"].get("success") is not None
        ]
        wins = [
            item for item in rows
            if item["validation_result"].get("success") is True
        ]

        return self._rate(len(wins), len(rows))

    def _major_lessons(self, journals):
        from engines.daily_journal_engine import DailyJournalEngine

        return DailyJournalEngine().monthly_summary(journals)["major_lessons"]

    def _trade_digest(self, trade):
        return {
            "ticker": trade.get("ticker"),
            "action": trade.get("action"),
            "profit_loss": trade.get("profit_loss", 0),
            "holding_period": trade.get("holding_period", 0),
            "reason": trade.get("reason", ""),
        }

    def _validation_summary(self, validations):
        decisions = {}
        results = {}

        for validation in validations:
            decision = validation.get("adoption_decision", "Unknown")
            result = validation.get("scientific_result", "Unknown")
            decisions[decision] = decisions.get(decision, 0) + 1
            results[result] = results.get(result, 0) + 1

        return {
            "validation_count": len(validations),
            "decision_distribution": decisions,
            "result_distribution": results,
        }

    def _latest_date(self, history):
        ordered = self._ordered_history(history)

        return self._short_date(ordered[-1].get("date")) if ordered else ""

    def _latest_month(self, ordered_history, journals):
        if ordered_history:
            return self._short_date(ordered_history[-1].get("date"))[:7]

        if journals:
            latest = sorted(
                journals,
                key=lambda item: item.get("date", ""),
            )[-1]
            return self._short_date(latest.get("date"))[:7]

        return "2026-06"

    def _short_date(self, value):
        return str(value or "")[:10]

    def _standard_deviation(self, values):
        return self.paper_engine._standard_deviation(values)

    def _average(self, values):
        clean = [value for value in values if value is not None]

        if not clean:
            return 0

        return round(sum(clean) / len(clean), 4)

    def _rate(self, numerator, denominator):
        if denominator == 0:
            return 0

        return round(numerator / denominator * 100, 2)
