import hashlib
from datetime import datetime


class ResearchEngine:
    DEFAULT_TOGGLES = {
        "use_technical": True,
        "use_fundamentals": True,
        "use_forecast": True,
        "use_news": True,
        "use_portfolio": True,
        "use_risk": True,
        "use_committee": True,
        "use_executive_review": True,
        "use_hypothesis": True,
        "use_discovery": True,
    }
    DEFAULT_STRATEGIES = [
        {
            "strategy_name": "Technical only",
            "components": ["Technical"],
        },
        {
            "strategy_name": "Technical + Forecast",
            "components": ["Technical", "Forecast"],
        },
        {
            "strategy_name": "Technical + Forecast + Fundamentals",
            "components": ["Technical", "Forecast", "Fundamental"],
        },
        {
            "strategy_name": "Everything",
            "components": [
                "Technical",
                "Forecast",
                "Fundamental",
                "News",
                "Portfolio",
                "Risk",
            ],
        },
    ]

    def create_experiment(
        self,
        title,
        description,
        dataset,
        ticker_list,
        provider_configuration=None,
        forecast_provider="mock",
        news_provider="fake",
        fundamental_provider="mock",
        validation_window=30,
        benchmark_snapshot=None,
        related_discoveries=None,
        status="Planned",
        notes="",
        experiment_date=None,
        toggles=None,
    ):
        date = experiment_date or datetime.now().isoformat()
        provider_configuration = provider_configuration or {}
        benchmark_snapshot = benchmark_snapshot or {}
        related_discoveries = related_discoveries or []
        experiment_toggles = dict(self.DEFAULT_TOGGLES)
        experiment_toggles.update(toggles or {})

        experiment = {
            "experiment_id": self.generate_experiment_id(
                title,
                date,
                dataset,
                ticker_list,
            ),
            "title": title,
            "description": description,
            "date": date,
            "dataset": dataset,
            "ticker_list": list(ticker_list),
            "provider_configuration": provider_configuration,
            "forecast_provider": forecast_provider,
            "news_provider": news_provider,
            "fundamental_provider": fundamental_provider,
            "validation_window": validation_window,
            "benchmark_snapshot": benchmark_snapshot,
            "related_discoveries": related_discoveries,
            "toggles": experiment_toggles,
            "disabled_subsystems": [
                toggle.replace("use_", "")
                for toggle, enabled in experiment_toggles.items()
                if not enabled
            ],
            "status": status,
            "notes": notes,
        }

        return experiment

    def generate_experiment_id(self, title, date, dataset, ticker_list):
        seed = "|".join([
            title,
            date,
            dataset,
            ",".join(sorted(ticker_list)),
        ])
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]

        return f"arl-{digest}"

    def compare_strategies(self, strategies=None):
        results = []

        for strategy in strategies or self.DEFAULT_STRATEGIES:
            validations = strategy.get("validation_results", [])
            returns = [
                result.get("percentage_return")
                for result in validations
                if result.get("percentage_return") is not None
            ]
            hits = [
                result for result in validations
                if result.get("success") is True or result.get("hit") is True
            ]
            gains = [value for value in returns if value > 0]
            losses = [value for value in returns if value < 0]
            count = len(validations)

            results.append({
                "strategy_name": strategy.get("strategy_name"),
                "components": strategy.get("components", []),
                "recommendation_count": count,
                "hit_rate": self._rate(len(hits), count),
                "average_return": self._average(returns),
                "average_gain": self._average(gains),
                "average_loss": self._average(losses),
                "confidence": self._average([
                    result.get("confidence", 0)
                    for result in validations
                ]),
                "runtime": strategy.get("runtime", 0),
                "missing_data": strategy.get("missing_data", []),
            })

        return results

    def compare_providers(self, providers):
        rows = []

        for provider_type, provider_results in providers.items():
            ranked = sorted(
                provider_results,
                key=lambda item: item.get("score", 0),
                reverse=True,
            )

            for index, provider in enumerate(ranked, start=1):
                rows.append({
                    "provider_type": provider_type,
                    "provider_name": provider.get("provider_name"),
                    "status": provider.get("status", "Available"),
                    "score": provider.get("score", 0),
                    "rank": index,
                    "notes": provider.get("notes", ""),
                })

        return rows

    def attribute_recommendation(self, recommendation):
        evidence = self._get(recommendation, "evidence_breakdown", [])
        weighted = [
            {
                "name": item.get("category", item.get("name", "Unknown")),
                "score": item.get("score", 0),
                "weight": item.get("weight", 0),
                "confidence": item.get("confidence", 0),
            }
            for item in evidence
            if isinstance(item, dict)
        ]

        strongest = max(
            weighted,
            key=lambda item: item["score"] * item["weight"],
            default={"name": "Unknown"},
        )
        weakest_confidence = min(
            weighted,
            key=lambda item: item["confidence"],
            default={"name": "Unknown"},
        )
        changed = [
            item["name"] for item in weighted
            if item["score"] >= 70 or item["score"] < 50
        ]

        return {
            "ticker": self._get(recommendation, "ticker", ""),
            "action": self._get(recommendation, "action", ""),
            "strongest_engine": strongest["name"],
            "confidence_drag_engine": weakest_confidence["name"],
            "changed_evidence": changed,
            "notes": "Attribution is calculated from evidence score, weight, and confidence.",
        }

    def run_experiment(
        self,
        experiment,
        strategies=None,
        providers=None,
        recommendations=None,
    ):
        strategy_results = self.compare_strategies(strategies)
        provider_results = self.compare_providers(providers or {})
        attributions = [
            self.attribute_recommendation(recommendation)
            for recommendation in (recommendations or [])
        ]
        hypothesis_analysis = self.analyze_hypotheses(
            recommendations or []
        )
        executive_analysis = self.analyze_executive_reviews(
            recommendations or []
        )
        evidence_ranking_report = self.evidence_ranking_report(
            recommendations or []
        )
        knowledge_graph = self.analyze_knowledge_graph(
            recommendations or [],
            provider_results,
            experiment,
        )

        return {
            "experiment": experiment,
            "strategy_results": strategy_results,
            "provider_results": provider_results,
            "attributions": attributions,
            "hypothesis_analysis": hypothesis_analysis,
            "executive_analysis": executive_analysis,
            "evidence_ranking_report": evidence_ranking_report,
            "knowledge_graph": knowledge_graph,
            "executive_summary": self._executive_summary(
                experiment,
                strategy_results,
                provider_results,
            ),
            "recommendations": self._next_actions(
                strategy_results,
                provider_results,
            ),
            "next_experiments": [
                "Test provider alternatives against the same validation window.",
                "Compare evidence combinations with low-confidence cases removed.",
            ],
            "future_work": [
                "Add larger historical datasets.",
                "Add normalized research report persistence if report volume grows.",
            ],
        }

    def persist_report(self, report):
        from database.repository import (
            save_research_attributions,
            save_research_experiment,
            save_research_provider_results,
            save_research_strategy_results,
        )

        experiment = report["experiment"]
        experiment_id = experiment["experiment_id"]
        save_research_experiment(experiment)
        save_research_strategy_results(
            experiment_id,
            report["strategy_results"],
        )
        save_research_provider_results(
            experiment_id,
            report["provider_results"],
        )
        save_research_attributions(
            experiment_id,
            report["attributions"],
        )

    def generate_markdown_report(self, report):
        experiment = report["experiment"]
        lines = [
            f"# Atlas Research Lab Report: {experiment['title']}",
            "",
            "## Executive Summary",
            report["executive_summary"],
            "",
            "## Experiment Configuration",
            f"- Experiment ID: {experiment['experiment_id']}",
            f"- Dataset: {experiment['dataset']}",
            f"- Tickers: {', '.join(experiment['ticker_list'])}",
            f"- Forecast Provider: {experiment['forecast_provider']}",
            f"- News Provider: {experiment['news_provider']}",
            f"- Fundamental Provider: {experiment['fundamental_provider']}",
            f"- Validation Window: {experiment['validation_window']}",
            (
                "- Disabled Subsystems: "
                f"{', '.join(experiment.get('disabled_subsystems', [])) or 'None'}"
            ),
            "",
            "## Results",
        ]

        for result in report["strategy_results"]:
            lines.append(
                "- "
                f"{result['strategy_name']}: "
                f"{result['hit_rate']}% hit rate, "
                f"{result['average_return']}% average return"
            )

        lines.extend(["", "## Provider Comparison"])
        for provider in report["provider_results"]:
            lines.append(
                "- "
                f"{provider['provider_type']} / {provider['provider_name']}: "
                f"rank {provider['rank']}, score {provider['score']}"
            )

        hypothesis = report.get("hypothesis_analysis", {})
        lines.extend(["", "## Hypothesis Analysis"])
        lines.append(
            "- Most frequent counterfactuals: "
            f"{', '.join(hypothesis.get('frequent_counterfactuals', [])) or 'None'}"
        )
        lines.append(
            "- Highest accuracy assumptions: "
            f"{', '.join(hypothesis.get('highest_accuracy_assumptions', [])) or 'None'}"
        )
        lines.append(
            "- Failed assumptions: "
            f"{', '.join(hypothesis.get('failed_assumptions', [])) or 'None'}"
        )

        executive = report.get("executive_analysis", {})
        lines.extend(["", "## Executive Review Analysis"])
        lines.append(
            "- Common warnings: "
            f"{', '.join(executive.get('common_warnings', [])) or 'None'}"
        )
        lines.append(
            "- Frequent missing evidence: "
            f"{', '.join(executive.get('frequent_missing_evidence', [])) or 'None'}"
        )
        lines.append(
            "- Executive false positives: "
            f"{executive.get('executive_false_positives', 0)}"
        )
        lines.append(
            "- Executive false negatives: "
            f"{executive.get('executive_false_negatives', 0)}"
        )

        evidence_report = report.get("evidence_ranking_report", {})
        lines.extend(["", "## Evidence Ranking Report"])
        lines.append(
            "- Strongest Evidence Category: "
            f"{evidence_report.get('strongest_evidence_category', 'Unavailable')}"
        )
        lines.append(
            "- Weakest Evidence Category: "
            f"{evidence_report.get('weakest_evidence_category', 'Unavailable')}"
        )
        for item in evidence_report.get("evidence_rankings", [])[:5]:
            lines.append(
                "- "
                f"{item['category']}: score {item['contribution_score']}, "
                f"{item['hit_rate']}% hit rate, "
                f"{item['average_return']}% average return, "
                f"sample {item['sample_size']}"
            )

        graph = report.get("knowledge_graph", {})
        lines.extend(["", "## Knowledge Graph"])
        lines.append(f"- Nodes: {graph.get('node_count', 0)}")
        lines.append(f"- Relationships: {graph.get('relationship_count', 0)}")
        lines.append(
            "- Institutional Summary: "
            f"{graph.get('summary', 'No graph summary available.')}"
        )

        lines.extend(["", "## Recommendations"])
        lines.extend([f"- {item}" for item in report["recommendations"]])
        lines.extend(["", "## Next Experiments"])
        lines.extend([f"- {item}" for item in report["next_experiments"]])
        lines.extend(["", "## Future Work"])
        lines.extend([f"- {item}" for item in report["future_work"]])

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Atlas Brain - explainability composition (read-only)
    # ------------------------------------------------------------------
    def brain_report(self, ticker, source_data=None, generation_time=None):
        """Compose an explainable Atlas Brain report for a ticker.

        This is not a new engine. It reuses existing Atlas outputs
        (RecommendationEngine, ProbabilityEngine, ResearchMemoryEngine,
        PortfolioConstructionEngine, and PerformanceAnalyticsEngine) and only
        reformats them into one coherent explanation. It is read-only and
        changes no recommendation, probability, or portfolio behavior.
        """
        from datetime import datetime

        from engines.performance_analytics_engine import PerformanceAnalyticsEngine
        from engines.probability_engine import ProbabilityEngine
        from engines.recommendation_engine import RecommendationEngine
        from engines.research_memory_engine import ResearchMemoryEngine

        ticker = (ticker or "").upper()
        if source_data is None:
            from database.repository import get_discovery_source_data

            source_data = get_discovery_source_data()

        recommendation, available = self._brain_recommendation(ticker, source_data)
        probability_report = (
            recommendation.get("probability_report")
            if isinstance(recommendation.get("probability_report"), dict)
            else None
        )
        if not probability_report:
            probability_report = ProbabilityEngine().estimate(
                recommendation,
                history=source_data.get("recommendations", []),
                case_studies=source_data.get("case_studies", []),
            )

        explanation = RecommendationEngine().explain(recommendation)
        probability_detail = ProbabilityEngine().explain(report=probability_report)

        try:
            memory = ResearchMemoryEngine().build(
                recommendation,
                source_data=source_data,
            )
        except Exception:
            memory = {"similar_historical_cases": [], "lessons": {}}

        trust = PerformanceAnalyticsEngine().trust_indicators(
            recommendation=recommendation,
            source_data=source_data,
        )
        contributions = explanation["engine_contributions"]

        return {
            "ticker": ticker,
            "available": available,
            "demo_data": not available,
            "generated_at": generation_time or datetime.now().isoformat(),
            "overview": self._brain_overview(recommendation, probability_detail),
            "decision_flow": explanation["decision_flow"],
            "evidence_contribution": {
                "items": contributions,
                "top_category": contributions[0]["category"] if contributions else None,
                "total": 100 if contributions else 0,
            },
            "engine_contributions": contributions,
            "confidence_breakdown": explanation["confidence_breakdown"],
            "decision_tree": explanation["decision_tree"],
            "reasoning_summary": explanation["reasoning_summary"],
            "timeline": self._brain_timeline(recommendation, probability_detail),
            "historical_influence": self._brain_historical_influence(
                memory,
                source_data,
                recommendation,
            ),
            "portfolio_impact": self._brain_portfolio_impact(
                recommendation,
                source_data,
            ),
            "catalyst_impact": self._brain_catalyst_impact(recommendation),
            "probability_detail": probability_detail,
            "trust_indicators": trust,
            "policy": {
                "read_only": True,
                "explainability_only": True,
                "changes_recommendation_behavior": False,
                "changes_probabilities": False,
                "changes_portfolio_construction": False,
                "automatic_execution": False,
                "broker_integration": False,
                "human_approval_required": True,
            },
        }

    def brain_summary(self, ticker, source_data=None):
        report = self.brain_report(ticker, source_data=source_data)

        return {
            "ticker": report["ticker"],
            "available": report["available"],
            "demo_data": report["demo_data"],
            "overview": report["overview"],
            "reasoning_summary": report["reasoning_summary"],
            "trust_indicators": report["trust_indicators"],
            "policy": report["policy"],
        }

    def brain_evidence(self, ticker, source_data=None):
        report = self.brain_report(ticker, source_data=source_data)

        return {
            "ticker": report["ticker"],
            "demo_data": report["demo_data"],
            "evidence_contribution": report["evidence_contribution"],
            "engine_contributions": report["engine_contributions"],
            "confidence_breakdown": report["confidence_breakdown"],
            "policy": report["policy"],
        }

    def brain_timeline(self, ticker, source_data=None):
        report = self.brain_report(ticker, source_data=source_data)

        return {
            "ticker": report["ticker"],
            "demo_data": report["demo_data"],
            "timeline": report["timeline"],
            "decision_flow": report["decision_flow"],
            "decision_tree": report["decision_tree"],
            "policy": report["policy"],
        }

    def _brain_recommendation(self, ticker, source_data):
        for item in source_data.get("recommendations", []):
            if str(item.get("ticker", "")).upper() == ticker:
                return item, True

        return self._brain_demo_recommendation(ticker), False

    def _brain_overview(self, recommendation, probability_detail):
        return {
            "ticker": recommendation.get("ticker", ""),
            "recommendation": recommendation.get("action", "Unavailable"),
            "confidence": recommendation.get("confidence", 0),
            "probability": probability_detail.get("outperformance_probability", 0),
            "knowledge_score": recommendation.get("knowledge_score", 0),
            "stability_score": recommendation.get("stability_score", 0),
            "executive_review": recommendation.get("executive_status", "Unavailable"),
            "committee_decision": {
                "agreement": recommendation.get("committee_agreement", 0),
                "summary": recommendation.get("final_committee_summary", ""),
            },
        }

    def _brain_timeline(self, recommendation, probability_detail):
        macro_regime = recommendation.get("market_regime", "current regime")
        steps = [
            ("Market opens", "Validated market data is ingested for the ticker."),
            (
                "Macro evaluated",
                f"Macro regime context assessed ({macro_regime}).",
            ),
            (
                "Forecast generated",
                "Deterministic forecast direction "
                f"{recommendation.get('forecast_direction', 'neutral')} with "
                f"confidence {recommendation.get('forecast_confidence', 0)}.",
            ),
            (
                "Committee discussion",
                recommendation.get("final_committee_summary")
                or f"Committee agreement {recommendation.get('committee_agreement', 0)}%.",
            ),
            (
                "Probability computed",
                f"Outperformance probability "
                f"{probability_detail.get('outperformance_probability', 0)}% "
                f"({probability_detail.get('uncertainty_level', 'Unknown')} uncertainty).",
            ),
            (
                "Portfolio impact",
                "Paper portfolio allocation and risk budget evaluated.",
            ),
            (
                "Recommendation finalized",
                f"{recommendation.get('action', 'Unavailable')} at "
                f"{recommendation.get('confidence', 0)}% confidence.",
            ),
        ]

        return [
            {"step": index + 1, "label": label, "detail": detail}
            for index, (label, detail) in enumerate(steps)
        ]

    def _brain_historical_influence(self, memory, source_data, recommendation):
        analogs = memory.get("similar_historical_cases", []) or []
        lessons = memory.get("lessons", {}) or {}
        ticker = str(recommendation.get("ticker", "")).upper()
        case_studies = [
            case for case in source_data.get("case_studies", [])
            if str(case.get("ticker", "")).upper() == ticker
        ]
        similarity_scores = [
            analog.get("similarity_score", 0)
            for analog in analogs
            if analog.get("similarity_score") is not None
        ]

        return {
            "analogs": analogs[:5],
            "case_studies": case_studies[:5],
            "average_similarity": (
                round(sum(similarity_scores) / len(similarity_scores), 2)
                if similarity_scores
                else 0
            ),
            "past_outcomes": {
                "win_rate": lessons.get("win_rate", 0),
                "average_historical_return": lessons.get(
                    "average_historical_return",
                    0,
                ),
                "average_holding_period": lessons.get("average_holding_period", 0),
            },
            "research_memory": {
                "common_successful_patterns": lessons.get(
                    "common_successful_patterns",
                    [],
                ),
                "common_failure_patterns": lessons.get(
                    "common_failure_patterns",
                    [],
                ),
                "explanation": lessons.get("explanation", ""),
            },
        }

    def _brain_portfolio_impact(self, recommendation, source_data):
        ticker = str(recommendation.get("ticker", "")).upper()

        try:
            from engines.portfolio_construction_engine import (
                PortfolioConstructionEngine,
            )

            engine = PortfolioConstructionEngine()
            report = engine.build(
                recommendations=[recommendation],
                paper_portfolio=engine.demo_portfolio(),
            )
            operations = report.get("operations_summary", {})
            allocation = next(
                (
                    item for item in report.get("recommended_allocations", [])
                    if str(item.get("ticker", "")).upper() == ticker
                ),
                {},
            )

            return {
                "allocation": {
                    "ticker": ticker,
                    "target_weight": allocation.get("target_weight", 0),
                    "action": allocation.get("action", "Hold"),
                    "rationale": allocation.get("rationale", ""),
                },
                "risk_budget": report.get("risk_summary", {}),
                "sector_impact": {
                    "most_concentrated_sector": operations.get(
                        "most_concentrated_sector",
                    ),
                    "sector": allocation.get("sector", "Unknown"),
                },
                "cash_impact": {
                    "suggested_rebalance": operations.get(
                        "suggested_rebalance",
                        "Maintain",
                    ),
                    "largest_position": operations.get("largest_position", 0),
                },
                "diversification_impact": report.get("diversification", {}),
                "policy": report.get("policy", {}),
            }
        except Exception as error:
            return {
                "allocation": {"ticker": ticker, "target_weight": 0},
                "risk_budget": {},
                "sector_impact": {},
                "cash_impact": {},
                "diversification_impact": {},
                "note": f"Portfolio impact unavailable: {error}",
            }

    def _brain_catalyst_impact(self, recommendation):
        catalysts = recommendation.get("catalysts", []) or []
        most_important = None

        for catalyst in catalysts:
            if not isinstance(catalyst, dict):
                continue
            if most_important is None:
                most_important = catalyst
                continue
            if (catalyst.get("days_until_event") or 999) < (
                most_important.get("days_until_event") or 999
            ):
                most_important = catalyst

        return {
            "catalysts": catalysts[:6],
            "event_count": len(catalysts),
            "most_important": most_important,
            "summary": (
                f"{len(catalysts)} upcoming catalysts tracked."
                if catalysts
                else "No upcoming catalysts recorded for this ticker."
            ),
        }

    def _brain_demo_recommendation(self, ticker):
        return {
            "ticker": ticker,
            "action": "BUY",
            "confidence": 82,
            "signal_quality_score": 8,
            "rating": "Attractive",
            "overall_score": 78,
            "validation_status": "Pending",
            "technical_score": 72,
            "fundamental_score": 78,
            "forecast_score": 68,
            "forecast_direction": "Up",
            "forecast_confidence": 66,
            "expected_change": 3.4,
            "portfolio_score": 64,
            "risk_score": 70,
            "news_sentiment": "Positive",
            "news_confidence": 60,
            "headline_count": 6,
            "committee_agreement": 76,
            "final_committee_summary": (
                "The committee leans constructive on strong fundamentals with "
                "measured macro caution."
            ),
            "bullish_members": ["Fundamental", "Forecast", "Technical"],
            "bearish_members": ["Macro"],
            "neutral_members": ["News"],
            "executive_status": "READY",
            "executive_confidence": 80,
            "executive_summary": (
                "Executive review is ready: evidence is coherent and risks are "
                "understood."
            ),
            "executive_warnings": [],
            "knowledge_score": 80,
            "knowledge_level": "Good Knowledge",
            "stability_score": 78,
            "stability_level": "Stable",
            "most_sensitive_factor": "committee agreement",
            "top_positive_factors": [
                "Strong fundamentals with durable margins.",
                "Constructive technical trend.",
                "Committee agreement is high.",
            ],
            "top_negative_factors": [
                "Macro regime adds uncertainty.",
                "Earnings catalyst is approaching.",
            ],
            "missing_evidence": [],
            "assumptions": [
                "Fundamentals remain durable through the next quarter.",
                "No adverse macro shock before the earnings catalyst.",
            ],
            "counterfactuals": [
                {"scenario": "Weak earnings guidance", "impact": "Would reduce confidence."},
            ],
            "recommendation_flip_conditions": [
                "A material fundamentals downgrade would flip to HOLD.",
            ],
            "evidence_breakdown": [
                {"category": "Fundamentals", "score": 78, "weight": 0.30, "confidence": 80, "summary": "Durable margins and healthy balance sheet."},
                {"category": "Technical", "score": 72, "weight": 0.25, "confidence": 74, "summary": "Constructive trend above key moving averages."},
                {"category": "Forecast", "score": 68, "weight": 0.15, "confidence": 66, "summary": "Deterministic forecast points modestly higher."},
                {"category": "News", "score": 60, "weight": 0.10, "confidence": 60, "summary": "Positive but mixed headline agreement."},
                {"category": "Macro", "score": 54, "weight": 0.08, "confidence": 58, "summary": "Neutral-to-cautious macro regime."},
                {"category": "SEC", "score": 58, "weight": 0.05, "confidence": 55, "summary": "No adverse filing signals detected."},
                {"category": "Catalysts", "score": 62, "weight": 0.04, "confidence": 60, "summary": "Earnings catalyst approaching."},
                {"category": "Committee", "score": 76, "weight": 0.03, "confidence": 76, "summary": "Committee agreement is high."},
            ],
            "catalysts": [
                {"event_type": "Earnings", "days_until_event": 9, "catalyst_group": "Company", "potential_volatility_level": "High"},
                {"event_type": "CPI", "days_until_event": 4, "catalyst_group": "Macro", "potential_volatility_level": "Medium"},
            ],
            "probability_report": {
                "ticker": ticker,
                "recommendation": "BUY",
                "probabilities": {"outperformance": 62, "market_performance": 24, "underperformance": 14},
                "expected_outcome": {"expected_return": 3.1, "expected_holding_period": 30, "sample_size": 12},
                "confidence_quality": {"uncertainty_level": "Moderate", "sample_size": 12, "similar_historical_cases": []},
                "explanation": (
                    "Historical analogs favor outperformance with moderate "
                    "uncertainty on a small sample."
                ),
                "similar_historical_cases": [],
                "policy": {"changes_recommendation_behavior": False, "automatic_execution": False, "requires_human_approval": True},
            },
            "status": "SIMULATED",
            "is_example": True,
        }

    def research_dashboard_data(self):
        from database.repository import get_research_dashboard_data

        dashboard = get_research_dashboard_data()
        dashboard["model_evaluation_report"] = self.model_evaluation_report(
            dashboard.get("model_evaluations", [])
        )
        dashboard["scientific_validation_report"] = (
            self.scientific_validation_report(
                dashboard.get("scientific_validations", [])
            )
        )
        dashboard["simulation_arena_report"] = self.simulation_arena_report(
            dashboard.get("simulation_arena_runs", [])
        )
        dashboard["paper_trading_research"] = self.paper_trading_research(
            dashboard.get("paper_trades", []),
            dashboard.get("paper_performance_reports", []),
        )
        dashboard["case_study_filters"] = self.case_study_filters(
            dashboard.get("case_studies", [])
        )
        dashboard["portfolio_strategy_research"] = (
            self.portfolio_strategy_research([])
        )
        dashboard["portfolio_construction_research"] = (
            self.portfolio_construction_research(
                dashboard.get("portfolio_construction_reports", [])
            )
        )
        dashboard["catalyst_research"] = self.catalyst_research(
            dashboard.get("recommendations", []),
        )

        return dashboard

    def catalyst_research(self, recommendations):
        return {
            "future_studies": [
                "Before earnings",
                "After earnings",
                "Macro weeks",
                "High-volatility periods",
            ],
            "filters": {
                "before_earnings": self._catalyst_filter(
                    recommendations,
                    "Earnings",
                    max_days=14,
                ),
                "after_earnings": self._catalyst_filter(
                    recommendations,
                    "Earnings",
                    min_days=-14,
                    max_days=0,
                ),
                "macro_weeks": [
                    recommendation for recommendation in recommendations
                    if any(
                        catalyst.get("catalyst_group") == "Macro"
                        for catalyst in recommendation.get("catalysts", [])
                    )
                ],
                "high_volatility_periods": [
                    recommendation for recommendation in recommendations
                    if any(
                        catalyst.get("potential_volatility_level") == "High"
                        for catalyst in recommendation.get("catalysts", [])
                    )
                ],
            },
            "policy": (
                "Catalyst studies are research only: no live trading, no "
                "guaranteed returns, validation required, and no automatic execution."
            ),
        }

    def _catalyst_filter(
        self,
        recommendations,
        event_type,
        min_days=None,
        max_days=None,
    ):
        rows = []

        for recommendation in recommendations:
            for catalyst in recommendation.get("catalysts", []):
                if catalyst.get("event_type") != event_type:
                    continue

                days = catalyst.get("days_until_event")
                if days is None:
                    continue

                if min_days is not None and days < min_days:
                    continue

                if max_days is not None and days > max_days:
                    continue

                rows.append(recommendation)
                break

        return rows

    def portfolio_strategy_research(self, reviews):
        from engines.portfolio_strategy_engine import PortfolioStrategyEngine

        return PortfolioStrategyEngine().research_summary(reviews)

    def portfolio_construction_research(self, reports):
        latest = reports[0] if reports else {}
        validation = latest.get("scientific_validation", {})

        return {
            "report_count": len(reports),
            "latest_candidate_strategy": validation.get(
                "candidate_strategy",
                "Institutional Portfolio Construction v1",
            ),
            "latest_adoption_decision": validation.get(
                "adoption_decision",
                "RETEST",
            ),
            "requires_simulation_arena": validation.get(
                "simulation_arena_required",
                True,
            ),
            "requires_scientific_validation": validation.get(
                "scientific_validation_required",
                True,
            ),
            "policy": (
                "Portfolio construction research ranks allocation candidates "
                "only; it does not change recommendations or execute trades."
            ),
        }

    def case_study_filters(self, case_studies):
        from engines.case_study_engine import CaseStudyEngine

        engine = CaseStudyEngine()

        return {
            "winning_cases": engine.filter_cases(case_studies, "winning"),
            "losing_cases": engine.filter_cases(case_studies, "losing"),
            "bull_market": engine.filter_cases(case_studies, "bull_market"),
            "bear_market": engine.filter_cases(case_studies, "bear_market"),
            "committee_disagreements": engine.filter_cases(
                case_studies,
                "committee_disagreements",
            ),
            "forecast_failures": engine.filter_cases(
                case_studies,
                "forecast_failures",
            ),
            "news_failures": engine.filter_cases(
                case_studies,
                "news_failures",
            ),
        }

    def model_evaluation_report(self, evaluations=None):
        from engines.model_evaluation_lab import ModelEvaluationLab

        lab = ModelEvaluationLab()
        rows = evaluations or []

        return {
            "model_evaluations": rows,
            "rankings": lab.rank_models(rows) if rows else {
                "best_overall": None,
                "best_accuracy": None,
                "best_risk_adjusted": None,
                "best_low_cost": None,
                "best_speed": None,
                "not_recommended": [],
                "ordered": [],
            },
            "controlled_learning": lab.controlled_learning(),
        }

    def scientific_validation_report(self, validations=None):
        rows = validations or []
        decisions = {}
        results = {}

        for row in rows:
            decision = row.get("adoption_decision", "Unknown")
            result = row.get("scientific_result", "Unknown")
            decisions[decision] = decisions.get(decision, 0) + 1
            results[result] = results.get(result, 0) + 1

        return {
            "validation_count": len(rows),
            "decision_distribution": decisions,
            "result_distribution": results,
            "latest_reports": rows[:5],
            "policy": {
                "read_only": True,
                "changes_recommendation_behavior": False,
                "automatic_adoption": False,
            },
        }

    def simulation_arena_report(self, runs=None):
        rows = runs or []
        latest = rows[0] if rows else {}

        return {
            "arena_run_count": len(rows),
            "latest_arena_id": latest.get("arena_id"),
            "latest_best_overall": (
                latest.get("comparison", {}).get("best_overall")
            ),
            "latest_not_recommended": (
                latest.get("comparison", {}).get("not_recommended", [])
            ),
            "latest_runs": rows[:5],
            "policy": {
                "read_only": True,
                "research_only": True,
                "changes_recommendation_behavior": False,
                "automatic_execution": False,
            },
        }

    def paper_trading_research(self, trades=None, performance_reports=None):
        rows = trades or []
        reports = performance_reports or []
        closed = [
            trade for trade in rows
            if trade.get("exit_price") is not None
        ]

        return {
            "best_trades": self._rank_paper_trades(closed, True)[:5],
            "worst_trades": self._rank_paper_trades(closed, False)[:5],
            "biggest_winners": self._rank_paper_trades(closed, True)[:5],
            "biggest_mistakes": self._rank_paper_trades(closed, False)[:5],
            "longest_holds": sorted(
                closed,
                key=lambda trade: (
                    trade.get("holding_period") or 0,
                    trade.get("ticker", ""),
                ),
                reverse=True,
            )[:5],
            "most_profitable_sectors": self._paper_sector_profitability(
                closed,
            ),
            "latest_performance": (
                reports[0].get("performance", {}) if reports else {}
            ),
            "policy": (
                "Paper trading research is simulated only and cannot execute "
                "orders or change recommendations."
            ),
        }

    def evidence_ranking_report(self, recommendations):
        from engines.performance_observatory import PerformanceObservatory

        return PerformanceObservatory().evidence_contribution_report(
            [
                self._recommendation_record(recommendation)
                for recommendation in recommendations
            ]
        )

    def analyze_hypotheses(self, recommendations):
        assumption_rows = []
        counterfactual_names = []

        for recommendation in recommendations:
            validation = self._get(
                recommendation,
                "validation_result",
                None,
            )
            success = None
            if isinstance(validation, dict):
                success = validation.get("success")

            for assumption in self._get(recommendation, "assumptions", []):
                assumption_rows.append({
                    "assumption": assumption,
                    "success": success,
                })

            for counterfactual in self._get(
                recommendation,
                "counterfactuals",
                [],
            ):
                if isinstance(counterfactual, dict):
                    counterfactual_names.append(
                        counterfactual.get("scenario", "")
                    )

        return {
            "failed_assumptions": self._rank_assumptions(
                assumption_rows,
                success_value=False,
            ),
            "highest_accuracy_assumptions": self._rank_assumptions(
                assumption_rows,
                success_value=True,
            ),
            "frequent_counterfactuals": self._frequent(counterfactual_names),
        }

    def analyze_executive_reviews(self, recommendations):
        warnings = []
        missing_evidence = []
        false_positives = 0
        false_negatives = 0

        for recommendation in recommendations:
            status = self._get(recommendation, "executive_status", "")
            validation = self._get(recommendation, "validation_result", None)
            success = None
            if isinstance(validation, dict):
                success = validation.get("success")

            warnings.extend(
                self._get(recommendation, "executive_warnings", []) or []
            )
            missing_evidence.extend(
                self._get(recommendation, "missing_evidence", []) or []
            )

            if success is False and status in {"READY", "CAUTION"}:
                false_positives += 1

            if success is True and status in {
                "NEEDS_REVIEW",
                "INSUFFICIENT_DATA",
            }:
                false_negatives += 1

        return {
            "common_warnings": self._frequent(warnings),
            "frequent_missing_evidence": self._frequent(missing_evidence),
            "executive_false_positives": false_positives,
            "executive_false_negatives": false_negatives,
        }

    def analyze_knowledge_graph(self, recommendations, providers, experiment):
        from engines.knowledge_graph_engine import KnowledgeGraphEngine

        source_data = {
            "recommendations": [
                self._recommendation_record(recommendation)
                for recommendation in recommendations
            ],
            "benchmark_results": [],
            "provider_results": providers,
            "research_experiments": [experiment],
        }
        graph = KnowledgeGraphEngine().build(
            source_data=source_data,
            discovery_data={"discovery_history": []},
            historical_runs=[],
        )

        return {
            "node_count": len(graph["nodes"]),
            "relationship_count": len(graph["relationships"]),
            "summary": KnowledgeGraphEngine().generate_summary(
                graph,
                "Atlas",
            ),
        }

    def _executive_summary(self, experiment, strategy_results, provider_results):
        best_strategy = max(
            strategy_results,
            key=lambda item: item.get("hit_rate", 0),
            default={"strategy_name": "None", "hit_rate": 0},
        )
        best_provider = max(
            provider_results,
            key=lambda item: item.get("score", 0),
            default={"provider_name": "None", "score": 0},
        )

        return (
            f"{experiment['title']} evaluated {len(strategy_results)} "
            f"strategies. Best strategy: {best_strategy['strategy_name']} "
            f"at {best_strategy['hit_rate']}% hit rate. Best provider: "
            f"{best_provider['provider_name']}."
        )

    def _next_actions(self, strategy_results, provider_results):
        actions = []

        if strategy_results:
            best_strategy = max(
                strategy_results,
                key=lambda item: item.get("hit_rate", 0),
            )
            actions.append(
                f"Prioritize further testing of {best_strategy['strategy_name']}."
            )

        if provider_results:
            best_provider = max(
                provider_results,
                key=lambda item: item.get("score", 0),
            )
            actions.append(
                f"Benchmark {best_provider['provider_name']} on a larger sample."
            )

        return actions or ["Collect more completed validation data."]

    def _recommendation_record(self, recommendation):
        return {
            "id": self._get(recommendation, "id", self._get(recommendation, "ticker", "")),
            "ticker": self._get(recommendation, "ticker", ""),
            "date": self._get(recommendation, "date", ""),
            "action": self._get(recommendation, "action", ""),
            "confidence": self._get(recommendation, "confidence", 0),
            "evidence_breakdown": self._get(recommendation, "evidence_breakdown", []),
            "committee_agreement": self._get(recommendation, "committee_agreement", 0),
            "main_disagreement": self._get(recommendation, "main_disagreement", ""),
            "executive_status": self._get(recommendation, "executive_status", ""),
            "executive_confidence": self._get(recommendation, "executive_confidence", 0),
            "executive_warnings": self._get(recommendation, "executive_warnings", []),
            "discovery_score": self._get(recommendation, "discovery_score", None),
            "assumptions": self._get(recommendation, "assumptions", []),
            "counterfactuals": self._get(recommendation, "counterfactuals", []),
            "validation_result": self._get(recommendation, "validation_result", None),
        }

    def _average(self, values):
        if not values:
            return 0

        return round(sum(values) / len(values), 2)

    def _rate(self, numerator, denominator):
        if denominator == 0:
            return 0

        return round(numerator / denominator * 100, 2)

    def _rank_paper_trades(self, trades, reverse):
        return sorted(
            trades,
            key=lambda trade: (
                trade.get("profit_loss", 0),
                trade.get("ticker", ""),
            ),
            reverse=reverse,
        )

    def _paper_sector_profitability(self, trades):
        totals = {}

        for trade in trades:
            sector = (
                trade.get("recommendation_snapshot", {}).get("sector")
                or "Unknown"
            )
            totals[sector] = round(
                totals.get(sector, 0) + trade.get("profit_loss", 0),
                2,
            )

        return [
            {"sector": sector, "profit_loss": profit_loss}
            for sector, profit_loss in sorted(
                totals.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]

    def _rank_assumptions(self, rows, success_value):
        counts = {}

        for row in rows:
            if row["success"] is not success_value:
                continue

            assumption = row["assumption"]
            counts[assumption] = counts.get(assumption, 0) + 1

        return [
            item[0] for item in sorted(
                counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[:5]
        ]

    def _frequent(self, values):
        counts = {}

        for value in values:
            if not value:
                continue

            counts[value] = counts.get(value, 0) + 1

        return [
            item[0] for item in sorted(
                counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[:5]
        ]

    def _get(self, item, key, fallback):
        if isinstance(item, dict):
            return item.get(key, fallback)

        return getattr(item, key, fallback)
