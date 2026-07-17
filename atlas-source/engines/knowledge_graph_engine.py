class KnowledgeGraphEngine:
    TICKER_ALIASES = {
        "apple": "AAPL",
        "microsoft": "MSFT",
        "nvidia": "NVDA",
        "tesla": "TSLA",
        "amazon": "AMZN",
        "google": "GOOGL",
        "alphabet": "GOOGL",
    }

    def build(
        self,
        source_data=None,
        discovery_data=None,
        historical_runs=None,
    ):
        if source_data is None:
            from database.repository import get_discovery_source_data

            source_data = get_discovery_source_data()

        if discovery_data is None:
            discovery_data = self._discovery_data()

        if historical_runs is None:
            historical_runs = self._historical_runs()

        graph = {"nodes": [], "relationships": []}
        seen_nodes = set()
        seen_relationships = set()

        self._recommendation_graph(graph, seen_nodes, seen_relationships, source_data)
        self._catalyst_graph(graph, seen_nodes, seen_relationships, source_data)
        self._probability_graph(graph, seen_nodes, seen_relationships, source_data)
        self._benchmark_graph(graph, seen_nodes, seen_relationships, source_data)
        self._provider_graph(graph, seen_nodes, seen_relationships, source_data)
        self._sec_graph(graph, seen_nodes, seen_relationships, source_data)
        self._macro_graph(graph, seen_nodes, seen_relationships, source_data)
        self._experiment_graph(graph, seen_nodes, seen_relationships, source_data)
        self._scientific_validation_graph(
            graph,
            seen_nodes,
            seen_relationships,
            source_data,
        )
        self._discovery_graph(graph, seen_nodes, seen_relationships, discovery_data)
        self._historical_graph(graph, seen_nodes, seen_relationships, historical_runs)
        self._case_study_graph(graph, seen_nodes, seen_relationships, source_data)
        self._research_memory_graph(graph, seen_nodes, seen_relationships, source_data)
        self._portfolio_strategy_graph(graph, seen_nodes, seen_relationships, source_data)
        self._portfolio_construction_graph(
            graph,
            seen_nodes,
            seen_relationships,
            source_data,
        )
        self._performance_snapshot_graph(graph, seen_nodes, source_data)
        self._ticker_similarity_graph(graph, seen_relationships)
        graph["summary"] = self.generate_summary(graph, "Atlas")

        return graph

    def search_related(self, graph, node_id=None, node_type=None, query=None):
        query_text = (query or "").lower()
        node_ids = {
            node["id"] for node in graph["nodes"]
            if (node_id is None or node["id"] == node_id)
            and (node_type is None or node["type"] == node_type)
            and (
                not query_text
                or query_text in node["label"].lower()
                or query_text in str(node.get("properties", {})).lower()
            )
        }
        related_ids = set(node_ids)

        for relationship in graph["relationships"]:
            if relationship["source"] in node_ids:
                related_ids.add(relationship["target"])

            if relationship["target"] in node_ids:
                related_ids.add(relationship["source"])

        return {
            "nodes": [
                node for node in graph["nodes"]
                if node["id"] in related_ids
            ],
            "relationships": [
                relationship for relationship in graph["relationships"]
                if (
                    relationship["source"] in related_ids
                    and relationship["target"] in related_ids
                )
            ],
        }

    def query(self, graph, query_type, value=None):
        if query_type == "similar_recommendations":
            return self.similar_recommendations(graph, value)

        if query_type == "similar_discoveries":
            return self.similar_discoveries(graph, value)

        if query_type == "historical_analogs":
            return self.historical_analogs(graph, value)

        if query_type == "research_memory":
            return self.research_memory(graph)

        if query_type == "sec_filings":
            return self.sec_filings(graph, value)

        if query_type == "macro":
            return self.macro(graph)

        if query_type == "most_common_failures":
            return self.most_common_failures(graph)

        if query_type == "most_successful_assumptions":
            return self.most_successful_assumptions(graph)

        if query_type == "provider_history":
            return self.provider_history(graph, value)

        if query_type == "committee_history":
            return self.committee_history(graph)

        if query_type == "executive_history":
            return self.executive_history(graph)

        return []

    def similar_recommendations(self, graph, ticker_or_action):
        value = (ticker_or_action or "").upper()

        return [
            node for node in graph["nodes"]
            if node["type"] == "Recommendation"
            and (
                node["properties"].get("ticker", "").upper() == value
                or node["properties"].get("action", "").upper() == value
            )
        ]

    def similar_discoveries(self, graph, term):
        text = (term or "").lower()

        return [
            node for node in graph["nodes"]
            if node["type"] == "Discovery"
            and (
                text in node["label"].lower()
                or text in str(node["properties"]).lower()
            )
        ]

    def historical_analogs(self, graph, ticker):
        value = (ticker or "").upper()

        return [
            node for node in graph["nodes"]
            if (
                node["properties"].get("ticker", "").upper() == value
                or value in str(node["properties"].get("tickers", [])).upper()
                or value in str(
                    node["properties"].get(
                        "configuration",
                        {},
                    ).get("tickers", [])
                ).upper()
            )
            and node["type"] in {"Recommendation", "Historical Replay"}
        ]

    def research_memory(self, graph):
        return [
            node for node in graph["nodes"]
            if node["type"] == "Research Memory"
        ]

    def sec_filings(self, graph, ticker=None):
        value = (ticker or "").upper()

        return [
            node for node in graph["nodes"]
            if node["type"] == "SEC Filing"
            and (
                not value
                or node["properties"].get("ticker", "").upper() == value
            )
        ]

    def macro(self, graph):
        return [
            node for node in graph["nodes"]
            if node["type"] in {"Macro Regime", "Macro Indicator"}
        ]

    def most_common_failures(self, graph):
        failures = {}

        for node in graph["nodes"]:
            if node["type"] != "Validation":
                continue

            if node["properties"].get("success") is not False:
                continue

            key = node["properties"].get("ticker") or "Unknown"
            failures[key] = failures.get(key, 0) + 1

        return self._ranked_counts(failures)

    def most_successful_assumptions(self, graph):
        successful_recommendations = {
            relationship["source"]
            for relationship in graph["relationships"]
            if relationship["type"] == "validated_by"
            and self._node(graph, relationship["target"]).get("properties", {}).get("success")
            is True
        }
        counts = {}

        for relationship in graph["relationships"]:
            if relationship["type"] != "assumed":
                continue

            if relationship["source"] not in successful_recommendations:
                continue

            assumption = self._node(graph, relationship["target"])["label"]
            counts[assumption] = counts.get(assumption, 0) + 1

        return self._ranked_counts(counts)

    def provider_history(self, graph, provider_name=None):
        value = (provider_name or "").lower()

        return [
            node for node in graph["nodes"]
            if node["type"] == "Provider"
            and (not value or value in node["label"].lower())
        ]

    def committee_history(self, graph):
        return [
            node for node in graph["nodes"]
            if node["type"] == "Committee Review"
        ]

    def executive_history(self, graph):
        return [
            node for node in graph["nodes"]
            if node["type"] == "Executive Review"
        ]

    def generate_summary(self, graph, topic):
        normalized = self._normalize_topic(topic)

        if normalized == "committee disagreements":
            disagreements = [
                node for node in graph["nodes"]
                if node["type"] == "Committee Review"
                and node["properties"].get("main_disagreement")
            ]

            return (
                "Atlas has learned from "
                f"{len(disagreements)} committee disagreement records."
            )

        if normalized == "failed recommendations":
            failures = self.most_common_failures(graph)

            return (
                "Atlas has learned from failed recommendations: "
                f"{', '.join([item['name'] for item in failures]) or 'none'}."
            )

        ticker = self.TICKER_ALIASES.get(normalized, topic.upper())
        recommendations = self.similar_recommendations(graph, ticker)
        validations = [
            relationship for relationship in graph["relationships"]
            if relationship["type"] == "validated_by"
            and relationship["source"] in {node["id"] for node in recommendations}
        ]

        return (
            f"Atlas knows {len(recommendations)} recommendations and "
            f"{len(validations)} validations related to {ticker}."
        )

    def _recommendation_graph(self, graph, seen_nodes, seen_relationships, source_data):
        for recommendation in source_data.get("recommendations", []):
            ticker = recommendation.get("ticker", "UNKNOWN")
            recommendation_id = f"recommendation:{recommendation.get('id', ticker)}"
            ticker_id = f"ticker:{ticker}"
            validation = recommendation.get("validation_result")

            self._add_node(graph, seen_nodes, ticker_id, "Ticker", ticker, {})
            self._add_node(
                graph,
                seen_nodes,
                recommendation_id,
                "Recommendation",
                f"{ticker} {recommendation.get('action', '')}",
                recommendation,
            )
            self._add_relationship(
                graph,
                seen_relationships,
                ticker_id,
                recommendation_id,
                "has_recommendation",
            )

            if validation is not None:
                validation_id = f"validation:{recommendation.get('id', ticker)}"
                properties = dict(validation) | {"ticker": ticker}
                self._add_node(
                    graph,
                    seen_nodes,
                    validation_id,
                    "Validation",
                    f"{ticker} validation",
                    properties,
                )
                self._add_relationship(
                    graph,
                    seen_relationships,
                    recommendation_id,
                    validation_id,
                    "validated_by",
                )

            self._committee_node(graph, seen_nodes, seen_relationships, recommendation_id, recommendation)
            self._executive_node(graph, seen_nodes, seen_relationships, recommendation_id, recommendation)
            self._evidence_nodes(graph, seen_nodes, seen_relationships, recommendation_id, recommendation)
            self._hypothesis_nodes(graph, seen_nodes, seen_relationships, recommendation_id, recommendation)
            self._counterfactual_nodes(graph, seen_nodes, seen_relationships, recommendation_id, recommendation)

    def _catalyst_graph(self, graph, seen_nodes, seen_relationships, source_data):
        catalyst_rows = list(source_data.get("catalysts", []))
        for recommendation in source_data.get("recommendations", []):
            for catalyst in recommendation.get("catalysts", []):
                row = dict(catalyst)
                row["recommendation_id"] = recommendation.get("id")
                row["recommendation_ticker"] = recommendation.get("ticker")
                catalyst_rows.append(row)

        for index, catalyst in enumerate(catalyst_rows, start=1):
            event_type = catalyst.get("event_type", "Catalyst")
            ticker = catalyst.get("ticker") or catalyst.get("recommendation_ticker")
            catalyst_id = (
                "catalyst:"
                f"{ticker or 'market'}:"
                f"{event_type}:"
                f"{catalyst.get('event_date', index)}"
            )
            self._add_node(
                graph,
                seen_nodes,
                catalyst_id,
                "Catalyst",
                event_type,
                catalyst,
            )

            if ticker:
                ticker_id = f"ticker:{ticker}"
                self._add_node(graph, seen_nodes, ticker_id, "Ticker", ticker, {})
                self._add_relationship(
                    graph,
                    seen_relationships,
                    ticker_id,
                    catalyst_id,
                    "has_catalyst",
                )

            recommendation_id = catalyst.get("recommendation_id")
            if recommendation_id is not None:
                self._add_relationship(
                    graph,
                    seen_relationships,
                    f"recommendation:{recommendation_id}",
                    catalyst_id,
                    "has_catalyst",
                )

            for case in source_data.get("case_studies", []):
                if case.get("ticker") == ticker:
                    case_id = f"case_study:{case.get('case_id', ticker)}"
                    self._add_relationship(
                        graph,
                        seen_relationships,
                        case_id,
                        catalyst_id,
                        "includes_catalyst",
                    )

    def _probability_graph(self, graph, seen_nodes, seen_relationships, source_data):
        for recommendation in source_data.get("recommendations", []):
            report = recommendation.get("probability_report")
            if not isinstance(report, dict) or not report:
                continue

            recommendation_id = f"recommendation:{recommendation.get('id', recommendation.get('ticker', 'unknown'))}"
            probability_id = f"probability:{recommendation.get('id', recommendation.get('ticker', 'unknown'))}"
            self._add_node(
                graph,
                seen_nodes,
                probability_id,
                "Probability",
                f"{recommendation.get('ticker', '')} probability",
                report,
            )
            self._add_relationship(
                graph,
                seen_relationships,
                recommendation_id,
                probability_id,
                "estimated_by",
            )

            for case in report.get("similar_historical_cases", []):
                if not case.get("id"):
                    continue

                self._add_relationship(
                    graph,
                    seen_relationships,
                    probability_id,
                    f"case_study:{case['id']}",
                    "uses_similar_case",
                )

    def _benchmark_graph(self, graph, seen_nodes, seen_relationships, source_data):
        for index, benchmark in enumerate(source_data.get("benchmark_results", []), start=1):
            benchmark_id = (
                "benchmark:"
                f"{benchmark.get('engine_name', 'unknown')}:"
                f"{benchmark.get('metric', index)}"
            )
            self._add_node(
                graph,
                seen_nodes,
                benchmark_id,
                "Benchmark",
                benchmark.get("metric", "Benchmark"),
                benchmark,
            )

            for node in graph["nodes"]:
                if node["type"] == "Recommendation":
                    self._add_relationship(
                        graph,
                        seen_relationships,
                        node["id"],
                        benchmark_id,
                        "benchmarked_by",
                    )

    def _provider_graph(self, graph, seen_nodes, seen_relationships, source_data):
        for provider in source_data.get("provider_results", []):
            provider_id = (
                "provider:"
                f"{provider.get('provider_type', 'unknown')}:"
                f"{provider.get('provider_name', 'unknown')}"
            )
            self._add_node(
                graph,
                seen_nodes,
                provider_id,
                "Provider",
                provider.get("provider_name", "Provider"),
                provider,
            )

    def _sec_graph(self, graph, seen_nodes, seen_relationships, source_data):
        filings = source_data.get("sec_filings")
        if filings is None:
            try:
                from engines.sec_engine import SecEngine

                filings = SecEngine().filings()
            except Exception:
                filings = []

        for filing in filings:
            ticker = filing.get("ticker", "UNKNOWN")
            ticker_id = f"ticker:{ticker}"
            filing_id = (
                "sec_filing:"
                f"{ticker}:"
                f"{filing.get('form_type', '').replace(' ', '-')}:"
                f"{filing.get('filing_date', '')}"
            )
            self._add_node(graph, seen_nodes, ticker_id, "Ticker", ticker, {})
            self._add_node(
                graph,
                seen_nodes,
                filing_id,
                "SEC Filing",
                f"{ticker} {filing.get('form_type', '')}",
                filing,
            )
            self._add_relationship(
                graph,
                seen_relationships,
                ticker_id,
                filing_id,
                "filed",
                {"form_type": filing.get("form_type", "")},
            )

    def _macro_graph(self, graph, seen_nodes, seen_relationships, source_data):
        report = source_data.get("macro_report")
        if report is None:
            try:
                from engines.macro_engine import MacroEngine

                report = MacroEngine().analyze()
            except Exception:
                report = {"indicators": [], "current_macro_regime": "Unavailable"}

        macro_id = "macro:current"
        self._add_node(
            graph,
            seen_nodes,
            macro_id,
            "Macro Regime",
            report.get("current_macro_regime", "Macro Regime"),
            report,
        )

        for indicator in report.get("indicators", []):
            indicator_id = f"macro_indicator:{indicator.get('indicator', '')}"
            self._add_node(
                graph,
                seen_nodes,
                indicator_id,
                "Macro Indicator",
                indicator.get("indicator", "Macro Indicator"),
                indicator,
            )
            self._add_relationship(
                graph,
                seen_relationships,
                macro_id,
                indicator_id,
                "uses_macro_indicator",
                {"value": indicator.get("value", 0)},
            )

    def _experiment_graph(self, graph, seen_nodes, seen_relationships, source_data):
        providers = [
            node for node in graph["nodes"]
            if node["type"] == "Provider"
        ]

        for experiment in source_data.get("research_experiments", []):
            experiment_id = f"experiment:{experiment.get('experiment_id', '')}"
            self._add_node(
                graph,
                seen_nodes,
                experiment_id,
                "Research Experiment",
                experiment.get("title", "Research Experiment"),
                experiment,
            )

            for provider in providers:
                self._add_relationship(
                    graph,
                    seen_relationships,
                    experiment_id,
                    provider["id"],
                    "tested",
                )

    def _scientific_validation_graph(
        self,
        graph,
        seen_nodes,
        seen_relationships,
        source_data,
    ):
        for report in source_data.get("scientific_validations", []):
            experiment_id = report.get("experiment_id", "unknown")
            validation_id = f"scientific_validation:{experiment_id}"
            feature_id = f"feature:{report.get('feature_tested', 'unknown')}"

            self._add_node(
                graph,
                seen_nodes,
                validation_id,
                "Scientific Validation",
                report.get("feature_tested", "Scientific Validation"),
                report,
            )
            self._add_node(
                graph,
                seen_nodes,
                feature_id,
                "Research Feature",
                report.get("feature_tested", "Research Feature"),
                {
                    "feature_tested": report.get("feature_tested", ""),
                    "adoption_decision": report.get("adoption_decision", ""),
                },
            )
            self._add_relationship(
                graph,
                seen_relationships,
                validation_id,
                feature_id,
                "tests_feature",
            )

            experiment_node_id = f"experiment:{experiment_id}"
            if self._node(graph, experiment_node_id):
                self._add_relationship(
                    graph,
                    seen_relationships,
                    experiment_node_id,
                    validation_id,
                    "scientifically_validated_by",
                )

    def _case_study_graph(self, graph, seen_nodes, seen_relationships, source_data):
        for case in source_data.get("case_studies", []):
            case_id = f"case_study:{case.get('case_id', case.get('ticker', 'unknown'))}"
            ticker = case.get("ticker", "UNKNOWN")
            ticker_id = f"ticker:{ticker}"

            self._add_node(graph, seen_nodes, ticker_id, "Ticker", ticker, {})
            self._add_node(
                graph,
                seen_nodes,
                case_id,
                "Case Study",
                f"{ticker} case study",
                case,
            )
            self._add_relationship(
                graph,
                seen_relationships,
                ticker_id,
                case_id,
                "has_case_study",
            )

            for node in graph["nodes"]:
                if (
                    node["type"] == "Recommendation"
                    and node["properties"].get("ticker") == ticker
                ):
                    self._add_relationship(
                        graph,
                        seen_relationships,
                        case_id,
                        node["id"],
                        "summarizes_recommendation",
                    )

                if (
                    node["type"] == "Validation"
                    and node["properties"].get("ticker") == ticker
                ):
                    self._add_relationship(
                        graph,
                        seen_relationships,
                        case_id,
                        node["id"],
                        "summarizes_validation",
                    )

                if node["type"] == "Discovery":
                    self._add_relationship(
                        graph,
                        seen_relationships,
                        case_id,
                        node["id"],
                        "informed_by_discovery",
                    )

                if node["type"] == "Research Experiment":
                    self._add_relationship(
                        graph,
                        seen_relationships,
                        case_id,
                        node["id"],
                        "informed_by_experiment",
                    )

                if node["type"] == "Historical Replay":
                    self._add_relationship(
                        graph,
                        seen_relationships,
                        case_id,
                        node["id"],
                        "historical_analog",
                    )

                if node["type"] == "Provider":
                    self._add_relationship(
                        graph,
                        seen_relationships,
                        case_id,
                        node["id"],
                        "references_provider",
                    )

    def _research_memory_graph(self, graph, seen_nodes, seen_relationships, source_data):
        from engines.research_memory_engine import ResearchMemoryEngine

        summary = ResearchMemoryEngine().graph_relationship_summary(source_data)
        self._add_node(
            graph,
            seen_nodes,
            "research_memory:summary",
            "Research Memory",
            "Research Memory Summary",
            summary,
        )

        for analog in summary["strongest_analogs"]:
            self._add_relationship(
                graph,
                seen_relationships,
                analog["source"],
                analog["target"],
                "strongest_analog",
                {
                    "similarity_score": analog["score"],
                    "component_scores": analog["components"],
                },
            )

        for analog in summary["weakest_analogs"]:
            self._add_relationship(
                graph,
                seen_relationships,
                analog["source"],
                analog["target"],
                "weakest_analog",
                {
                    "similarity_score": analog["score"],
                    "component_scores": analog["components"],
                },
            )

    def _portfolio_strategy_graph(self, graph, seen_nodes, seen_relationships, source_data):
        for index, review in enumerate(source_data.get("portfolio_strategies", []), start=1):
            portfolio_id = f"portfolio:{index}"
            strategy_id = f"portfolio_strategy:{index}"
            optimization_id = f"portfolio_optimization:{index}"

            self._add_node(
                graph,
                seen_nodes,
                portfolio_id,
                "Portfolio",
                f"Portfolio {index}",
                review.get("analysis", {}),
            )
            self._add_node(
                graph,
                seen_nodes,
                strategy_id,
                "Portfolio Strategy",
                f"Portfolio Strategy {index}",
                {
                    "recommendations": review.get(
                        "strategy_recommendations",
                        [],
                    ),
                    "controlled_decision": review.get(
                        "controlled_decision",
                        {},
                    ),
                },
            )
            self._add_node(
                graph,
                seen_nodes,
                optimization_id,
                "Portfolio Optimization",
                f"Portfolio Optimization {index}",
                review.get("simulation", {}),
            )
            self._add_relationship(
                graph,
                seen_relationships,
                portfolio_id,
                strategy_id,
                "has_strategy",
            )
            self._add_relationship(
                graph,
                seen_relationships,
                strategy_id,
                optimization_id,
                "optimizes",
            )

    def _portfolio_construction_graph(
        self,
        graph,
        seen_nodes,
        seen_relationships,
        source_data,
    ):
        for index, report in enumerate(
            source_data.get("portfolio_construction_reports", []),
            start=1,
        ):
            allocation_id = f"portfolio_allocation:{index}"
            risk_id = f"risk_budget:{index}"
            diversification_id = f"diversification:{index}"
            capital_id = f"capital_allocation:{index}"
            health_id = f"portfolio_health:{index}"
            rebalance_id = f"rebalancing_decisions:{index}"

            self._add_node(
                graph,
                seen_nodes,
                allocation_id,
                "Portfolio Allocation",
                f"Portfolio Allocation {index}",
                {"allocations": report.get("recommended_allocations", [])},
            )
            self._add_node(
                graph,
                seen_nodes,
                risk_id,
                "Risk Budget",
                f"Risk Budget {index}",
                report.get("risk_budget", {}),
            )
            self._add_node(
                graph,
                seen_nodes,
                diversification_id,
                "Diversification",
                f"Diversification {index}",
                report.get("diversification", {}),
            )
            self._add_node(
                graph,
                seen_nodes,
                capital_id,
                "Capital Allocation",
                f"Capital Allocation {index}",
                {
                    "ranking": report.get("capital_allocation_ranking")
                    or report.get("recommended_allocations", []),
                },
            )
            self._add_node(
                graph,
                seen_nodes,
                health_id,
                "Portfolio Health",
                f"Portfolio Health {index}",
                report.get("operations_summary", {}),
            )
            self._add_node(
                graph,
                seen_nodes,
                rebalance_id,
                "Rebalancing Decisions",
                f"Rebalancing Decisions {index}",
                {"actions": report.get("portfolio_actions", [])},
            )

            for source, target, relationship in [
                (allocation_id, capital_id, "ranks_capital"),
                (allocation_id, risk_id, "has_risk_budget"),
                (allocation_id, diversification_id, "has_diversification"),
                (diversification_id, health_id, "determines_health"),
                (health_id, rebalance_id, "informs_rebalance"),
            ]:
                self._add_relationship(
                    graph,
                    seen_relationships,
                    source,
                    target,
                    relationship,
                )

            for allocation in report.get("recommended_allocations", []):
                ticker = allocation.get("ticker")
                if not ticker:
                    continue
                ticker_id = f"ticker:{ticker}"
                self._add_node(graph, seen_nodes, ticker_id, "Ticker", ticker, {})
                self._add_relationship(
                    graph,
                    seen_relationships,
                    ticker_id,
                    allocation_id,
                    "has_allocation",
                    allocation,
                )

    def _discovery_graph(self, graph, seen_nodes, seen_relationships, discovery_data):
        discoveries = discovery_data.get("discovery_history") or discovery_data.get("recent_discoveries", [])

        for discovery in discoveries:
            discovery_id = f"discovery:{discovery.get('id', discovery.get('title', 'unknown'))}"
            self._add_node(
                graph,
                seen_nodes,
                discovery_id,
                "Discovery",
                discovery.get("title", "Discovery"),
                discovery,
            )

            for node in graph["nodes"]:
                if node["type"] == "Recommendation":
                    self._add_relationship(
                        graph,
                        seen_relationships,
                        node["id"],
                        discovery_id,
                        "generated_discovery",
                    )

    def _historical_graph(self, graph, seen_nodes, seen_relationships, historical_runs):
        for run in historical_runs:
            run_id = f"historical_replay:{run.get('experiment_id', run.get('id', 'unknown'))}"
            config = run.get("configuration", {})
            self._add_node(
                graph,
                seen_nodes,
                run_id,
                "Historical Replay",
                run.get("experiment_id", "Historical Replay"),
                run,
            )

            for ticker in config.get("tickers", []):
                ticker_id = f"ticker:{ticker}"
                self._add_node(graph, seen_nodes, ticker_id, "Ticker", ticker, {})
                self._add_relationship(
                    graph,
                    seen_relationships,
                    ticker_id,
                    run_id,
                    "historical_analog",
                )

    def _performance_snapshot_graph(self, graph, seen_nodes, source_data):
        recommendations = source_data.get("recommendations", [])
        validations = [
            item.get("validation_result")
            for item in recommendations
            if item.get("validation_result") is not None
        ]
        successful = [
            item for item in validations
            if item.get("success") is True
        ]
        snapshot = {
            "recommendation_count": len(recommendations),
            "validation_count": len(validations),
            "win_rate": (
                round(len(successful) / len(validations) * 100, 2)
                if validations else 0
            ),
            "benchmark_count": len(source_data.get("benchmark_results", [])),
        }
        self._add_node(
            graph,
            seen_nodes,
            "performance_snapshot:current",
            "Performance Snapshot",
            "Current Performance Snapshot",
            snapshot,
        )

    def _ticker_similarity_graph(self, graph, seen_relationships):
        tickers = [
            node for node in graph["nodes"]
            if node["type"] == "Ticker"
        ]

        for index, ticker in enumerate(tickers):
            for other in tickers[index + 1:]:
                self._add_relationship(
                    graph,
                    seen_relationships,
                    ticker["id"],
                    other["id"],
                    "similar_to",
                    {"basis": "coexisting_atlas_history"},
                )

    def _committee_node(self, graph, seen_nodes, seen_relationships, recommendation_id, recommendation):
        if recommendation.get("committee_agreement") is None:
            return

        committee_id = f"committee:{recommendation_id}"
        self._add_node(
            graph,
            seen_nodes,
            committee_id,
            "Committee Review",
            f"Committee {recommendation.get('ticker', '')}",
            {
                "agreement": recommendation.get("committee_agreement", 0),
                "main_disagreement": recommendation.get("main_disagreement", ""),
                "summary": recommendation.get("final_committee_summary", ""),
            },
        )
        self._add_relationship(
            graph,
            seen_relationships,
            recommendation_id,
            committee_id,
            "discussed_by",
        )

    def _executive_node(self, graph, seen_nodes, seen_relationships, recommendation_id, recommendation):
        if not recommendation.get("executive_status"):
            return

        executive_id = f"executive:{recommendation_id}"
        self._add_node(
            graph,
            seen_nodes,
            executive_id,
            "Executive Review",
            f"Executive {recommendation.get('ticker', '')}",
            {
                "status": recommendation.get("executive_status", ""),
                "confidence": recommendation.get("executive_confidence", 0),
                "warnings": recommendation.get("executive_warnings", []),
            },
        )
        self._add_relationship(
            graph,
            seen_relationships,
            recommendation_id,
            executive_id,
            "reviewed_by",
        )

    def _evidence_nodes(self, graph, seen_nodes, seen_relationships, recommendation_id, recommendation):
        for index, evidence in enumerate(recommendation.get("evidence_breakdown", []), start=1):
            name = evidence.get("category") or evidence.get("name") or "Evidence"
            evidence_id = f"evidence:{recommendation_id}:{index}:{name}"
            self._add_node(
                graph,
                seen_nodes,
                evidence_id,
                "Evidence",
                name,
                evidence,
            )
            self._add_relationship(
                graph,
                seen_relationships,
                recommendation_id,
                evidence_id,
                "supported_by",
            )

    def _hypothesis_nodes(self, graph, seen_nodes, seen_relationships, recommendation_id, recommendation):
        for index, assumption in enumerate(recommendation.get("assumptions", []), start=1):
            assumption_id = f"hypothesis:{recommendation_id}:{index}"
            self._add_node(
                graph,
                seen_nodes,
                assumption_id,
                "Hypothesis",
                assumption,
                {"assumption": assumption},
            )
            self._add_relationship(
                graph,
                seen_relationships,
                recommendation_id,
                assumption_id,
                "assumed",
            )

    def _counterfactual_nodes(self, graph, seen_nodes, seen_relationships, recommendation_id, recommendation):
        for index, counterfactual in enumerate(recommendation.get("counterfactuals", []), start=1):
            label = counterfactual.get("scenario", "Counterfactual")
            counterfactual_id = f"counterfactual:{recommendation_id}:{index}"
            self._add_node(
                graph,
                seen_nodes,
                counterfactual_id,
                "Counterfactual",
                label,
                counterfactual,
            )
            self._add_relationship(
                graph,
                seen_relationships,
                recommendation_id,
                counterfactual_id,
                "challenged_by",
            )

    def _add_node(self, graph, seen_nodes, node_id, node_type, label, properties):
        if node_id in seen_nodes:
            return

        seen_nodes.add(node_id)
        graph["nodes"].append({
            "id": node_id,
            "type": node_type,
            "label": label,
            "properties": properties or {},
        })

    def _add_relationship(self, graph, seen_relationships, source, target, relationship_type, properties=None):
        key = (source, target, relationship_type)

        if key in seen_relationships:
            return

        seen_relationships.add(key)
        graph["relationships"].append({
            "source": source,
            "target": target,
            "type": relationship_type,
            "properties": properties or {},
        })

    def _node(self, graph, node_id):
        return next(
            (node for node in graph["nodes"] if node["id"] == node_id),
            {},
        )

    def _ranked_counts(self, counts):
        return [
            {"name": name, "count": count}
            for name, count in sorted(
                counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]

    def _normalize_topic(self, topic):
        return (topic or "").strip().lower()

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

    def _historical_runs(self):
        try:
            from database.repository import get_historical_validation_runs

            return get_historical_validation_runs(limit=20)
        except Exception:
            return []
