class PerformanceObservatory:
    MARKET_REGIMES = [
        "Strong Bull",
        "Bull",
        "Sideways",
        "Volatile",
        "Bear",
        "Strong Bear",
    ]
    ENGINE_NAMES = [
        "Technical",
        "Fundamental",
        "Forecast",
        "News",
        "Portfolio",
        "Risk",
        "Evidence",
        "Committee",
    ]
    EVIDENCE_CATEGORIES = [
        "Technical",
        "Fundamentals",
        "Forecast",
        "News",
        "Portfolio",
        "Risk",
        "Committee",
        "Executive Review",
        "Validation",
        "Discovery",
    ]
    EVIDENCE_ALIASES = {
        "Fundamentals": ["Fundamentals", "Fundamental"],
        "Executive Review": ["Executive Review", "Executive"],
    }
    PROVIDER_TYPES = ["forecast", "news", "fundamental", "data", "catalyst"]

    def generate(self, source_data=None, discovery_data=None):
        if source_data is None:
            from database.repository import get_discovery_source_data

            source_data = get_discovery_source_data()

        if discovery_data is None:
            discovery_data = self._discovery_data()

        recommendations = source_data.get("recommendations", [])
        benchmarks = source_data.get("benchmark_results", [])
        providers = source_data.get("provider_results", [])
        experiments = source_data.get("research_experiments", [])
        model_evaluations = source_data.get("model_evaluations", [])
        case_studies = source_data.get("case_studies", [])
        portfolio_strategies = source_data.get("portfolio_strategies", [])
        catalysts = source_data.get("catalysts", [])
        scientific_validations = source_data.get("scientific_validations", [])
        simulation_arena_runs = source_data.get("simulation_arena_runs", [])
        paper_history = source_data.get("paper_portfolio_history", [])
        paper_trades = source_data.get("paper_trades", [])
        paper_performance = source_data.get("paper_performance_reports", [])
        portfolio_construction = source_data.get(
            "portfolio_construction_reports",
            [],
        )

        return {
            "platform_metrics": self.platform_metrics(recommendations),
            "engine_report_cards": self.engine_report_cards(recommendations),
            "provider_report_cards": self.provider_report_cards(providers),
            "provider_health_summary": self.provider_health_summary(),
            "sec_summary": self.sec_summary(),
            "macro_summary": self.macro_summary(),
            "model_evaluation_summary": self.model_evaluation_summary(
                model_evaluations
            ),
            "case_study_summary": self.case_study_summary(case_studies),
            "portfolio_strategy_summary": self.portfolio_strategy_summary(
                portfolio_strategies
            ),
            "portfolio_construction_summary": (
                self.portfolio_construction_summary(portfolio_construction)
            ),
            "catalyst_summary": self.catalyst_summary(
                recommendations,
                catalysts,
            ),
            "probability_summary": self.probability_summary(recommendations),
            "scientific_validation_summary": (
                self.scientific_validation_summary(scientific_validations)
            ),
            "simulation_arena_summary": (
                self.simulation_arena_summary(simulation_arena_runs)
            ),
            "paper_trading_dashboard": self.paper_trading_dashboard(
                paper_history,
                paper_trades,
                paper_performance,
            ),
            "evidence_contribution_report": (
                self.evidence_contribution_report(recommendations)
            ),
            "performance_by_regime": self.performance_by_regime(
                recommendations
            ),
            "benchmark_history": self.benchmark_history(benchmarks),
            "committee_history": self.committee_history(recommendations),
            "discovery_history": self.discovery_history(discovery_data),
            "experiment_summary": self.experiment_summary(experiments),
            "knowledge_graph_summary": self.knowledge_graph_summary(
                source_data,
                discovery_data,
            ),
            "research_memory_summary": self.research_memory_summary(
                source_data,
            ),
            "controlled_learning": {
                "automatic_behavior_changes": False,
                "requires_human_approval": True,
                "policy": (
                    "Performance observations are advisory and do not change "
                    "recommendation logic, providers, thresholds, or weights."
                ),
            },
        }

    def performance_analytics(self, **kwargs):
        """Deterministic performance analytics that measures Atlas itself.

        Delegates to PerformanceAnalyticsEngine (imported lazily to avoid a
        circular import). Read-only; does not change recommendation behavior.
        """
        from engines.performance_analytics_engine import (
            PerformanceAnalyticsEngine,
        )

        return PerformanceAnalyticsEngine(observatory=self).generate(**kwargs)

    def probability_summary(self, recommendations):
        from engines.probability_engine import ProbabilityEngine

        report = ProbabilityEngine().calibration_report(recommendations)
        reports = [
            item.get("probability_report")
            for item in recommendations
            if isinstance(item.get("probability_report"), dict)
        ]

        return report | {
            "report_count": len(reports),
            "average_expected_return": self._average([
                item.get("expected_outcome", {}).get("expected_return")
                for item in reports
            ]),
            "policy": (
                "Probability estimates are measurement only and do not change "
                "recommendation behavior or execute trades."
            ),
        }

    def portfolio_construction_summary(self, reports):
        latest = reports[0] if reports else {}
        operations = latest.get("operations_summary", {})
        diversification = latest.get("diversification", {})

        return {
            "report_count": len(reports),
            "portfolio_health": operations.get("portfolio_health", "Unavailable"),
            "risk_budget": operations.get("risk_budget", "Unavailable"),
            "largest_position": operations.get("largest_position", 0),
            "most_concentrated_sector": operations.get(
                "most_concentrated_sector"
            ),
            "diversification_score": operations.get(
                "diversification_score",
                diversification.get("diversification_score", 0),
            ),
            "suggested_rebalance": operations.get(
                "suggested_rebalance",
                "Maintain",
            ),
            "policy": (
                "Portfolio construction is read-only, paper-only allocation "
                "research and does not execute trades or change recommendations."
            ),
        }

    def scientific_validation_summary(self, validations):
        decisions = self._distribution([
            item.get("adoption_decision", "Unknown")
            for item in validations
        ])
        results = self._distribution([
            item.get("scientific_result", "Unknown")
            for item in validations
        ])
        adoptable = [
            item for item in validations
            if item.get("adoption_decision") == "ADOPT"
        ]

        return {
            "validation_count": len(validations),
            "decision_distribution": decisions,
            "result_distribution": results,
            "adoptable_feature_count": len(adoptable),
            "latest_reports": validations[:5],
            "policy": (
                "Scientific validation measures adoption evidence only. It "
                "does not change BUY/HOLD/AVOID logic, providers, thresholds, "
                "weights, broker connections, or execution."
            ),
        }

    def simulation_arena_summary(self, runs):
        latest = runs[0] if runs else {}
        comparison = latest.get("comparison", {})

        return {
            "arena_run_count": len(runs),
            "latest_arena_id": latest.get("arena_id"),
            "latest_best_overall": comparison.get("best_overall"),
            "latest_best_risk_adjusted": comparison.get("best_risk_adjusted"),
            "latest_not_recommended": comparison.get("not_recommended", []),
            "latest_strategy_count": len(latest.get("results", [])),
            "policy": (
                "Simulation Arena output is research-only and does not change "
                "recommendation behavior, providers, thresholds, brokers, or "
                "execution."
            ),
        }

    def paper_trading_dashboard(self, history, trades, performance_reports):
        latest = history[0] if history else {}
        latest_performance = (
            performance_reports[0].get("performance", {})
            if performance_reports
            else {}
        )

        return {
            "latest_portfolio": latest,
            "portfolio_history": history[:30],
            "rolling_performance": {
                "latest_total_return": latest.get("total_return", 0),
                "latest_daily_return": latest.get("daily_return", 0),
                "latest_sharpe": latest_performance.get("sharpe", 0),
                "latest_sortino": latest_performance.get("sortino", 0),
                "latest_max_drawdown": latest_performance.get(
                    "max_drawdown",
                    0,
                ),
            },
            "trade_count": len(trades),
            "paper_validation_source": bool(performance_reports),
            "policy": (
                "Paper trading is simulated research only: no real money, no "
                "broker connection, no order execution, and no recommendation "
                "behavior changes."
            ),
        }

    def provider_health_summary(self):
        from market.provider_registry import ProviderRegistry

        registry = ProviderRegistry()

        return registry.health()["summary"] | {
            "active_providers": registry.active_providers(),
            "experimental_providers": registry.summary()["experimental_providers"],
            "policy": (
                "Provider health is read-only. Mock providers remain the "
                "offline default and no provider changes recommendation behavior."
            ),
        }

    def sec_summary(self):
        from engines.sec_engine import SecEngine

        return SecEngine().observatory_summary()

    def macro_summary(self):
        from engines.macro_engine import MacroEngine

        return MacroEngine().observatory_summary()

    def research_memory_summary(self, source_data):
        from engines.research_memory_engine import ResearchMemoryEngine

        engine = ResearchMemoryEngine()
        cases = engine.historical_cases(source_data)
        reports = []

        for recommendation in source_data.get("recommendations", []):
            report = engine.build(
                recommendation,
                source_data=source_data,
                limit=5,
            )
            if report["similar_historical_cases"]:
                reports.append(report)

        analogs = [
            analog
            for report in reports
            for analog in report["similar_historical_cases"]
        ]

        return {
            "case_count": len(cases),
            "report_count": len(reports),
            "research_memory_retrieval_accuracy": engine.observability(
                analogs,
                cases,
            )["research_memory_retrieval_accuracy"],
            "analog_success_rate": engine.observability(
                analogs,
                cases,
            )["analog_success_rate"],
            "similarity_score_calibration": engine.observability(
                analogs,
                cases,
            )["similarity_score_calibration"],
            "pattern_frequency": engine.pattern_frequency(cases),
            "policy": (
                "Research memory is advisory evidence only and does not "
                "change recommendation actions, thresholds, providers, or trades."
            ),
        }

    def catalyst_summary(self, recommendations, catalysts=None):
        groups = {}
        catalysts = catalysts or []

        for recommendation in recommendations:
            validation = recommendation.get("validation_result")
            if not isinstance(validation, dict):
                continue

            for catalyst in recommendation.get("catalysts", []):
                event_type = catalyst.get("event_type")
                if not event_type:
                    continue

                groups.setdefault(event_type, []).append({
                    "success": (
                        validation.get("success") is True
                        or validation.get("hit") is True
                    ),
                    "return": validation.get("percentage_return"),
                })

        if not groups:
            for catalyst in catalysts:
                event_type = catalyst.get("event_type")
                if event_type:
                    groups.setdefault(event_type, [])

        ranked = []
        for event_type, rows in groups.items():
            returns = [
                item["return"] for item in rows
                if item.get("return") is not None
            ]
            ranked.append({
                "catalyst": event_type,
                "sample_size": len(rows),
                "win_rate": self._rate(
                    len([item for item in rows if item.get("success")]),
                    len(rows),
                ),
                "average_return": self._average(returns),
            })

        ranked = sorted(
            ranked,
            key=lambda item: (
                item["average_return"],
                item["win_rate"],
                item["sample_size"],
                item["catalyst"],
            ),
            reverse=True,
        )
        most_common = sorted(
            ranked,
            key=lambda item: (-item["sample_size"], item["catalyst"]),
        )

        return {
            "most_common_catalyst": (
                most_common[0]["catalyst"] if most_common else None
            ),
            "best_performing_catalyst": (
                ranked[0]["catalyst"] if ranked else None
            ),
            "worst_performing_catalyst": (
                ranked[-1]["catalyst"] if ranked else None
            ),
            "rankings": ranked,
            "policy": (
                "Catalyst performance is measurement only and does not change "
                "recommendation actions or trigger trades."
            ),
        }

    def portfolio_strategy_summary(self, portfolio_strategies):
        if not portfolio_strategies:
            return {
                "review_count": 0,
                "atlas_outperformance_rate": 0,
                "average_return_improvement": 0,
                "requires_human_approval": True,
            }

        outperformed = [
            item for item in portfolio_strategies
            if item.get("historical_replay", {}).get("atlas_outperformed")
        ]

        return {
            "review_count": len(portfolio_strategies),
            "atlas_outperformance_rate": self._rate(
                len(outperformed),
                len(portfolio_strategies),
            ),
            "average_return_improvement": self._average([
                item.get("historical_replay", {}).get("difference", 0)
                for item in portfolio_strategies
            ]),
            "requires_human_approval": True,
        }

    def case_study_summary(self, case_studies):
        if not case_studies:
            return {
                "case_count": 0,
                "best_case": None,
                "worst_case": None,
                "most_educational_case": None,
                "most_similar_cases": [],
            }

        ordered = sorted(
            case_studies,
            key=lambda item: (
                item.get("return", 0),
                item.get("knowledge_score", 0),
                item.get("stability_score", 0),
                item.get("ticker", ""),
            ),
            reverse=True,
        )
        educational = sorted(
            case_studies,
            key=lambda item: (
                len(item.get("lessons_learned", {}).get("future_improvements", [])),
                abs(item.get("return", 0)),
                item.get("ticker", ""),
            ),
            reverse=True,
        )

        return {
            "case_count": len(case_studies),
            "best_case": ordered[0],
            "worst_case": ordered[-1],
            "most_educational_case": educational[0],
            "most_similar_cases": self._most_similar_cases(case_studies),
        }

    def _most_similar_cases(self, case_studies):
        if len(case_studies) < 2:
            return []

        pairs = []
        for index, case in enumerate(case_studies):
            for other in case_studies[index + 1:]:
                score = 0
                if case.get("ticker") == other.get("ticker"):
                    score += 3
                if case.get("market_regime") == other.get("market_regime"):
                    score += 2
                if case.get("outcome") == other.get("outcome"):
                    score += 1

                pairs.append({
                    "case_ids": [case.get("case_id"), other.get("case_id")],
                    "tickers": [case.get("ticker"), other.get("ticker")],
                    "similarity_score": score,
                })

        return sorted(
            pairs,
            key=lambda item: (-item["similarity_score"], item["case_ids"]),
        )[:5]

    def model_evaluation_summary(self, evaluations):
        from engines.model_evaluation_lab import ModelEvaluationLab

        lab = ModelEvaluationLab()
        rankings = lab.rank_models(evaluations) if evaluations else {
            "best_overall": None,
            "best_accuracy": None,
            "best_risk_adjusted": None,
            "best_low_cost": None,
            "best_speed": None,
            "not_recommended": [],
            "ordered": [],
        }

        return {
            "evaluation_count": len(evaluations),
            "rankings": rankings,
            "controlled_learning": lab.controlled_learning(),
        }

    def performance_by_regime(self, recommendations):
        return [
            self._regime_summary(regime, recommendations)
            for regime in self.MARKET_REGIMES
        ]

    def _regime_summary(self, regime, recommendations):
        rows = [
            item for item in recommendations
            if item.get("market_regime", "Sideways") == regime
        ]
        validations = [
            item.get("validation_result")
            for item in rows
            if isinstance(item.get("validation_result"), dict)
        ]
        completed = [
            item for item in validations
            if item.get("success") is not None or item.get("hit") is not None
        ]
        returns = [
            item.get("percentage_return")
            for item in completed
            if item.get("percentage_return") is not None
        ]
        wins = [
            item for item in completed
            if item.get("success") is True or item.get("hit") is True
        ]

        return {
            "regime": regime,
            "sample_size": len(completed),
            "win_rate": self._rate(len(wins), len(completed)),
            "average_return": self._average(returns),
            "recommendation_distribution": self._distribution([
                item.get("action", "UNKNOWN") for item in rows
            ]),
            "average_committee_agreement": self._average([
                item.get("committee_agreement", 0) for item in rows
            ]),
            "average_knowledge_score": self._average([
                item.get("knowledge_score", 0) for item in rows
            ]),
            "average_stability_score": self._average([
                item.get("stability_score", 0) for item in rows
            ]),
            "evidence_rankings": (
                self.evidence_contribution_report(rows)["evidence_rankings"]
                if rows
                else []
            ),
        }

    def evidence_contribution_report(self, recommendations):
        categories = [
            self._evidence_contribution(category, recommendations)
            for category in self.EVIDENCE_CATEGORIES
        ]
        rankings = sorted(
            categories,
            key=lambda item: (
                item["contribution_score"],
                item["confidence"],
                item["sample_size"],
                item["average_return"],
                item["category"],
            ),
            reverse=True,
        )
        strongest = rankings[0] if rankings else None
        weakest = rankings[-1] if rankings else None

        return {
            "categories": categories,
            "strongest_evidence_category": (
                strongest["category"] if strongest else "Unavailable"
            ),
            "weakest_evidence_category": (
                weakest["category"] if weakest else "Unavailable"
            ),
            "evidence_rankings": rankings,
            "automatic_behavior_changes": False,
            "policy": (
                "Historical contribution estimates are measurement only and "
                "do not change recommendation actions, thresholds, or weights."
            ),
        }

    def _evidence_contribution(self, category, recommendations):
        rows = []

        for recommendation in recommendations:
            validation = recommendation.get("validation_result")
            if not isinstance(validation, dict):
                continue

            if validation.get("success") is None and validation.get("hit") is None:
                continue

            score = self._category_score(category, recommendation)
            if score is None:
                continue

            if score < 60:
                continue

            rows.append({
                "score": score,
                "confidence": self._category_confidence(
                    category,
                    recommendation,
                    score,
                ),
                "success": (
                    validation.get("success") is True
                    or validation.get("hit") is True
                ),
                "return": validation.get("percentage_return"),
            })

        returns = [
            item["return"] for item in rows
            if item["return"] is not None
        ]
        hit_rate = self._rate(
            len([item for item in rows if item["success"]]),
            len(rows),
        )
        average_return = self._average(returns)
        confidence = self._contribution_confidence(
            len(rows),
            self._average([item["confidence"] for item in rows]),
        )
        contribution_score = self._contribution_score(
            hit_rate,
            average_return,
            confidence,
        )

        return {
            "category": category,
            "sample_size": len(rows),
            "average_return": average_return,
            "hit_rate": hit_rate,
            "contribution_score": contribution_score,
            "confidence": confidence,
            "strengths": self._contribution_strengths(
                category,
                hit_rate,
                average_return,
                contribution_score,
                len(rows),
            ),
            "weaknesses": self._contribution_weaknesses(
                category,
                hit_rate,
                average_return,
                contribution_score,
                len(rows),
            ),
        }

    def _category_score(self, category, recommendation):
        evidence = self._find_evidence(
            recommendation.get("evidence_breakdown", []),
            category,
        )
        if evidence is not None:
            return evidence.get("score", 0)

        if category == "Committee":
            return recommendation.get("committee_agreement")

        if category == "Executive Review":
            return recommendation.get(
                "executive_confidence",
                self._executive_status_score(
                    recommendation.get("executive_status")
                ),
            )

        if category == "Discovery":
            return recommendation.get("discovery_score")

        return None

    def _category_confidence(self, category, recommendation, score):
        evidence = self._find_evidence(
            recommendation.get("evidence_breakdown", []),
            category,
        )
        if evidence is not None:
            return evidence.get("confidence", score)

        if category == "Executive Review":
            return recommendation.get("executive_confidence", score)

        return score

    def _executive_status_score(self, status):
        if status == "READY":
            return 85

        if status == "CAUTION":
            return 65

        if status == "NEEDS_REVIEW":
            return 40

        if status == "INSUFFICIENT_DATA":
            return 25

        return None

    def _contribution_confidence(self, sample_size, average_confidence):
        sample_component = min(60, sample_size * 10)
        evidence_component = min(40, average_confidence * 0.4)

        return round(min(100, sample_component + evidence_component), 2)

    def _contribution_score(self, hit_rate, average_return, confidence):
        return_component = max(0, min(100, 50 + average_return * 5))
        score = (
            hit_rate * 0.55
            + return_component * 0.30
            + confidence * 0.15
        )

        return round(max(0, min(100, score)), 2)

    def _contribution_strengths(
        self,
        category,
        hit_rate,
        average_return,
        contribution_score,
        sample_size,
    ):
        strengths = []

        if hit_rate >= 60:
            strengths.append(f"{category} has a positive historical hit rate.")

        if average_return > 0:
            strengths.append(f"{category} has positive average return.")

        if contribution_score >= 70:
            strengths.append(f"{category} ranks as a high-contribution signal.")

        if sample_size >= 10:
            strengths.append(f"{category} has a useful sample size.")

        return strengths or [f"{category} has measurable supportive history."]

    def _contribution_weaknesses(
        self,
        category,
        hit_rate,
        average_return,
        contribution_score,
        sample_size,
    ):
        weaknesses = []

        if sample_size < 5:
            weaknesses.append("Sample size is small.")

        if hit_rate < 50:
            weaknesses.append(f"{category} hit rate is below 50%.")

        if average_return < 0:
            weaknesses.append(f"{category} has negative average return.")

        if contribution_score < 50:
            weaknesses.append(f"{category} contribution score is below 50.")

        return weaknesses or ["No major weakness identified."]

    def knowledge_graph_summary(self, source_data, discovery_data):
        from engines.knowledge_graph_engine import KnowledgeGraphEngine

        graph = KnowledgeGraphEngine().build(
            source_data=source_data,
            discovery_data=discovery_data,
            historical_runs=[],
        )

        return {
            "node_count": len(graph["nodes"]),
            "relationship_count": len(graph["relationships"]),
            "committee_history_count": len(
                KnowledgeGraphEngine().committee_history(graph)
            ),
            "executive_history_count": len(
                KnowledgeGraphEngine().executive_history(graph)
            ),
        }

    def platform_metrics(self, recommendations):
        validations = [
            item.get("validation_result")
            for item in recommendations
            if item.get("validation_result") is not None
        ]
        validated = [
            item for item in validations
            if item.get("success") is not None
        ]
        returns = [
            item.get("percentage_return")
            for item in validated
            if item.get("percentage_return") is not None
        ]
        wins = [item for item in validated if item.get("success") is True]
        rolling = validated[-10:]
        confidences = [
            item.get("confidence", 0)
            for item in recommendations
            if item.get("validation_result") is not None
        ]

        return {
            "lifetime_recommendations": len(recommendations),
            "validated_recommendations": len(validated),
            "current_win_rate": self._rate(len(wins), len(validated)),
            "rolling_win_rate": self._rate(
                len([item for item in rolling if item.get("success") is True]),
                len(rolling),
            ),
            "average_return": self._average(returns),
            "median_return": self._median(returns),
            "largest_gain": max(returns) if returns else 0,
            "largest_loss": min(returns) if returns else 0,
            "sharpe_placeholder": 0,
            "drawdown_placeholder": 0,
            "confidence_calibration": self._confidence_calibration(
                recommendations,
            ),
            "average_confidence": self._average(confidences),
            "recommendation_distribution": self._distribution(
                [item.get("action", "UNKNOWN") for item in recommendations]
            ),
            "committee_agreement_distribution": (
                self._committee_distribution(recommendations)
            ),
            "executive_approval_rate": self._executive_approval_rate(
                recommendations,
            ),
            "executive_warning_frequency": self._executive_warning_frequency(
                recommendations,
            ),
            "readiness_distribution": self._distribution([
                item.get("executive_status", "UNREVIEWED")
                or "UNREVIEWED"
                for item in recommendations
            ]),
            "historical_executive_accuracy": (
                self._historical_executive_accuracy(recommendations)
            ),
            "average_stability_score": self._average([
                item.get("stability_score", 0) for item in recommendations
            ]),
            "stability_distribution": self._distribution([
                item.get("stability_level", "Unscored") or "Unscored"
                for item in recommendations
            ]),
            "average_knowledge_score": self._average([
                item.get("knowledge_score", 0) for item in recommendations
            ]),
            "knowledge_distribution": self._distribution([
                item.get("knowledge_level", "Unscored") or "Unscored"
                for item in recommendations
            ]),
        }

    def engine_report_cards(self, recommendations):
        return [
            self._engine_report_card(engine_name, recommendations)
            for engine_name in self.ENGINE_NAMES
        ]

    def provider_report_cards(self, providers):
        cards = []

        for provider_type in self.PROVIDER_TYPES:
            rows = [
                item for item in providers
                if item.get("provider_type") == provider_type
            ]
            ranked = sorted(
                rows,
                key=lambda item: (
                    item.get("score") or 0,
                    -1 * (item.get("rank") or 999),
                    item.get("provider_name") or "",
                ),
                reverse=True,
            )

            if not ranked:
                cards.append({
                    "provider_type": provider_type,
                    "provider_name": "Unavailable",
                    "rank": None,
                    "historical_performance": 0,
                    "sample_size": 0,
                    "status": "No history",
                    "strengths": [],
                    "weaknesses": ["No provider performance history."],
                })
                continue

            for index, provider in enumerate(ranked, start=1):
                score = provider.get("score") or 0
                cards.append({
                    "provider_type": provider_type,
                    "provider_name": provider.get("provider_name", ""),
                    "rank": index,
                    "historical_performance": score,
                    "sample_size": len(rows),
                    "status": provider.get("status", ""),
                    "strengths": self._provider_strengths(score, provider),
                    "weaknesses": self._provider_weaknesses(score, provider),
                })

        return cards

    def benchmark_history(self, benchmarks):
        metrics = {}

        for row in benchmarks:
            metric = row.get("metric", "unknown")
            metrics.setdefault(metric, []).append(row.get("value") or 0)

        return {
            "benchmark_count": len(benchmarks),
            "latest_results": benchmarks[:10],
            "metric_averages": {
                metric: self._average(values)
                for metric, values in sorted(metrics.items())
            },
        }

    def committee_history(self, recommendations):
        agreements = [
            item.get("committee_agreement", 0)
            for item in recommendations
            if item.get("committee_agreement") is not None
        ]
        disagreements = [
            item for item in recommendations
            if item.get("main_disagreement")
        ]

        return {
            "sample_size": len(agreements),
            "average_agreement": self._average(agreements),
            "agreement_distribution": self._committee_distribution(
                recommendations,
            ),
            "disagreement_count": len(disagreements),
            "latest_disagreements": [
                {
                    "ticker": item.get("ticker", ""),
                    "main_disagreement": item.get("main_disagreement", ""),
                }
                for item in disagreements[-5:]
            ],
        }

    def discovery_history(self, discovery_data):
        recent = discovery_data.get("recent_discoveries", [])
        top = discovery_data.get("top_discoveries", [])

        return {
            "discovery_count": len(discovery_data.get("discovery_history", [])),
            "recent_discoveries": recent[:5],
            "top_discoveries": top[:5],
        }

    def experiment_summary(self, experiments):
        return {
            "experiment_count": len(experiments),
            "status_distribution": self._distribution([
                item.get("status", "Unknown") for item in experiments
            ]),
            "latest_experiments": experiments[-5:],
        }

    def _engine_report_card(self, engine_name, recommendations):
        if engine_name == "Committee":
            return self._committee_report_card(recommendations)

        if engine_name == "Evidence":
            evidence_rows = [
                evidence for recommendation in recommendations
                for evidence in recommendation.get("evidence_breakdown", [])
                if isinstance(evidence, dict)
            ]
            validated = [
                recommendation for recommendation in recommendations
                if (recommendation.get("validation_result") or {}).get("success")
                is not None
            ]

            return {
                "engine": engine_name,
                "accuracy": self._success_rate(validated),
                "confidence": self._average([
                    item.get("confidence", 0) for item in evidence_rows
                ]),
                "sample_size": len(validated),
                "strengths": self._strengths(
                    "Evidence",
                    self._average([item.get("score", 0) for item in evidence_rows]),
                    self._success_rate(validated),
                ),
                "weaknesses": self._weaknesses(
                    "Evidence",
                    self._average([item.get("score", 0) for item in evidence_rows]),
                    self._success_rate(validated),
                    len(validated),
                ),
            }

        rows = []
        for recommendation in recommendations:
            evidence = self._find_evidence(
                recommendation.get("evidence_breakdown", []),
                engine_name,
            )
            if evidence is None:
                continue

            rows.append({
                "score": evidence.get("score", 0),
                "confidence": evidence.get("confidence", 0),
                "validation": recommendation.get("validation_result"),
            })

        validated = [
            item for item in rows
            if item.get("validation") is not None
            and item["validation"].get("success") is not None
        ]
        accuracy = self._rate(
            len([
                item for item in validated
                if item["validation"].get("success") is True
            ]),
            len(validated),
        )
        average_score = self._average([item["score"] for item in rows])

        return {
            "engine": engine_name,
            "accuracy": accuracy,
            "confidence": self._average([
                item["confidence"] for item in rows
            ]),
            "sample_size": len(validated),
            "strengths": self._strengths(
                engine_name,
                average_score,
                accuracy,
            ),
            "weaknesses": self._weaknesses(
                engine_name,
                average_score,
                accuracy,
                len(validated),
            ),
        }

    def _committee_report_card(self, recommendations):
        validated = [
            item for item in recommendations
            if (item.get("validation_result") or {}).get("success") is not None
        ]
        accuracy = self._success_rate(validated)
        agreement = self._average([
            item.get("committee_agreement", 0) for item in recommendations
        ])

        return {
            "engine": "Committee",
            "accuracy": accuracy,
            "confidence": agreement,
            "sample_size": len(validated),
            "strengths": self._strengths("Committee", agreement, accuracy),
            "weaknesses": self._weaknesses(
                "Committee",
                agreement,
                accuracy,
                len(validated),
            ),
        }

    def _discovery_data(self):
        try:
            from database.repository import get_discovery_dashboard_data

            return get_discovery_dashboard_data()
        except Exception:
            return {
                "recent_discoveries": [],
                "top_discoveries": [],
                "discovery_history": [],
            }

    def _find_evidence(self, evidence_rows, name):
        names = set(self.EVIDENCE_ALIASES.get(name, [name]))

        return next(
            (
                item for item in evidence_rows
                if isinstance(item, dict)
                and (
                    item.get("category") in names
                    or item.get("name") in names
                )
            ),
            None,
        )

    def _success_rate(self, recommendations):
        validated = [
            item for item in recommendations
            if (item.get("validation_result") or {}).get("success") is not None
        ]

        return self._rate(
            len([
                item for item in validated
                if item["validation_result"].get("success") is True
            ]),
            len(validated),
        )

    def _confidence_calibration(self, recommendations):
        rows = [
            item for item in recommendations
            if item.get("validation_result") is not None
            and item["validation_result"].get("success") is not None
        ]

        if not rows:
            return 0

        errors = []
        for item in rows:
            expected = item.get("confidence", 0)
            actual = 100 if item["validation_result"].get("success") else 0
            errors.append(abs(expected - actual))

        return round(max(0, 100 - self._average(errors)), 2)

    def _committee_distribution(self, recommendations):
        buckets = {"low": 0, "medium": 0, "high": 0}

        for item in recommendations:
            agreement = item.get("committee_agreement", 0) or 0
            if agreement >= 75:
                buckets["high"] += 1
            elif agreement >= 50:
                buckets["medium"] += 1
            else:
                buckets["low"] += 1

        return buckets

    def _executive_approval_rate(self, recommendations):
        reviewed = [
            item for item in recommendations
            if item.get("executive_status")
        ]
        ready = [
            item for item in reviewed
            if item.get("executive_status") == "READY"
        ]

        return self._rate(len(ready), len(reviewed))

    def _executive_warning_frequency(self, recommendations):
        reviewed = [
            item for item in recommendations
            if item.get("executive_status")
        ]
        warning_count = sum(
            len(item.get("executive_warnings", []) or [])
            for item in reviewed
        )

        if not reviewed:
            return 0

        return round(warning_count / len(reviewed), 2)

    def _historical_executive_accuracy(self, recommendations):
        validated = [
            item for item in recommendations
            if item.get("executive_status")
            and (item.get("validation_result") or {}).get("success")
            is not None
        ]

        aligned = []
        for item in validated:
            status = item.get("executive_status")
            success = item["validation_result"].get("success")
            aligned.append(
                (status in {"READY", "CAUTION"} and success is True)
                or (status in {"NEEDS_REVIEW", "INSUFFICIENT_DATA"}
                    and success is False)
            )

        return self._rate(len([item for item in aligned if item]), len(aligned))

    def _distribution(self, values):
        counts = {}

        for value in values:
            counts[value] = counts.get(value, 0) + 1

        return counts

    def _strengths(self, name, score, accuracy):
        strengths = []

        if accuracy >= 60:
            strengths.append(f"{name} has positive validated accuracy.")

        if score >= 70:
            strengths.append(f"{name} has strong average evidence.")

        return strengths or [f"{name} has measurable history."]

    def _weaknesses(self, name, score, accuracy, sample_size):
        weaknesses = []

        if sample_size < 5:
            weaknesses.append("Sample size is small.")

        if accuracy < 50:
            weaknesses.append(f"{name} validated accuracy is below 50%.")

        if score < 50:
            weaknesses.append(f"{name} evidence score is weak.")

        return weaknesses or ["No major weakness identified."]

    def _provider_strengths(self, score, provider):
        strengths = []

        if score >= 70:
            strengths.append("Strong historical provider score.")

        if provider.get("status") == "Available":
            strengths.append("Provider is available.")

        return strengths or ["Provider has measurable history."]

    def _provider_weaknesses(self, score, provider):
        weaknesses = []

        if score < 50:
            weaknesses.append("Provider score is below 50.")

        if provider.get("status") != "Available":
            weaknesses.append("Provider is not marked available.")

        return weaknesses or ["No major weakness identified."]

    def _average(self, values):
        cleaned = [
            value for value in values
            if value is not None
        ]

        if not cleaned:
            return 0

        return round(sum(cleaned) / len(cleaned), 2)

    def _median(self, values):
        cleaned = sorted([
            value for value in values
            if value is not None
        ])

        if not cleaned:
            return 0

        midpoint = len(cleaned) // 2
        if len(cleaned) % 2 == 1:
            return cleaned[midpoint]

        return round((cleaned[midpoint - 1] + cleaned[midpoint]) / 2, 2)

    def _rate(self, numerator, denominator):
        if denominator == 0:
            return 0

        return round(numerator / denominator * 100, 2)
