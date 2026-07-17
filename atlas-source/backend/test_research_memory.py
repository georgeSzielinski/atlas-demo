import os
import tempfile

import database.connection as connection
from api.main import research_memory_dashboard
from database.repository import save_case_studies
from database.setup import setup_database
from engines.case_study_engine import CaseStudyEngine
from engines.discovery_engine import DiscoveryEngine
from engines.knowledge_graph_engine import KnowledgeGraphEngine
from engines.performance_observatory import PerformanceObservatory
from engines.research_memory_engine import ResearchMemoryEngine


history = [
    {
        "id": 1,
        "ticker": "AAPL",
        "sector": "Technology",
        "action": "BUY",
        "market_regime": "Bull",
        "committee_agreement": 86,
        "executive_status": "READY",
        "knowledge_score": 92,
        "stability_score": 84,
        "evidence_breakdown": [
            {"category": "Fundamentals", "score": 88},
            {"category": "Forecast", "score": 82},
        ],
        "catalysts": [{"event_type": "Earnings"}],
        "probability_report": {
            "probabilities": {
                "outperformance": 72,
                "market_performance": 18,
                "underperformance": 10,
            },
            "expected_outcome": {"expected_return": 7},
            "confidence_quality": {"uncertainty_level": "Low"},
        },
        "portfolio_strategy": ["Maintain", "Core position"],
        "validation_result": {
            "success": True,
            "hit": True,
            "percentage_return": 9,
            "holding_period": 45,
        },
    },
    {
        "id": 2,
        "ticker": "MSFT",
        "sector": "Technology",
        "action": "BUY",
        "market_regime": "Bull",
        "committee_agreement": 82,
        "executive_status": "READY",
        "knowledge_score": 90,
        "stability_score": 80,
        "evidence_breakdown": [
            {"category": "Fundamentals", "score": 84},
            {"category": "Forecast", "score": 78},
        ],
        "catalysts": [{"event_type": "Earnings"}],
        "probability_report": {
            "probabilities": {
                "outperformance": 68,
                "market_performance": 20,
                "underperformance": 12,
            },
            "expected_outcome": {"expected_return": 6},
            "confidence_quality": {"uncertainty_level": "Low"},
        },
        "portfolio_strategy": ["Maintain", "Core position"],
        "validation_result": {
            "success": True,
            "hit": True,
            "percentage_return": 6,
            "holding_period": 30,
        },
    },
    {
        "id": 3,
        "ticker": "TSLA",
        "sector": "Consumer Discretionary",
        "action": "BUY",
        "market_regime": "Volatile",
        "committee_agreement": 52,
        "executive_status": "CAUTION",
        "knowledge_score": 64,
        "stability_score": 42,
        "evidence_breakdown": [
            {"category": "News", "score": 76},
            {"category": "Forecast", "score": 66},
        ],
        "catalysts": [{"event_type": "Product Launch"}],
        "probability_report": {
            "probabilities": {
                "outperformance": 30,
                "market_performance": 35,
                "underperformance": 35,
            },
            "expected_outcome": {"expected_return": -2},
            "confidence_quality": {"uncertainty_level": "High"},
        },
        "portfolio_strategy": ["Reduce"],
        "validation_result": {
            "success": False,
            "hit": False,
            "percentage_return": -5,
            "holding_period": 20,
        },
    },
]

target = {
    "id": 99,
    "ticker": "NVDA",
    "sector": "Technology",
    "action": "BUY",
    "market_regime": "Bull",
    "committee_agreement": 84,
    "executive_status": "READY",
    "knowledge_score": 91,
    "stability_score": 82,
    "evidence_breakdown": [
        {"category": "Fundamentals", "score": 86},
        {"category": "Forecast", "score": 80},
    ],
    "catalysts": [{"event_type": "Earnings"}],
    "probability_report": {
        "probabilities": {
            "outperformance": 70,
            "market_performance": 19,
            "underperformance": 11,
        },
        "expected_outcome": {"expected_return": 6.5},
        "confidence_quality": {"uncertainty_level": "Low"},
    },
    "portfolio_strategy": ["Maintain", "Core position"],
}

source_data = {
    "recommendations": history,
    "case_studies": [],
    "benchmark_results": [],
    "provider_results": [],
    "research_experiments": [],
    "catalysts": [],
}

engine = ResearchMemoryEngine()
report = engine.build(target, source_data=source_data)
analogs = report["similar_historical_cases"]

assert analogs[0]["ticker"] == "AAPL"
assert analogs[0]["similarity_score"] > analogs[-1]["similarity_score"]
assert analogs[0]["component_scores"]["market_regime"] == 12
assert analogs[0]["component_scores"]["evidence_profile"] == 14
assert report["lessons"]["average_historical_return"] == 3.33
assert report["lessons"]["average_holding_period"] == 31.67
assert report["lessons"]["win_rate"] == 66.67
assert {"pattern": "Fundamentals", "count": 2} in report["lessons"]["most_useful_evidence"]
assert {"pattern": "Earnings", "count": 2} in report["lessons"]["frequent_catalyst_behavior"]
assert report["policy"]["changes_recommendation_behavior"] is False

original_action = target["action"]
target["research_memory_report"] = report
assert target["action"] == original_action

case = CaseStudyEngine().build_case_study(
    history[0],
    case_date="2026-06-30T16:00:00",
)
assert case["lessons_learned"]["most_useful_evidence"] == "Fundamentals"

case_source = dict(source_data)
case_source["case_studies"] = [case]
graph = KnowledgeGraphEngine().build(
    source_data=case_source,
    discovery_data={
        "recent_discoveries": [],
        "top_discoveries": [],
        "discovery_history": [],
    },
    historical_runs=[],
)
memory_nodes = [
    node for node in graph["nodes"]
    if node["type"] == "Research Memory"
]
strong_relationships = [
    relationship for relationship in graph["relationships"]
    if relationship["type"] == "strongest_analog"
]
weak_relationships = [
    relationship for relationship in graph["relationships"]
    if relationship["type"] == "weakest_analog"
]
assert memory_nodes
assert strong_relationships
assert weak_relationships
assert memory_nodes[0]["properties"]["recurring_patterns"]
assert memory_nodes[0]["properties"]["recurring_failures"]

observatory = PerformanceObservatory().generate(
    source_data=source_data,
    discovery_data={
        "recent_discoveries": [],
        "top_discoveries": [],
        "discovery_history": [],
    },
)
memory_summary = observatory["research_memory_summary"]
assert memory_summary["case_count"] == 3
assert memory_summary["analog_success_rate"] > 0
assert memory_summary["similarity_score_calibration"]["sample_size"] > 0
assert memory_summary["pattern_frequency"]["evidence"][0]["pattern"] == "Forecast"

discoveries = DiscoveryEngine().analyze(
    source_data=source_data,
    discovery_date="2026-06-30T16:05:00",
)
descriptions = [item["description"] for item in discoveries]
assert (
    "High committee agreement and strong fundamentals frequently resemble successful historical cases."
    in descriptions
)
assert "Technology earnings setups are often similar during Bull markets." in descriptions

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    setup_database()
    save_case_studies([case])

    api_result = research_memory_dashboard(ticker="AAPL")
    assert api_result["target"]["ticker"] == "AAPL"
    assert api_result["similar_historical_cases"]
    assert api_result["policy"]["automatic_execution"] is False
finally:
    connection.DATABASE_PATH = original_database_path
    if os.path.exists(database_path):
        os.remove(database_path)

print("ResearchMemoryEngine test passed.")
