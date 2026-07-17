import os
import tempfile

import database.connection as connection
from api.main import case_studies_dashboard
from database.repository import (
    get_case_studies,
    get_discovery_source_data,
    get_research_dashboard_data,
    save_case_studies,
)
from database.setup import setup_database
from engines.case_study_engine import CaseStudyEngine
from engines.discovery_engine import DiscoveryEngine
from engines.knowledge_graph_engine import KnowledgeGraphEngine
from engines.performance_observatory import PerformanceObservatory
from engines.research_engine import ResearchEngine


recommendations = [
    {
        "id": 1,
        "ticker": "AAPL",
        "action": "BUY",
        "market_regime": "Bull",
        "committee_agreement": 82,
        "main_disagreement": "",
        "final_committee_summary": "Committee aligned.",
        "executive_status": "READY",
        "executive_confidence": 78,
        "executive_warnings": [],
        "knowledge_score": 84,
        "stability_score": 76,
        "evidence_breakdown": [
            {"category": "Technical", "score": 88},
            {"category": "Forecast", "score": 80},
            {"category": "News", "score": 52},
        ],
        "validation_result": {
            "success": True,
            "hit": True,
            "percentage_return": 9.5,
            "holding_period": 30,
            "status": "Succeeded",
            "confidence": 78,
        },
        "benchmark": {"baseline_return": 3.0},
        "assumptions": ["Bull trend persists."],
        "counterfactuals": [{"scenario": "Trend breaks below 50MA."}],
    },
    {
        "id": 2,
        "ticker": "TSLA",
        "action": "BUY",
        "market_regime": "Bear",
        "committee_agreement": 72,
        "main_disagreement": "Risk disagreed with Forecast.",
        "final_committee_summary": "Committee had material disagreement.",
        "executive_status": "READY",
        "executive_confidence": 75,
        "executive_warnings": ["Risk elevated."],
        "knowledge_score": 62,
        "stability_score": 41,
        "evidence_breakdown": [
            {"category": "Forecast", "score": 82},
            {"category": "News", "score": 76},
            {"category": "Risk", "score": 35},
        ],
        "validation_result": {
            "success": False,
            "hit": False,
            "percentage_return": -7.25,
            "holding_period": 30,
            "status": "Failed",
            "confidence": 75,
        },
        "benchmark": {"baseline_return": -2.0},
        "assumptions": ["Forecast rebound arrives."],
        "counterfactuals": [{"scenario": "News worsens after entry."}],
    },
]

engine = CaseStudyEngine()
cases = engine.build_case_studies(
    recommendations,
    case_date="2026-06-30T12:00:00",
)

assert len(cases) == 2
assert cases[0]["ticker"] == "AAPL"
assert cases[0]["outcome"] == "Win"
assert cases[0]["return"] == 9.5
assert cases[0]["holding_period"] == 30
assert cases[0]["lessons_learned"]["most_useful_evidence"] == "Technical"
assert cases[0]["lessons_learned"]["least_useful_evidence"] == "News"
assert cases[1]["outcome"] == "Loss"
assert cases[1]["lessons_learned"]["unexpected_outcome"] == "High confidence loss"
assert cases[1]["lessons_learned"]["confidence_calibration"] == "Needs review"
assert "Review failed evidence" in cases[1]["lessons_learned"]["future_improvements"][0]

assert engine.filter_cases(cases, "winning") == [cases[0]]
assert engine.filter_cases(cases, "losing") == [cases[1]]
assert engine.filter_cases(cases, "bull_market") == [cases[0]]
assert engine.filter_cases(cases, "bear_market") == [cases[1]]
assert engine.filter_cases(cases, "committee_disagreements") == [cases[1]]
assert engine.filter_cases(cases, "forecast_failures") == [cases[1]]
assert engine.filter_cases(cases, "news_failures") == [cases[1]]

source_data = {
    "recommendations": recommendations,
    "benchmark_results": [{"engine_name": "Benchmark", "metric": "hit_rate"}],
    "provider_results": [
        {
            "provider_type": "forecast",
            "provider_name": "Mock Forecast",
            "status": "Available",
            "score": 70,
            "rank": 1,
        }
    ],
    "research_experiments": [
        {
            "experiment_id": "exp-case",
            "title": "Case Study Experiment",
            "status": "Completed",
        }
    ],
    "case_studies": cases,
}
discovery_data = {
    "discovery_history": [
        {
            "id": "disc-case",
            "title": "Case discovery",
            "description": "Case study discovery.",
        }
    ],
    "recent_discoveries": [],
    "top_discoveries": [],
}
historical_runs = [
    {
        "experiment_id": "hist-case",
        "configuration": {"tickers": ["AAPL", "TSLA"]},
    }
]

graph = KnowledgeGraphEngine().build(
    source_data=source_data,
    discovery_data=discovery_data,
    historical_runs=historical_runs,
)
case_nodes = [node for node in graph["nodes"] if node["type"] == "Case Study"]
case_relationship_types = {
    relationship["type"]
    for relationship in graph["relationships"]
    if relationship["source"].startswith("case_study:")
}

assert len(case_nodes) == 2
assert {
    "summarizes_recommendation",
    "summarizes_validation",
    "informed_by_discovery",
    "informed_by_experiment",
    "historical_analog",
    "references_provider",
} <= case_relationship_types

observatory = PerformanceObservatory().generate(
    source_data=source_data,
    discovery_data=discovery_data,
)
summary = observatory["case_study_summary"]
assert summary["case_count"] == 2
assert summary["best_case"]["ticker"] == "AAPL"
assert summary["worst_case"]["ticker"] == "TSLA"
assert summary["most_educational_case"]["ticker"] == "TSLA"
assert summary["most_similar_cases"]

discoveries = DiscoveryEngine().analyze(
    source_data=source_data,
    discovery_date="2026-06-30T12:05:00",
)
descriptions = [item["description"] for item in discoveries]
assert "AAPL is the strongest validated case study with 9.5% return." in descriptions
assert "TSLA is the weakest validated case study with -7.25% return." in descriptions

filters = ResearchEngine().case_study_filters(cases)
assert filters["winning_cases"] == [cases[0]]
assert filters["losing_cases"] == [cases[1]]
assert filters["committee_disagreements"] == [cases[1]]

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    setup_database()
    save_case_studies(cases)

    saved = get_case_studies()
    assert len(saved) == 2
    assert saved[0]["ticker"] in {"AAPL", "TSLA"}
    assert saved[0]["lessons_learned"]

    dashboard = get_research_dashboard_data()
    assert dashboard["case_studies"]

    research = ResearchEngine().research_dashboard_data()
    assert research["case_study_filters"]["winning_cases"]
    assert research["case_study_filters"]["losing_cases"]

    discovery_source = get_discovery_source_data()
    assert len(discovery_source["case_studies"]) == 2

    api_result = case_studies_dashboard()
    assert len(api_result["case_studies"]) == 2
    assert api_result["case_study_filters"]["forecast_failures"]
finally:
    connection.DATABASE_PATH = original_database_path
    if os.path.exists(database_path):
        os.remove(database_path)

print("CaseStudyEngine test passed.")
