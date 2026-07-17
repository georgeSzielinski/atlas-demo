import os
import tempfile

import database.connection as connection
from api.main import probabilities_dashboard
from database.repository import (
    get_discovery_source_data,
    get_probability_reports,
    save_probability_reports,
)
from database.setup import setup_database
from engines.case_study_engine import CaseStudyEngine
from engines.discovery_engine import DiscoveryEngine
from engines.knowledge_graph_engine import KnowledgeGraphEngine
from engines.performance_observatory import PerformanceObservatory
from engines.probability_engine import ProbabilityEngine


history = [
    {
        "id": 1,
        "ticker": "AAPL",
        "action": "BUY",
        "market_regime": "Bull",
        "committee_agreement": 84,
        "executive_status": "READY",
        "knowledge_score": 92,
        "stability_score": 82,
        "evidence_breakdown": [
            {"category": "Technical", "score": 86},
            {"category": "Forecast", "score": 80},
        ],
        "catalysts": [{"event_type": "Earnings"}],
        "validation_result": {
            "success": True,
            "hit": True,
            "percentage_return": 8,
            "holding_period": 30,
        },
    },
    {
        "id": 2,
        "ticker": "MSFT",
        "action": "BUY",
        "market_regime": "Bull",
        "committee_agreement": 80,
        "executive_status": "READY",
        "knowledge_score": 94,
        "stability_score": 84,
        "evidence_breakdown": [
            {"category": "Technical", "score": 82},
            {"category": "Forecast", "score": 78},
        ],
        "catalysts": [{"event_type": "Earnings"}],
        "validation_result": {
            "success": True,
            "hit": True,
            "percentage_return": 6,
            "holding_period": 30,
        },
    },
    {
        "id": 3,
        "ticker": "NVDA",
        "action": "BUY",
        "market_regime": "Bull",
        "committee_agreement": 78,
        "executive_status": "READY",
        "knowledge_score": 91,
        "stability_score": 80,
        "evidence_breakdown": [
            {"category": "Technical", "score": 85},
            {"category": "Forecast", "score": 83},
        ],
        "catalysts": [{"event_type": "Earnings"}],
        "validation_result": {
            "success": True,
            "hit": True,
            "percentage_return": 4,
            "holding_period": 30,
        },
    },
    {
        "id": 4,
        "ticker": "TSLA",
        "action": "BUY",
        "market_regime": "Bull",
        "committee_agreement": 76,
        "executive_status": "READY",
        "knowledge_score": 88,
        "stability_score": 76,
        "evidence_breakdown": [
            {"category": "Technical", "score": 75},
            {"category": "Forecast", "score": 72},
        ],
        "catalysts": [{"event_type": "Product Launch"}],
        "validation_result": {
            "success": False,
            "hit": False,
            "percentage_return": -3,
            "holding_period": 30,
        },
    },
]
target = {
    "id": 99,
    "ticker": "AAPL",
    "action": "BUY",
    "market_regime": "Bull",
    "committee_agreement": 82,
    "executive_status": "READY",
    "knowledge_score": 93,
    "stability_score": 83,
    "evidence_breakdown": [
        {"category": "Technical", "score": 84},
        {"category": "Forecast", "score": 82},
    ],
    "catalysts": [{"event_type": "Earnings"}],
}

engine = ProbabilityEngine()
report = engine.estimate(target, history=history)

assert sum(report["probabilities"].values()) == 100
assert report["probabilities"]["outperformance"] == 75
assert report["probabilities"]["underperformance"] == 25
assert report["expected_outcome"]["expected_return"] == 3.75
assert report["expected_outcome"]["expected_holding_period"] == 30
assert report["expected_outcome"]["best_case"] == 8
assert report["expected_outcome"]["base_case"] == 5.0
assert report["expected_outcome"]["worst_case"] == -3
assert report["confidence_quality"]["sample_size"] == 4
assert report["confidence_quality"]["uncertainty_level"] == "Moderate"
assert report["policy"]["changes_recommendation_behavior"] is False

original_action = target["action"]
target["probability_report"] = report
target["validation_result"] = {
    "success": True,
    "hit": True,
    "percentage_return": 8,
    "holding_period": 30,
}
assert target["action"] == original_action

uncertain_report = engine.estimate(
    {
        "id": 100,
        "ticker": "TSLA",
        "action": "BUY",
        "market_regime": "Bear",
        "knowledge_score": 55,
        "stability_score": 35,
        "catalysts": [{"event_type": "Product Launch"}],
    },
    history=[history[-1]],
)
uncertain = dict(history[-1])
uncertain["probability_report"] = uncertain_report

recommendations = [target, uncertain]
observatory = PerformanceObservatory().generate(
    source_data={
        "recommendations": recommendations,
        "benchmark_results": [],
        "provider_results": [],
        "research_experiments": [],
    },
    discovery_data={
        "recent_discoveries": [],
        "top_discoveries": [],
        "discovery_history": [],
    },
)
probability_summary = observatory["probability_summary"]
assert probability_summary["sample_size"] == 2
assert probability_summary["probability_accuracy"] == 100
assert probability_summary["uncertainty_distribution"]["Moderate"] == 1
assert probability_summary["uncertainty_distribution"]["Very High"] == 1

discoveries = DiscoveryEngine().analyze(
    source_data={
        "recommendations": recommendations,
        "benchmark_results": [],
        "provider_results": [],
        "research_experiments": [],
    },
    discovery_date="2026-06-30T15:00:00",
)
descriptions = [item["description"] for item in discoveries]
assert "High-probability recommendations outperform 100.0% of the time." in descriptions
assert "Recommendations with High uncertainty underperform." in descriptions
assert any(
    description.startswith("Knowledge scores above 90 improve probability calibration")
    for description in descriptions
)

case = CaseStudyEngine().build_case_study(
    target,
    case_date="2026-06-30T15:05:00",
)
assert case["probability_report"]["probabilities"]["outperformance"] == 75

graph = KnowledgeGraphEngine().build(
    source_data={
        "recommendations": recommendations,
        "case_studies": [case],
        "benchmark_results": [],
        "provider_results": [],
        "research_experiments": [],
    },
    discovery_data={
        "recent_discoveries": [],
        "top_discoveries": [],
        "discovery_history": [],
    },
    historical_runs=[],
)
probability_nodes = [
    node for node in graph["nodes"]
    if node["type"] == "Probability"
]
probability_relationships = [
    relationship for relationship in graph["relationships"]
    if relationship["type"] == "estimated_by"
]
assert probability_nodes
assert probability_relationships

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    setup_database()
    stored_report = dict(report)
    stored_report["recommendation_id"] = "99"
    stored_report["report_date"] = "2026-06-30T15:10:00"
    save_probability_reports([stored_report])

    saved = get_probability_reports()
    assert len(saved) == 1
    assert saved[0]["ticker"] == "AAPL"
    assert saved[0]["probabilities"]["outperformance"] == 75

    source = get_discovery_source_data()
    assert source["probability_reports"][0]["ticker"] == "AAPL"

    api_result = probabilities_dashboard()
    assert api_result["probability_reports"][0]["ticker"] == "AAPL"
    assert api_result["policy"]["automatic_execution"] is False
finally:
    connection.DATABASE_PATH = original_database_path
    if os.path.exists(database_path):
        os.remove(database_path)

print("ProbabilityEngine test passed.")
