from engines.knowledge_graph_engine import KnowledgeGraphEngine


source_data = {
    "recommendations": [
        {
            "id": 1,
            "ticker": "AAPL",
            "action": "BUY",
            "confidence": 82,
            "committee_agreement": 80,
            "main_disagreement": "",
            "final_committee_summary": "Committee agrees.",
            "executive_status": "READY",
            "executive_confidence": 78,
            "executive_warnings": [],
            "evidence_breakdown": [
                {"category": "Technical", "score": 85},
                {"category": "Forecast", "score": 76},
            ],
            "assumptions": [
                "Atlas assumes technical evidence remains valid.",
            ],
            "counterfactuals": [
                {"scenario": "If forecast weakens"},
            ],
            "validation_result": {
                "success": True,
                "percentage_return": 8,
                "status": "Succeeded",
            },
        },
        {
            "id": 2,
            "ticker": "MSFT",
            "action": "HOLD",
            "confidence": 58,
            "committee_agreement": 42,
            "main_disagreement": "Forecast disagrees with Risk.",
            "final_committee_summary": "Committee disagrees.",
            "executive_status": "NEEDS_REVIEW",
            "executive_confidence": 48,
            "executive_warnings": ["Committee Agreement requires review."],
            "evidence_breakdown": [
                {"category": "Risk", "score": 35},
            ],
            "assumptions": [
                "Atlas assumes risk evidence improves.",
            ],
            "counterfactuals": [
                {"scenario": "If risk increases"},
            ],
            "validation_result": {
                "success": False,
                "percentage_return": -4,
                "status": "Failed",
            },
        },
    ],
    "benchmark_results": [
        {
            "engine_name": "BenchmarkEngine",
            "metric": "overall_hit_rate",
            "value": 50,
        },
    ],
    "provider_results": [
        {
            "provider_type": "forecast",
            "provider_name": "Mock",
            "score": 70,
            "rank": 1,
            "status": "Available",
        },
    ],
    "research_experiments": [
        {
            "experiment_id": "arl-test",
            "title": "Provider Experiment",
            "status": "Completed",
        },
    ],
}
discovery_data = {
    "discovery_history": [
        {
            "id": "disc-1",
            "title": "Failed AAPL recommendations",
            "description": "AAPL failures cluster around risk evidence.",
        },
    ],
}
historical_runs = [
    {
        "experiment_id": "hist-test",
        "configuration": {
            "tickers": ["AAPL"],
        },
        "metrics": {
            "win_rate": 50,
        },
    },
]

engine = KnowledgeGraphEngine()
graph = engine.build(
    source_data=source_data,
    discovery_data=discovery_data,
    historical_runs=historical_runs,
)

node_types = {node["type"] for node in graph["nodes"]}
relationship_types = {item["type"] for item in graph["relationships"]}

assert {
    "Ticker",
    "Recommendation",
    "Validation",
    "Benchmark",
    "Discovery",
    "Research Experiment",
    "Committee Review",
    "Executive Review",
    "Historical Replay",
    "Hypothesis",
    "Counterfactual",
    "Evidence",
    "Provider",
    "Performance Snapshot",
} <= node_types
assert "validated_by" in relationship_types
assert "discussed_by" in relationship_types
assert "reviewed_by" in relationship_types
assert "benchmarked_by" in relationship_types
assert "generated_discovery" in relationship_types
assert "tested" in relationship_types
assert "historical_analog" in relationship_types
assert "similar_to" in relationship_types

related = engine.search_related(graph, node_id="ticker:AAPL")
assert any(node["type"] == "Recommendation" for node in related["nodes"])

similar_recommendations = engine.query(
    graph,
    "similar_recommendations",
    "AAPL",
)
similar_discoveries = engine.query(
    graph,
    "similar_discoveries",
    "risk",
)
historical_analogs = engine.query(
    graph,
    "historical_analogs",
    "AAPL",
)
failures = engine.query(graph, "most_common_failures")
assumptions = engine.query(graph, "most_successful_assumptions")
providers = engine.query(graph, "provider_history", "Mock")
committee = engine.query(graph, "committee_history")
executive = engine.query(graph, "executive_history")

assert len(similar_recommendations) == 1
assert len(similar_discoveries) == 1
assert any(node["type"] == "Historical Replay" for node in historical_analogs)
assert failures[0] == {"name": "MSFT", "count": 1}
assert assumptions[0]["name"] == "Atlas assumes technical evidence remains valid."
assert providers[0]["label"] == "Mock"
assert len(committee) == 2
assert len(executive) == 2

apple_summary = engine.generate_summary(graph, "Apple")
committee_summary = engine.generate_summary(graph, "committee disagreements")
failure_summary = engine.generate_summary(graph, "failed recommendations")

assert "1 recommendations" in apple_summary
assert "committee disagreement" in committee_summary
assert "MSFT" in failure_summary

print("KnowledgeGraphEngine test passed.")
