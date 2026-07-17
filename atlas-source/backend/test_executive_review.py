import tempfile

import database.connection as connection
from database.repository import get_recommendations_for_run, save_recommendations
from database.setup import setup_database
from engines.executive_review_engine import ExecutiveReviewEngine
from engines.performance_observatory import PerformanceObservatory
from engines.recommendation_engine import RecommendationEngine
from engines.research_engine import ResearchEngine
from models.investment_recommendation import InvestmentRecommendation


recommendation = InvestmentRecommendation(
    ticker="AAPL",
    action="BUY",
    confidence=82,
    reasons=["Bullish technical trend"],
    risks=[],
    score=5,
    technical_score=88,
    fundamental_score=72,
    portfolio_score=64,
    risk_score=70,
    forecast_score=68,
    forecast_direction="UP",
    forecast_confidence=70,
    news_confidence=62,
    headline_count=4,
    overall_conviction=75,
    committee_agreement=82,
)
recommendation.evidence_breakdown = [
    {"category": "Technical", "score": 88, "confidence": 90},
    {"category": "Fundamental", "score": 72, "confidence": 70},
    {"category": "Forecast", "score": 68, "confidence": 65},
    {"category": "News", "score": 62, "confidence": 62},
    {"category": "Portfolio", "score": 64, "confidence": 64},
    {"category": "Risk", "score": 70, "confidence": 70},
]
recommendation.confidence_metadata = [
    {"confidence": 90},
    {"confidence": 70},
    {"confidence": 65},
    {"confidence": 62},
    {"confidence": 64},
    {"confidence": 70},
]
recommendation.recommendation_flip_conditions = [
    "No single deterministic counterfactual crosses an action threshold."
]

original_action = recommendation.action
review = ExecutiveReviewEngine().review(
    recommendation,
    historical_recommendations=[
        {
            "ticker": "AAPL",
            "action": "BUY",
            "validation_result": {"success": True},
        }
    ],
)

assert recommendation.action == original_action
assert review["executive_status"] == "READY"
assert review["executive_confidence"] >= 70
assert review["executive_warnings"] == []
assert "Evidence Completeness" in review["executive_strengths"]
assert review["controlled_decision"].startswith("Executive review")

recommendation.executive_review = review
recommendation.executive_status = review["executive_status"]
recommendation.executive_confidence = review["executive_confidence"]
recommendation.executive_summary = review["executive_summary"]
recommendation.executive_warnings = review["executive_warnings"]
recommendation.executive_strengths = review["executive_strengths"]
recommendation.executive_weaknesses = review["executive_weaknesses"]
recommendation.required_follow_up_research = (
    review["required_follow_up_research"]
)

caution = InvestmentRecommendation(
    ticker="TSLA",
    action="HOLD",
    confidence=48,
    score=2,
    committee_agreement=35,
    forecast_direction="",
    headline_count=0,
    fundamental_score=0,
)
caution.evidence_breakdown = [
    {"category": "Technical", "score": 42, "confidence": 45},
]
caution_review = ExecutiveReviewEngine().review(caution)

assert caution.action == "HOLD"
assert caution_review["executive_status"] == "INSUFFICIENT_DATA"
assert caution_review["executive_warnings"]
assert caution_review["required_follow_up_research"]

RecommendationEngine()._attach_executive_review(caution)
assert caution.executive_review
assert caution.executive_status == "INSUFFICIENT_DATA"
assert caution.action == "HOLD"

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(suffix=".db") as database_file:
    connection.DATABASE_PATH = database_file.name
    setup_database()
    save_recommendations(1, [recommendation])
    saved = get_recommendations_for_run(1)[0]

    assert saved["executive_review"] == recommendation.executive_review
    assert saved["executive_status"] == "READY"
    assert saved["executive_confidence"] == recommendation.executive_confidence
    assert saved["executive_summary"] == recommendation.executive_summary
    assert saved["executive_warnings"] == recommendation.executive_warnings
    assert saved["executive_strengths"] == recommendation.executive_strengths
    assert saved["executive_weaknesses"] == recommendation.executive_weaknesses
    assert (
        saved["required_follow_up_research"]
        == recommendation.required_follow_up_research
    )

connection.DATABASE_PATH = original_database_path

observatory_report = PerformanceObservatory().generate(source_data={
    "recommendations": [
        {
            "action": "BUY",
            "confidence": 82,
            "committee_agreement": 82,
            "executive_status": "READY",
            "executive_warnings": [],
            "validation_result": {"success": True, "percentage_return": 5},
            "evidence_breakdown": recommendation.evidence_breakdown,
        },
        {
            "action": "HOLD",
            "confidence": 48,
            "committee_agreement": 35,
            "executive_status": "INSUFFICIENT_DATA",
            "executive_warnings": caution_review["executive_warnings"],
            "validation_result": {"success": False, "percentage_return": -3},
            "evidence_breakdown": caution.evidence_breakdown,
        },
    ],
    "benchmark_results": [],
    "provider_results": [],
    "research_experiments": [],
}, discovery_data={
    "recent_discoveries": [],
    "top_discoveries": [],
    "discovery_history": [],
})
metrics = observatory_report["platform_metrics"]

assert metrics["executive_approval_rate"] == 50
assert metrics["executive_warning_frequency"] > 0
assert metrics["readiness_distribution"] == {
    "READY": 1,
    "INSUFFICIENT_DATA": 1,
}
assert metrics["historical_executive_accuracy"] == 100

research = ResearchEngine().analyze_executive_reviews([
    {
        "executive_status": "READY",
        "executive_warnings": ["Committee Agreement requires review."],
        "missing_evidence": ["Risk"],
        "validation_result": {"success": False},
    },
    {
        "executive_status": "NEEDS_REVIEW",
        "executive_warnings": ["Missing Data incomplete: News."],
        "missing_evidence": ["News"],
        "validation_result": {"success": True},
    },
])

assert research["common_warnings"]
assert research["frequent_missing_evidence"] == ["News", "Risk"]
assert research["executive_false_positives"] == 1
assert research["executive_false_negatives"] == 1

print("ExecutiveReviewEngine test passed.")
