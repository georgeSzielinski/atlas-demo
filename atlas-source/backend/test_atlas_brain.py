import os
import tempfile

import database.connection as connection
from api.main import (
    brain_dashboard,
    brain_evidence_dashboard,
    brain_summary_dashboard,
    brain_timeline_dashboard,
)
from database.setup import setup_database
from engines.performance_analytics_engine import PerformanceAnalyticsEngine
from engines.probability_engine import ProbabilityEngine
from engines.recommendation_engine import RecommendationEngine
from engines.research_engine import ResearchEngine
from engines.research_lab_engine import ResearchLabEngine


# ------------------------------------------------------------------
# Deterministic recommendation fixture (a saved-style recommendation)
# ------------------------------------------------------------------
recommendation = {
    "ticker": "AAPL",
    "action": "BUY",
    "confidence": 84,
    "signal_quality_score": 8,
    "technical_score": 74,
    "fundamental_score": 80,
    "forecast_score": 70,
    "forecast_direction": "Up",
    "forecast_confidence": 68,
    "portfolio_score": 66,
    "risk_score": 71,
    "news_confidence": 45,
    "committee_agreement": 78,
    "final_committee_summary": "Committee is constructive on fundamentals.",
    "executive_status": "READY",
    "executive_confidence": 82,
    "executive_summary": "Executive review is ready.",
    "knowledge_score": 82,
    "stability_score": 76,
    "top_positive_factors": ["Strong fundamentals.", "Constructive trend."],
    "top_negative_factors": ["Macro uncertainty."],
    "evidence_breakdown": [
        {"category": "Fundamentals", "score": 80, "weight": 0.30, "confidence": 82, "summary": "Durable margins."},
        {"category": "Technical", "score": 74, "weight": 0.25, "confidence": 75, "summary": "Uptrend intact."},
        {"category": "Forecast", "score": 70, "weight": 0.15, "confidence": 68, "summary": "Higher forecast."},
        {"category": "News", "score": 45, "weight": 0.10, "confidence": 45, "summary": "Weak news agreement."},
        {"category": "Macro", "score": 52, "weight": 0.08, "confidence": 55, "summary": "Cautious macro."},
        {"category": "Committee", "score": 78, "weight": 0.03, "confidence": 78, "summary": "High agreement."},
    ],
    "catalysts": [
        {"event_type": "Earnings", "days_until_event": 8, "potential_volatility_level": "High"},
        {"event_type": "CPI", "days_until_event": 3, "potential_volatility_level": "Medium"},
    ],
    "probability_report": {
        "ticker": "AAPL",
        "recommendation": "BUY",
        "probabilities": {"outperformance": 60, "market_performance": 26, "underperformance": 14},
        "expected_outcome": {"expected_return": 2.8, "expected_holding_period": 30, "sample_size": 10},
        "confidence_quality": {"uncertainty_level": "Moderate", "sample_size": 10, "similar_historical_cases": []},
        "explanation": "Analogs favor outperformance.",
        "similar_historical_cases": [],
        "policy": {"changes_recommendation_behavior": False, "automatic_execution": False},
    },
}
source_data = {"recommendations": [recommendation], "case_studies": []}

# ------------------------------------------------------------------
# RecommendationEngine.explain (read-only)
# ------------------------------------------------------------------
explanation = RecommendationEngine().explain(recommendation)
contributions = explanation["engine_contributions"]
assert len(contributions) == 6
assert abs(sum(item["percent"] for item in contributions) - 100) < 0.5
assert contributions[0]["category"] == "Fundamentals"  # highest score*weight
assert len(explanation["decision_flow"]) == 15
assert [node["label"] for node in explanation["decision_flow"]][0] == "Market Data"
assert explanation["decision_flow"][-1]["label"] == "Final Recommendation"
assert len(explanation["decision_tree"]["branches"]) == 5
assert explanation["decision_tree"]["final_outcome"] == "BUY"
breakdown = explanation["confidence_breakdown"]
assert any("fundamentals" in item["factor"].lower() for item in breakdown["raised"])
assert any("news" in item["factor"].lower() for item in breakdown["reduced"])
assert any("earnings" in item["factor"].lower() for item in breakdown["reduced"])
assert explanation["policy"]["changes_recommendation_behavior"] is False

# ------------------------------------------------------------------
# ProbabilityEngine.explain reuses the report (no recompute of logic)
# ------------------------------------------------------------------
probability_detail = ProbabilityEngine().explain(
    report=recommendation["probability_report"]
)
assert probability_detail["outperformance_probability"] == 60
assert probability_detail["most_likely_outcome"] == "outperformance"
assert probability_detail["uncertainty_level"] == "Moderate"
assert probability_detail["policy"]["changes_recommendation_behavior"] is False

