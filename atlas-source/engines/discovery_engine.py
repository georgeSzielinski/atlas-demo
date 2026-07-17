import hashlib
from datetime import datetime


class DiscoveryEngine:
    tiny_sample_threshold = 5

    def analyze(self, source_data=None, discovery_date=None):
        if source_data is None:
            from database.repository import get_discovery_source_data

            source_data = get_discovery_source_data()

        date = discovery_date or datetime.now().isoformat()
        discoveries = []
        discoveries.extend(
            self._evidence_combination_discoveries(source_data, date)
        )
        discoveries.extend(
            self._evidence_contribution_discoveries(source_data, date)
        )
        discoveries.extend(
            self._market_regime_discoveries(source_data, date)
        )
        discoveries.extend(
            self._macro_discoveries(source_data, date)
        )
        discoveries.extend(
            self._committee_agreement_discoveries(source_data, date)
        )
        discoveries.extend(
            self._provider_performance_discoveries(source_data, date)
        )
        discoveries.extend(
            self._model_evaluation_discoveries(source_data, date)
        )
        discoveries.extend(
            self._scientific_validation_discoveries(source_data, date)
        )
        discoveries.extend(
            self._simulation_arena_discoveries(source_data, date)
        )
        discoveries.extend(
            self._case_study_discoveries(source_data, date)
        )
        discoveries.extend(
            self._portfolio_strategy_discoveries(source_data, date)
        )
        discoveries.extend(
            self._portfolio_construction_discoveries(source_data, date)
        )
        discoveries.extend(
            self._catalyst_discoveries(source_data, date)
        )
        discoveries.extend(
            self._probability_discoveries(source_data, date)
        )
        discoveries.extend(
            self._research_memory_discoveries(source_data, date)
        )
        discoveries.extend(
            self._forecast_performance_discoveries(source_data, date)
        )
        discoveries.extend(
            self._confidence_calibration_discoveries(source_data, date)
        )
        discoveries.extend(
            self._validation_success_discoveries(source_data, date)
        )
        discoveries.extend(
            self._benchmark_trend_discoveries(source_data, date)
        )
        discoveries.append(self._sector_trend_placeholder(source_data, date))

        ranked = sorted(
            discoveries,
            key=lambda item: (
                item["importance"],
                item["confidence"],
                item["sample_size"],
            ),
            reverse=True,
        )
        graph_context = self._knowledge_graph_context(source_data, ranked)

        for discovery in ranked:
            discovery["knowledge_graph_context"] = graph_context

        return ranked

    def persist_discoveries(self, discoveries):
        from database.repository import save_discoveries

        save_discoveries(discoveries)

    def discovery_dashboard_data(self):
        from database.repository import get_discovery_dashboard_data

        return get_discovery_dashboard_data()

    def _knowledge_graph_context(self, source_data, discoveries):
        from engines.knowledge_graph_engine import KnowledgeGraphEngine

        graph = KnowledgeGraphEngine().build(
            source_data=source_data,
            discovery_data={"discovery_history": discoveries},
            historical_runs=[],
        )

        return {
            "node_count": len(graph["nodes"]),
            "relationship_count": len(graph["relationships"]),
            "failed_recommendations": KnowledgeGraphEngine().most_common_failures(
                graph
            )[:5],
        }

    def _evidence_combination_discoveries(self, source_data, date):
        groups = {}

        for recommendation in source_data.get("recommendations", []):
            validation = recommendation.get("validation_result")
            evidence = recommendation.get("evidence_breakdown", [])
            combination = tuple(sorted([
                item.get("category", item.get("name"))
                for item in evidence
                if isinstance(item, dict)
                and item.get("score", 0) >= 70
                and (item.get("category") or item.get("name"))
            ]))

            if not combination:
                combination = ("No strong evidence",)

            groups.setdefault(combination, []).append(validation)

        if not groups:
            return [
                self._record(
                    title="No evidence combination history available",
                    description=(
                        "Atlas does not yet have enough recommendation "
                        "history to compare evidence combinations."
                    ),
                    supporting_data={},
                    sample_size=0,
                    importance=20,
                    date=date,
                    related_engines=["EvidenceEngine"],
                    warnings=["No sample available."],
                    suggestions=["Collect validated recommendation history."],
                )
            ]

        ranked = sorted(
            [
                (combination, self._success_rate(validations), validations)
                for combination, validations in groups.items()
            ],
            key=lambda item: item[1],
            reverse=True,
        )
        best = ranked[0]
        weakest = ranked[-1]

        return [
            self._record(
                title="Highest-performing evidence combination",
                description=(
                    f"{', '.join(best[0])} has the highest observed "
                    f"validation success rate at {best[1]}%."
                ),
                supporting_data={
                    "combination": list(best[0]),
                    "success_rate": best[1],
                },
                sample_size=len(best[2]),
                importance=85 if best[1] >= 60 else 55,
                date=date,
                related_engines=["EvidenceEngine", "ValidationEngine"],
                suggestions=[
                    f"Investigate whether {', '.join(best[0])} deserves more controlled testing."
                ],
            ),
            self._record(
                title="Weakest evidence combination",
                description=(
                    f"{', '.join(weakest[0])} has the weakest observed "
                    f"validation success rate at {weakest[1]}%."
                ),
                supporting_data={
                    "combination": list(weakest[0]),
                    "success_rate": weakest[1],
                },
                sample_size=len(weakest[2]),
                importance=75 if weakest[1] < 50 else 45,
                date=date,
                related_engines=["EvidenceEngine", "ValidationEngine"],
                suggestions=[
                    f"Review whether {', '.join(weakest[0])} is creating noisy evidence."
                ],
            ),
        ]

    def _evidence_contribution_discoveries(self, source_data, date):
        from engines.performance_observatory import PerformanceObservatory

        report = PerformanceObservatory().evidence_contribution_report(
            source_data.get("recommendations", [])
        )
        rankings = [
            item for item in report["evidence_rankings"]
            if item["sample_size"] > 0
        ]

        if len(rankings) < 2:
            return []

        strongest = rankings[0]
        weakest = rankings[-1]
        gap = round(
            strongest["average_return"] - weakest["average_return"],
            2,
        )
        discoveries = [
            self._record(
                title="Evidence contribution leader",
                description=(
                    f"{strongest['category']} outperforms "
                    f"{weakest['category']} by {gap}%."
                ),
                supporting_data={
                    "strongest_category": strongest["category"],
                    "weakest_category": weakest["category"],
                    "average_return_gap": gap,
                    "evidence_rankings": rankings,
                },
                sample_size=strongest["sample_size"] + weakest["sample_size"],
                importance=80 if gap > 5 else 55,
                date=date,
                related_engines=["EvidenceEngine", "PerformanceObservatory"],
                suggestions=[
                    "Use contribution rankings as research evidence only; do not auto-reweight evidence."
                ],
            )
        ]

        trend = self._category_contribution_trend(
            "Forecast",
            source_data.get("recommendations", []),
        )
        if trend is not None:
            direction = "increased" if trend["change"] >= 0 else "decreased"
            discoveries.append(
                self._record(
                    title="Forecast contribution trend",
                    description=(
                        f"Forecast contribution has {direction} over time "
                        f"by {abs(trend['change'])}%."
                    ),
                    supporting_data=trend,
                    sample_size=trend["sample_size"],
                    importance=70 if abs(trend["change"]) >= 5 else 45,
                    date=date,
                    related_engines=[
                        "ForecastEngine",
                        "EvidenceEngine",
                        "PerformanceObservatory",
                    ],
                    suggestions=[
                        "Validate the trend on a larger sample before changing forecast usage."
                    ],
                )
            )

        return discoveries

    def _market_regime_discoveries(self, source_data, date):
        from engines.performance_observatory import PerformanceObservatory

        summaries = PerformanceObservatory().performance_by_regime(
            source_data.get("recommendations", [])
        )
        populated = [
            item for item in summaries
            if item["sample_size"] > 0
        ]

        if not populated:
            return []

        discoveries = []
        forecast = self._best_regime_evidence("Forecast", populated)
        if forecast is not None:
            discoveries.append(
                self._record(
                    title="Forecast regime performance",
                    description=(
                        f"Forecast performs best during "
                        f"{forecast['regime']} markets."
                    ),
                    supporting_data=forecast,
                    sample_size=forecast["sample_size"],
                    importance=70,
                    date=date,
                    related_engines=[
                        "MarketRegimeEngine",
                        "ForecastEngine",
                        "PerformanceObservatory",
                    ],
                    suggestions=[
                        "Compare forecast performance across regimes before changing forecast usage."
                    ],
                )
            )

        news = self._best_regime_evidence("News", populated)
        if news is not None:
            discoveries.append(
                self._record(
                    title="News regime contribution",
                    description=(
                        f"News contributes most during "
                        f"{news['regime']} regimes."
                    ),
                    supporting_data=news,
                    sample_size=news["sample_size"],
                    importance=70,
                    date=date,
                    related_engines=[
                        "MarketRegimeEngine",
                        "NewsEngine",
                        "PerformanceObservatory",
                    ],
                    suggestions=[
                        "Compare news contribution by regime before changing evidence weights."
                    ],
                )
            )

        committee = max(
            populated,
            key=lambda item: (
                item["average_committee_agreement"],
                item["sample_size"],
                item["regime"],
            ),
        )
        discoveries.append(
            self._record(
                title="Committee agreement by regime",
                description=(
                    "Committee agreement is strongest during "
                    f"{committee['regime']} markets."
                ),
                supporting_data={
                    "regime": committee["regime"],
                    "average_committee_agreement": (
                        committee["average_committee_agreement"]
                    ),
                },
                sample_size=committee["sample_size"],
                importance=65,
                date=date,
                related_engines=[
                    "MarketRegimeEngine",
                    "InvestmentCommitteeEngine",
                    "PerformanceObservatory",
                ],
                suggestions=[
                    "Use regime agreement as research context only; do not auto-change committee thresholds."
                ],
            )
        )

        return discoveries

    def _best_regime_evidence(self, category, regime_summaries):
        candidates = []

        for summary in regime_summaries:
            evidence = next(
                (
                    item for item in summary["evidence_rankings"]
                    if item["category"] == category
                    and item["sample_size"] > 0
                ),
                None,
            )
            if evidence is None:
                continue

            candidates.append({
                "regime": summary["regime"],
                "sample_size": evidence["sample_size"],
                "contribution_score": evidence["contribution_score"],
                "hit_rate": evidence["hit_rate"],
                "average_return": evidence["average_return"],
            })

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda item: (
                item["contribution_score"],
                item["hit_rate"],
                item["average_return"],
                item["sample_size"],
                item["regime"],
            ),
        )

    def _macro_discoveries(self, source_data, date):
        from engines.macro_engine import MacroEngine

        report = source_data.get("macro_report") or MacroEngine().analyze()
        risk_score = report.get("macro_risk_score", 0)
        if risk_score < 60:
            importance = 45
        elif risk_score < 75:
            importance = 65
        else:
            importance = 75

        return [
            self._record(
                title="Macro regime context",
                description=report.get("summary", "Macro summary unavailable."),
                supporting_data={
                    "current_macro_regime": report.get("current_macro_regime"),
                    "inflation_pressure": report.get("inflation_pressure"),
                    "rate_pressure": report.get("rate_pressure"),
                    "growth_pressure": report.get("growth_pressure"),
                    "recession_risk": report.get("recession_risk"),
                    "macro_risk_score": risk_score,
                },
                sample_size=len(report.get("indicators", [])),
                importance=importance,
                date=date,
                related_engines=["MacroEngine", "DiscoveryEngine"],
                suggestions=[
                    "Use macro regime as research context only; do not change recommendations automatically."
                ],
            )
        ]

    def _category_contribution_trend(self, category, recommendations):
        from engines.performance_observatory import PerformanceObservatory

        dated = [
            recommendation for recommendation in recommendations
            if recommendation.get("validation_result") is not None
        ]
        dated = sorted(
            dated,
            key=lambda item: (
                item.get("date")
                or item.get("created_at")
                or item.get("timestamp")
                or item.get("ticker", "")
            ),
        )

        if len(dated) < 4:
            return None

        midpoint = len(dated) // 2
        observatory = PerformanceObservatory()
        early = observatory.evidence_contribution_report(
            dated[:midpoint]
        )["categories"]
        recent = observatory.evidence_contribution_report(
            dated[midpoint:]
        )["categories"]
        early_category = next(
            item for item in early if item["category"] == category
        )
        recent_category = next(
            item for item in recent if item["category"] == category
        )

        if early_category["sample_size"] == 0 or recent_category["sample_size"] == 0:
            return None

        return {
            "category": category,
            "early_contribution_score": early_category["contribution_score"],
            "recent_contribution_score": recent_category["contribution_score"],
            "change": round(
                recent_category["contribution_score"]
                - early_category["contribution_score"],
                2,
            ),
            "sample_size": (
                early_category["sample_size"]
                + recent_category["sample_size"]
            ),
        }

    def _committee_agreement_discoveries(self, source_data, date):
        buckets = {
            "Low agreement": [],
            "Medium agreement": [],
            "High agreement": [],
        }

        disagreements = []

        for recommendation in source_data.get("recommendations", []):
            agreement = recommendation.get("committee_agreement", 0)
            validation = recommendation.get("validation_result")

            if agreement >= 75:
                buckets["High agreement"].append(validation)
            elif agreement >= 50:
                buckets["Medium agreement"].append(validation)
            else:
                buckets["Low agreement"].append(validation)

            if recommendation.get("main_disagreement"):
                disagreements.append(recommendation)

        best_bucket = max(
            buckets.items(),
            key=lambda item: self._success_rate(item[1]),
        )
        worst_disagreements = [
            item for item in disagreements
            if self._is_failed(item.get("validation_result"))
        ]

        return [
            self._record(
                title="Best committee agreement range",
                description=(
                    f"{best_bucket[0]} has the best observed validation "
                    f"success rate at {self._success_rate(best_bucket[1])}%."
                ),
                supporting_data={
                    "agreement_range": best_bucket[0],
                    "success_rate": self._success_rate(best_bucket[1]),
                },
                sample_size=len(best_bucket[1]),
                importance=70,
                date=date,
                related_engines=["InvestmentCommitteeEngine"],
                suggestions=[
                    "Compare committee agreement ranges before changing any thresholds."
                ],
            ),
            self._record(
                title="Worst committee disagreements",
                description=(
                    f"{len(worst_disagreements)} recommendations with "
                    "committee disagreement failed validation."
                ),
                supporting_data={
                    "failed_disagreements": [
                        item.get("ticker") for item in worst_disagreements
                    ],
                },
                sample_size=len(disagreements),
                importance=65 if worst_disagreements else 35,
                date=date,
                related_engines=["InvestmentCommitteeEngine", "ValidationEngine"],
                suggestions=[
                    "Investigate disagreement patterns before changing committee interpretation."
                ],
            ),
        ]

    def _provider_performance_discoveries(self, source_data, date):
        providers = source_data.get("provider_results", [])

        if not providers:
            return []

        best = max(providers, key=lambda item: item.get("score", 0))

        return [
            self._record(
                title="Provider performance leader",
                description=(
                    f"{best.get('provider_name')} leads provider research "
                    f"for {best.get('provider_type')} with score "
                    f"{best.get('score', 0)}."
                ),
                supporting_data=best,
                sample_size=len(providers),
                importance=65,
                date=date,
                related_engines=["ResearchEngine"],
                related_providers=[best.get("provider_name")],
                suggestions=[
                    f"Run a larger benchmark before promoting {best.get('provider_name')}."
                ],
            )
        ]

    def _model_evaluation_discoveries(self, source_data, date):
        from engines.model_evaluation_lab import ModelEvaluationLab

        evaluations = source_data.get("model_evaluations", [])

        if not evaluations:
            return []

        rankings = ModelEvaluationLab().rank_models(evaluations)
        best = rankings["best_overall"]
        not_recommended = rankings["not_recommended"]

        return [
            self._record(
                title="Model evaluation leader",
                description=(
                    f"{best} is the best overall model evaluation candidate."
                ),
                supporting_data={
                    "rankings": rankings,
                    "evaluation_count": len(evaluations),
                },
                sample_size=len(evaluations),
                importance=75,
                date=date,
                related_engines=["ModelEvaluationLab", "ResearchEngine"],
                suggestions=[
                    "Treat model rankings as adoption suggestions only; human approval is required."
                ],
            ),
            self._record(
                title="Models not recommended",
                description=(
                    f"{len(not_recommended)} model candidates are not recommended."
                ),
                supporting_data={
                    "not_recommended": not_recommended,
                },
                sample_size=len(not_recommended),
                importance=60 if not_recommended else 25,
                date=date,
                related_engines=["ModelEvaluationLab"],
                warnings=[
                    "Do not install or activate not-recommended models from evaluation output."
                ],
                suggestions=[
                    "Benchmark future placeholders before integration."
                ],
            ),
        ]

    def _scientific_validation_discoveries(self, source_data, date):
        validations = source_data.get("scientific_validations", [])

        if not validations:
            return []

        adoptable = [
            item for item in validations
            if item.get("adoption_decision") == "ADOPT"
        ]
        rejected = [
            item for item in validations
            if item.get("adoption_decision") == "REJECT"
        ]
        retest = [
            item for item in validations
            if item.get("adoption_decision") == "RETEST"
        ]

        return [
            self._record(
                title="Scientifically validated adoption candidates",
                description=(
                    f"{len(adoptable)} proposed improvements passed "
                    "scientific validation for adoption review."
                ),
                supporting_data={
                    "adoptable_features": [
                        item.get("feature_tested") for item in adoptable
                    ],
                    "retest_count": len(retest),
                    "reject_count": len(rejected),
                },
                sample_size=len(validations),
                importance=80 if adoptable else 50,
                date=date,
                related_engines=[
                    "ScientificValidationEngine",
                    "ResearchEngine",
                    "PerformanceObservatory",
                ],
                suggestions=[
                    "Use ADOPT as a research approval signal only; code changes still require human approval and tests."
                ],
            )
        ]

    def _simulation_arena_discoveries(self, source_data, date):
        runs = source_data.get("simulation_arena_runs", [])

        if not runs:
            return []

        latest = runs[0]
        comparison = latest.get("comparison", {})

        return [
            self._record(
                title="Simulation Arena strategy leader",
                description=(
                    f"{comparison.get('best_overall', 'Unavailable')} is the "
                    "best overall strategy in the latest arena run."
                ),
                supporting_data={
                    "arena_id": latest.get("arena_id"),
                    "best_overall": comparison.get("best_overall"),
                    "best_risk_adjusted": comparison.get("best_risk_adjusted"),
                    "not_recommended": comparison.get("not_recommended", []),
                },
                sample_size=len(latest.get("results", [])),
                importance=75,
                date=date,
                related_engines=[
                    "SimulationArena",
                    "HistoricalRunner",
                    "ScientificValidationEngine",
                ],
                suggestions=[
                    "Use arena rankings as research evidence only; do not auto-change Atlas behavior."
                ],
            )
        ]

    def _case_study_discoveries(self, source_data, date):
        from engines.performance_observatory import PerformanceObservatory

        case_studies = source_data.get("case_studies", [])
        if not case_studies:
            return []

        summary = PerformanceObservatory().case_study_summary(case_studies)
        best = summary.get("best_case")
        worst = summary.get("worst_case")
        educational = summary.get("most_educational_case")

        return [
            self._record(
                title="Best validated case study",
                description=(
                    f"{best['ticker']} is the strongest validated case study "
                    f"with {best['return']}% return."
                ),
                supporting_data=best,
                sample_size=len(case_studies),
                importance=75,
                date=date,
                related_engines=["CaseStudyEngine", "PerformanceObservatory"],
                suggestions=[
                    "Use best cases as research analogs only; do not auto-change recommendations."
                ],
            ),
            self._record(
                title="Worst validated case study",
                description=(
                    f"{worst['ticker']} is the weakest validated case study "
                    f"with {worst['return']}% return."
                ),
                supporting_data=worst,
                sample_size=len(case_studies),
                importance=70,
                date=date,
                related_engines=["CaseStudyEngine", "PerformanceObservatory"],
                suggestions=[
                    "Review losing case lessons before repeating similar setups."
                ],
            ),
            self._record(
                title="Most educational case study",
                description=(
                    f"{educational['ticker']} has the richest lessons learned."
                ),
                supporting_data=educational,
                sample_size=len(case_studies),
                importance=65,
                date=date,
                related_engines=["CaseStudyEngine", "ResearchEngine"],
                suggestions=[
                    "Use educational cases to design future controlled experiments."
                ],
            ),
        ]

    def _portfolio_strategy_discoveries(self, source_data, date):
        from engines.performance_observatory import PerformanceObservatory

        strategies = source_data.get("portfolio_strategies", [])
        if not strategies:
            return []

        summary = PerformanceObservatory().portfolio_strategy_summary(strategies)

        return [
            self._record(
                title="Portfolio strategy replay",
                description=(
                    "Atlas portfolio strategies outperformed baseline in "
                    f"{summary['atlas_outperformance_rate']}% of reviews."
                ),
                supporting_data=summary,
                sample_size=summary["review_count"],
                importance=70,
                date=date,
                related_engines=[
                    "PortfolioStrategyEngine",
                    "PerformanceObservatory",
                ],
                suggestions=[
                    "Use portfolio strategy results as research only; human approval is required."
                ],
            )
        ]

    def _portfolio_construction_discoveries(self, source_data, date):
        from engines.performance_observatory import PerformanceObservatory

        reports = source_data.get("portfolio_construction_reports", [])
        if not reports:
            return []

        summary = PerformanceObservatory().portfolio_construction_summary(reports)

        return [
            self._record(
                title="Portfolio construction candidate",
                description=(
                    "Latest construction report shows "
                    f"{summary['portfolio_health']} portfolio health with "
                    f"{summary['risk_budget']} risk budget."
                ),
                supporting_data=summary,
                sample_size=len(reports),
                importance=72,
                date=date,
                related_engines=[
                    "PortfolioConstructionEngine",
                    "PerformanceObservatory",
                ],
                suggestions=[
                    "Evaluate construction candidate through Simulation Arena and Scientific Validation."
                ],
            )
        ]

    def _catalyst_discoveries(self, source_data, date):
        from engines.performance_observatory import PerformanceObservatory

        summary = PerformanceObservatory().catalyst_summary(
            source_data.get("recommendations", []),
            source_data.get("catalysts", []),
        )
        rankings = [
            item for item in summary["rankings"]
            if item["sample_size"] > 0
        ]
        events = source_data.get("catalysts", [])
        discoveries = []

        if len(rankings) >= 2:
            best = rankings[0]
            worst = rankings[-1]
            discoveries.append(
                self._record(
                    title="Catalyst performance spread",
                    description=(
                        f"{best['catalyst']} outperform "
                        f"{worst['catalyst']}."
                    ),
                    supporting_data=summary,
                    sample_size=best["sample_size"] + worst["sample_size"],
                    importance=70,
                    date=date,
                    related_engines=[
                        "CatalystEngine",
                        "PerformanceObservatory",
                    ],
                    suggestions=[
                        "Use catalyst performance as research context only; do not change recommendation behavior."
                    ],
                )
            )

        event_types = {
            event.get("event_type")
            for event in events
        }
        if "CPI" in event_types:
            discoveries.append(
                self._record(
                    title="CPI catalyst volatility",
                    description="CPI weeks increase volatility.",
                    supporting_data={"event_type": "CPI"},
                    sample_size=len([
                        event for event in events
                        if event.get("event_type") == "CPI"
                    ]),
                    importance=65,
                    date=date,
                    related_engines=["CatalystEngine"],
                    suggestions=[
                        "Study macro weeks separately before changing risk interpretation."
                    ],
                )
            )

        if "FOMC" in event_types:
            discoveries.append(
                self._record(
                    title="FOMC catalyst stability",
                    description="FOMC weeks reduce recommendation stability.",
                    supporting_data={"event_type": "FOMC"},
                    sample_size=len([
                        event for event in events
                        if event.get("event_type") == "FOMC"
                    ]),
                    importance=65,
                    date=date,
                    related_engines=["CatalystEngine"],
                    suggestions=[
                        "Track FOMC-week stability without automatically changing actions."
                    ],
                )
            )

        return discoveries

    def _forecast_performance_discoveries(self, source_data, date):
        forecast_benchmarks = [
            item for item in source_data.get("benchmark_results", [])
            if "forecast" in item.get("engine_name", "").lower()
            or "forecast" in item.get("metric", "").lower()
        ]

        if not forecast_benchmarks:
            return []

        average = self._average([
            item.get("value", 0) for item in forecast_benchmarks
        ])
        suggestion = "Forecast contributes little under current configuration."

        if average >= 60:
            suggestion = "Investigate increasing forecast research coverage."

        return [
            self._record(
                title="Forecast model performance",
                description=(
                    f"Forecast benchmark average is {average} across "
                    f"{len(forecast_benchmarks)} benchmark rows."
                ),
                supporting_data={"average_forecast_benchmark": average},
                sample_size=len(forecast_benchmarks),
                importance=60,
                date=date,
                related_engines=["ForecastEngine", "BenchmarkEngine"],
                suggestions=[suggestion],
            )
        ]

    def _probability_discoveries(self, source_data, date):
        from engines.performance_observatory import PerformanceObservatory

        recommendations = source_data.get("recommendations", [])
        summary = PerformanceObservatory().probability_summary(recommendations)
        high_probability = [
            item for item in recommendations
            if item.get("probability_report", {}).get(
                "probabilities",
                {},
            ).get("outperformance", 0) >= 70
            and isinstance(item.get("validation_result"), dict)
        ]
        high_uncertainty = [
            item for item in recommendations
            if item.get("probability_report", {}).get(
                "confidence_quality",
                {},
            ).get("uncertainty_level") in {"High", "Very High"}
            and isinstance(item.get("validation_result"), dict)
        ]
        high_knowledge = [
            item for item in recommendations
            if item.get("knowledge_score", 0) >= 90
            and isinstance(item.get("validation_result"), dict)
        ]
        discoveries = []

        if high_probability:
            rate = self._success_rate([
                item.get("validation_result")
                for item in high_probability
            ])
            discoveries.append(
                self._record(
                    title="High probability outcome accuracy",
                    description=(
                        "High-probability recommendations outperform "
                        f"{rate}% of the time."
                    ),
                    supporting_data={
                        "success_rate": rate,
                        "probability_summary": summary,
                    },
                    sample_size=len(high_probability),
                    importance=75,
                    date=date,
                    related_engines=["ProbabilityEngine", "ValidationEngine"],
                    suggestions=[
                        "Use probability accuracy as calibration research only; do not change actions."
                    ],
                )
            )

        if high_uncertainty:
            average_return = self._average([
                item.get("validation_result", {}).get("percentage_return", 0)
                for item in high_uncertainty
            ])
            outcome = (
                "underperform"
                if average_return < 0
                else "need more validation"
            )
            discoveries.append(
                self._record(
                    title="High uncertainty outcomes",
                    description=(
                        f"Recommendations with High uncertainty {outcome}."
                    ),
                    supporting_data={
                        "average_return": average_return,
                        "uncertainty_distribution": (
                            summary["uncertainty_distribution"]
                        ),
                    },
                    sample_size=len(high_uncertainty),
                    importance=70 if average_return < 0 else 45,
                    date=date,
                    related_engines=["ProbabilityEngine"],
                    suggestions=[
                        "Treat high uncertainty as a research warning, not an automatic override."
                    ],
                )
            )

        if high_knowledge:
            calibration = PerformanceObservatory().probability_summary(
                high_knowledge,
            )["probability_calibration"]
            discoveries.append(
                self._record(
                    title="Knowledge score calibration",
                    description=(
                        "Knowledge scores above 90 improve probability "
                        f"calibration to {calibration}%."
                    ),
                    supporting_data={"probability_calibration": calibration},
                    sample_size=len(high_knowledge),
                    importance=65,
                    date=date,
                    related_engines=[
                        "ProbabilityEngine",
                        "KnowledgeGraphEngine",
                    ],
                    suggestions=[
                        "Validate high-knowledge calibration on larger samples."
                    ],
                )
            )

        return discoveries

    def _research_memory_discoveries(self, source_data, date):
        from engines.research_memory_engine import ResearchMemoryEngine

        engine = ResearchMemoryEngine()
        cases = engine.historical_cases(source_data)
        if not cases:
            return []

        high_agreement = [
            case for case in cases
            if case.get("committee_agreement", 0) >= 75
            and "Fundamentals" in case.get("evidence_profile", [])
        ]
        successful_high_agreement = [
            case for case in high_agreement
            if case.get("outcome") == "Win"
        ]
        technology_bull = [
            case for case in cases
            if case.get("sector") == "Technology"
            and case.get("market_regime") == "Bull"
            and "Earnings" in case.get("catalyst_profile", [])
        ]
        graph_summary = engine.graph_relationship_summary(source_data)
        discoveries = []

        if high_agreement:
            rate = self._rate(
                len(successful_high_agreement),
                len(high_agreement),
            )
            discoveries.append(
                self._record(
                    title="Research memory agreement pattern",
                    description=(
                        "High committee agreement and strong fundamentals "
                        "frequently resemble successful historical cases."
                    ),
                    supporting_data={
                        "success_rate": rate,
                        "sample_cases": [
                            case.get("ticker") for case in high_agreement
                        ],
                    },
                    sample_size=len(high_agreement),
                    importance=75 if rate >= 60 else 50,
                    date=date,
                    related_engines=[
                        "ResearchMemoryEngine",
                        "InvestmentCommitteeEngine",
                        "FundamentalEngine",
                    ],
                    suggestions=[
                        "Use this as historical evidence only; do not change recommendation behavior."
                    ],
                )
            )

        if technology_bull:
            discoveries.append(
                self._record(
                    title="Research memory sector regime pattern",
                    description=(
                        "Technology earnings setups are often similar during "
                        "Bull markets."
                    ),
                    supporting_data={
                        "case_count": len(technology_bull),
                        "tickers": [
                            case.get("ticker") for case in technology_bull
                        ],
                    },
                    sample_size=len(technology_bull),
                    importance=65,
                    date=date,
                    related_engines=[
                        "ResearchMemoryEngine",
                        "MarketRegimeEngine",
                        "CatalystEngine",
                    ],
                    suggestions=[
                        "Validate sector-regime analogs in controlled research before changing any workflow."
                    ],
                )
            )

        if graph_summary["recurring_failures"]:
            discoveries.append(
                self._record(
                    title="Research memory recurring failures",
                    description=(
                        "Historical analogs show recurring failure patterns "
                        "that should be reviewed before repeating similar setups."
                    ),
                    supporting_data={
                        "recurring_failures": graph_summary["recurring_failures"],
                        "weakest_analogs": graph_summary["weakest_analogs"],
                    },
                    sample_size=len(cases),
                    importance=70,
                    date=date,
                    related_engines=[
                        "ResearchMemoryEngine",
                        "KnowledgeGraphEngine",
                    ],
                    suggestions=[
                        "Treat recurring failures as review prompts, not automatic overrides."
                    ],
                )
            )

        return discoveries

    def _confidence_calibration_discoveries(self, source_data, date):
        recommendations = source_data.get("recommendations", [])
        high_confidence = [
            item for item in recommendations
            if item.get("confidence", 0) >= 75
        ]
        low_confidence = [
            item for item in recommendations
            if item.get("confidence", 0) < 60
        ]
        high_rate = self._success_rate([
            item.get("validation_result") for item in high_confidence
        ])
        low_rate = self._success_rate([
            item.get("validation_result") for item in low_confidence
        ])
        gap = round(high_rate - low_rate, 2)

        return [
            self._record(
                title="Confidence calibration",
                description=(
                    f"High-confidence recommendations validated at "
                    f"{high_rate}% versus {low_rate}% for low confidence."
                ),
                supporting_data={
                    "high_confidence_success_rate": high_rate,
                    "low_confidence_success_rate": low_rate,
                    "gap": gap,
                },
                sample_size=len(high_confidence) + len(low_confidence),
                importance=75 if gap > 15 else 45,
                date=date,
                related_engines=["ConfidenceEngine", "ValidationEngine"],
                suggestions=[
                    "Review confidence calibration before changing confidence thresholds."
                ],
            )
        ]

    def _validation_success_discoveries(self, source_data, date):
        validations = [
            item.get("validation_result")
            for item in source_data.get("recommendations", [])
            if item.get("validation_result") is not None
        ]
        success_rate = self._success_rate(validations)

        return [
            self._record(
                title="Validation success",
                description=(
                    f"Validated recommendations have a {success_rate}% "
                    "success rate."
                ),
                supporting_data={"success_rate": success_rate},
                sample_size=len(validations),
                importance=80 if success_rate >= 60 else 55,
                date=date,
                related_engines=["ValidationEngine"],
                suggestions=[
                    "Use validation results as research input only; do not auto-change recommendations."
                ],
            )
        ]

    def _benchmark_trend_discoveries(self, source_data, date):
        benchmarks = source_data.get("benchmark_results", [])

        if not benchmarks:
            return []

        average = self._average([item.get("value", 0) for item in benchmarks])

        return [
            self._record(
                title="Benchmark trend",
                description=(
                    f"Recent benchmark average is {average} across "
                    f"{len(benchmarks)} metric rows."
                ),
                supporting_data={"average_benchmark_value": average},
                sample_size=len(benchmarks),
                importance=55,
                date=date,
                related_engines=["BenchmarkEngine"],
                suggestions=[
                    "Track benchmark direction over additional snapshots."
                ],
            )
        ]

    def _sector_trend_placeholder(self, source_data, date):
        recommendations = source_data.get("recommendations", [])
        sector_count = len([
            item for item in recommendations
            if item.get("sector")
        ])

        return self._record(
            title="Sector trend coverage",
            description=(
                "Sector trend discovery requires sector-tagged "
                "recommendation history."
            ),
            supporting_data={"sector_tagged_recommendations": sector_count},
            sample_size=sector_count,
            importance=25,
            date=date,
            related_engines=["DiscoveryEngine"],
            warnings=["Sector data is not yet available in saved recommendations."],
            suggestions=["Add sector metadata before evaluating sector trends."],
        )

    def _record(
        self,
        title,
        description,
        supporting_data,
        sample_size,
        importance,
        date,
        related_engines=None,
        related_providers=None,
        warnings=None,
        suggestions=None,
    ):
        related_engines = related_engines or []
        related_providers = related_providers or []
        warnings = warnings or []
        suggestions = suggestions or []
        support_level = self._support_level(sample_size)

        if support_level == "Tiny sample":
            warnings = warnings + [
                "Tiny sample size; treat as a research lead, not a conclusion."
            ]

        confidence = self._confidence(sample_size, importance)
        discovery_id = self._discovery_id(title, date, supporting_data)

        return {
            "id": discovery_id,
            "title": title,
            "description": description,
            "supporting_data": supporting_data,
            "sample_size": sample_size,
            "confidence": confidence,
            "importance": importance,
            "date": date,
            "related_engines": related_engines,
            "related_providers": related_providers,
            "status": "Observed",
            "support_level": support_level,
            "warnings": warnings,
            "suggestions": suggestions,
            "automatic_behavior_change": False,
        }

    def _discovery_id(self, title, date, supporting_data):
        seed = f"{title}|{date}|{supporting_data}"
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]

        return f"disc-{digest}"

    def _support_level(self, sample_size):
        if sample_size < self.tiny_sample_threshold:
            return "Tiny sample"

        if sample_size < 20:
            return "Moderate sample"

        return "Strong sample"

    def _confidence(self, sample_size, importance):
        sample_score = min(70, sample_size * 5)
        importance_score = min(30, importance * 0.3)

        return round(min(100, sample_score + importance_score), 2)

    def _success_rate(self, validations):
        completed = [
            item for item in validations
            if item is not None and item.get("success") is not None
        ]

        if not completed:
            return 0

        successful = [
            item for item in completed
            if item.get("success") is True or item.get("hit") is True
        ]

        return round(len(successful) / len(completed) * 100, 2)

    def _is_failed(self, validation):
        if validation is None:
            return False

        return validation.get("success") is False or validation.get("hit") is False

    def _average(self, values):
        values = [value for value in values if value is not None]

        if not values:
            return 0

        return round(sum(values) / len(values), 2)

    def _rate(self, numerator, denominator):
        if denominator == 0:
            return 0

        return round(numerator / denominator * 100, 2)
