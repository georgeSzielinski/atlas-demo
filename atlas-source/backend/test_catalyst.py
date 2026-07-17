from api.main import catalyst_summary_dashboard, catalysts_dashboard
from backend.status import catalyst_provider_status
from engines.catalyst_engine import CatalystEngine, CatalystProviderFactory
from engines.discovery_engine import DiscoveryEngine
from engines.knowledge_graph_engine import KnowledgeGraphEngine
from engines.performance_observatory import PerformanceObservatory
from engines.research_engine import ResearchEngine


engine = CatalystEngine(provider_name="mock")
analysis = engine.analyze(["AAPL", "MSFT"], as_of_date="2026-06-30")

assert analysis["provider"] == "mock"
assert analysis["controlled_behavior"]["changes_recommendation_actions"] is False
assert analysis["controlled_behavior"]["automatic_execution"] is False
assert analysis["controlled_behavior"]["requires_human_approval"] is True
assert analysis["summary"]["most_common_catalyst"] == "CPI"

aapl_context = analysis["recommendation_contexts"]["AAPL"]
aapl_event_types = [event["event_type"] for event in aapl_context]
assert "Earnings" in aapl_event_types
assert "CPI" in aapl_event_types
assert "FOMC" in aapl_event_types
assert next(
    event for event in aapl_context
    if event["event_type"] == "Earnings"
)["days_until_event"] == 15

future_provider = CatalystProviderFactory.create("earnings_calendar")
assert future_provider.provider_name == "earnings_calendar"
assert future_provider.get_events(["AAPL"], "2026-06-30") == []

recommendations = [
    {
        "id": 1,
        "ticker": "AAPL",
        "action": "BUY",
        "committee_agreement": 82,
        "knowledge_score": 80,
        "stability_score": 75,
        "catalysts": [
            event for event in aapl_context
            if event["event_type"] in {"Earnings", "CPI", "FOMC"}
        ],
        "validation_result": {
            "success": True,
            "hit": True,
            "percentage_return": 8.0,
            "status": "Succeeded",
        },
    },
    {
        "id": 2,
        "ticker": "AAPL",
        "action": "HOLD",
        "committee_agreement": 74,
        "knowledge_score": 70,
        "stability_score": 66,
        "catalysts": [
            event for event in aapl_context
            if event["event_type"] == "Product Launch"
        ],
        "validation_result": {
            "success": False,
            "hit": False,
            "percentage_return": -2.0,
            "status": "Failed",
        },
    },
]
source_data = {
    "recommendations": recommendations,
    "catalysts": analysis["events"],
    "benchmark_results": [],
    "provider_results": [
        {
            "provider_type": "catalyst",
            "provider_name": "mock",
            "status": "Available",
            "score": 80,
        }
    ],
    "research_experiments": [],
}

observatory = PerformanceObservatory().generate(
    source_data=source_data,
    discovery_data={
        "recent_discoveries": [],
        "top_discoveries": [],
        "discovery_history": [],
    },
)
catalyst_summary = observatory["catalyst_summary"]
assert catalyst_summary["most_common_catalyst"] == "CPI"
assert catalyst_summary["best_performing_catalyst"] in {"CPI", "Earnings", "FOMC"}
assert catalyst_summary["worst_performing_catalyst"] == "Product Launch"

discoveries = DiscoveryEngine().analyze(
    source_data=source_data,
    discovery_date="2026-06-30T14:00:00",
)
descriptions = [item["description"] for item in discoveries]
assert "CPI weeks increase volatility." in descriptions
assert "FOMC weeks reduce recommendation stability." in descriptions
assert any("outperform Product Launch" in description for description in descriptions)

research = ResearchEngine().catalyst_research(recommendations)
assert "Before earnings" in research["future_studies"]
assert research["filters"]["before_earnings"] == []
assert research["filters"]["macro_weeks"] == [recommendations[0]]
assert research["filters"]["high_volatility_periods"] == [recommendations[0]]
assert "no automatic execution" in research["policy"]

graph = KnowledgeGraphEngine().build(
    source_data=source_data,
    discovery_data={
        "recent_discoveries": [],
        "top_discoveries": [],
        "discovery_history": [],
    },
    historical_runs=[],
)
catalyst_nodes = [node for node in graph["nodes"] if node["type"] == "Catalyst"]
catalyst_relationships = [
    relationship for relationship in graph["relationships"]
    if relationship["type"] == "has_catalyst"
]
assert catalyst_nodes
assert catalyst_relationships

api_analysis = catalysts_dashboard()
assert api_analysis["provider"] == "mock"
assert api_analysis["recommendation_contexts"]

api_summary = catalyst_summary_dashboard()
assert api_summary["event_count"] > 0

health = catalyst_provider_status()
assert health["active_provider"] == "mock"
assert health["healthy"] is True
assert health["events_available"] > 0

print("CatalystEngine test passed.")