# Empty report is graceful.
empty_probability = ProbabilityEngine().explain(report={})
assert empty_probability["outperformance_probability"] == 0
assert empty_probability["most_likely_outcome"] == "unavailable"

# ------------------------------------------------------------------
# Trust indicators (Part 9) reuse existing systems
# ------------------------------------------------------------------
trust = PerformanceAnalyticsEngine().trust_indicators(
    recommendation=recommendation,
    source_data=source_data,
    validations=[
        {"adoption_decision": "ADOPT", "scientific_result": "Improved"},
    ],
    experiments=ResearchLabEngine().default_experiments(),
)
assert set(trust.keys()) >= {
    "validation_status",
    "experiment_status",
    "probability_calibration",
    "data_provider_health",
    "market_freshness",
    "research_confidence",
}
assert trust["research_confidence"]["label"] in {"High", "Moderate", "Developing", "Insufficient"}
assert trust["data_provider_health"]["active_provider"] == "mock"
assert trust["policy"]["broker_integration"] is False

# ------------------------------------------------------------------
# brain_report - available path (saved recommendation)
# ------------------------------------------------------------------
report = ResearchEngine().brain_report("AAPL", source_data=source_data)
assert report["available"] is True
assert report["demo_data"] is False
assert report["overview"]["recommendation"] == "BUY"
assert report["overview"]["confidence"] == 84
assert report["overview"]["probability"] == 60
assert report["overview"]["knowledge_score"] == 82
assert report["overview"]["executive_review"] == "READY"
assert report["overview"]["committee_decision"]["agreement"] == 78
assert len(report["decision_flow"]) == 15
assert report["evidence_contribution"]["top_category"] == "Fundamentals"
assert len(report["timeline"]) == 7
assert report["catalyst_impact"]["event_count"] == 2
assert report["catalyst_impact"]["most_important"]["event_type"] == "CPI"  # nearest event
assert "allocation" in report["portfolio_impact"]
assert report["policy"]["changes_recommendation_behavior"] is False
assert report["policy"]["changes_probabilities"] is False
assert report["policy"]["changes_portfolio_construction"] is False
assert report["policy"]["broker_integration"] is False

# Slices are consistent with the full report.
summary = ResearchEngine().brain_summary("AAPL", source_data=source_data)
assert summary["overview"]["recommendation"] == "BUY"
assert "trust_indicators" in summary
evidence = ResearchEngine().brain_evidence("AAPL", source_data=source_data)
assert evidence["evidence_contribution"]["top_category"] == "Fundamentals"
timeline = ResearchEngine().brain_timeline("AAPL", source_data=source_data)
assert len(timeline["timeline"]) == 7
assert len(timeline["decision_flow"]) == 15

# ------------------------------------------------------------------
# brain_report - demo fallback for an unknown ticker (never crash)
# ------------------------------------------------------------------
demo_report = ResearchEngine().brain_report("ZZZZ", source_data=source_data)
assert demo_report["available"] is False
assert demo_report["demo_data"] is True
assert demo_report["overview"]["recommendation"] == "BUY"
assert len(demo_report["decision_flow"]) == 15
assert demo_report["policy"]["broker_integration"] is False

# ------------------------------------------------------------------
# API endpoints against an empty database (graceful demo fallback)
# ------------------------------------------------------------------
original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    setup_database()

    api_report = brain_dashboard("AAPL")
    assert api_report["ticker"] == "AAPL"
    assert api_report["demo_data"] is True  # empty DB -> deterministic example
    assert len(api_report["decision_flow"]) == 15
    assert api_report["policy"]["changes_recommendation_behavior"] is False

    api_summary = brain_summary_dashboard("AAPL")
    assert "overview" in api_summary
    assert "trust_indicators" in api_summary

    api_evidence = brain_evidence_dashboard("AAPL")
    assert "evidence_contribution" in api_evidence
    assert abs(
        sum(item["percent"] for item in api_evidence["engine_contributions"]) - 100
    ) < 0.5

    api_timeline = brain_timeline_dashboard("AAPL")
    assert len(api_timeline["timeline"]) == 7
    assert len(api_timeline["decision_flow"]) == 15
finally:
    connection.DATABASE_PATH = original_database_path
    if os.path.exists(database_path):
        os.remove(database_path)

print("AtlasBrain test passed.")
