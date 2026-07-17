from engines.intelligence_fusion_engine import IntelligenceFusionEngine
from engines.recommendation_engine import RecommendationEngine
import database.connection as connection
from database.repository import get_recommendations_for_run, save_recommendations
from database.setup import setup_database
from models.stock_analysis import StockAnalysis
import tempfile


engine = IntelligenceFusionEngine()
result = engine.fuse(
    technical=80,
    fundamentals={"score": 90},
    forecast={"forecast_score": 40},
    news={"confidence": 20},
    portfolio=75,
    risk=65,
    evidence=[
        {"name": "Technical", "score": 80},
        {"name": "Forecast", "score": 40},
    ],
    confidence=[
        {"confidence": 85},
        {"confidence": 45},
    ],
)

assert result["overall_conviction"] == 64.45
assert result["strongest_positive_factor"] == {
    "name": "fundamentals",
    "score": 90,
}
assert result["strongest_negative_factor"] == {
    "name": "news",
    "score": 20,
}
assert len(result["conflicting_signals"]) == 6
assert result["missing_inputs"] == []
assert result["confidence_breakdown"]
assert result["evidence_weighting_table"]
assert result["engine_contribution_percentages"]["technical"] == 20
assert result["strongest_agreement"] == (
    "technical, fundamentals, portfolio agree positively."
)
assert "news is weakest" in result["strongest_disagreement"]
assert result["uncertainty_score"] == 52
assert "Fusion supports a measured or neutral thesis" in (
    result["recommendation_rationale"]
)
assert "Fusion conviction is 64.45/100." in result["fusion_summary"]

missing_result = engine.fuse(technical=70)

assert missing_result["overall_conviction"] == 70
assert "fundamentals" in missing_result["missing_inputs"]
assert "Missing inputs" in missing_result["fusion_summary"]

recommendation_engine = RecommendationEngine()
recommendations = recommendation_engine.build_recommendations([
    StockAnalysis(
        ticker="AAPL",
        asset_type="Stock",
        price=100,
        week_return=5,
        month_return=10,
        moving_average_20=95,
        moving_average_50=90,
        price_vs_20ma=5,
        price_vs_50ma=10,
        rsi=55,
        macd=1,
        macd_signal=0.5,
        macd_trend="Bullish",
        volatility=12,
        trend="Bullish",
        score=4,
    )
])
recommendation = recommendations[0]

assert recommendation.fusion
assert recommendation.overall_conviction > 0
assert recommendation.fusion_summary
assert recommendation.fusion["missing_inputs"] == []
assert recommendation.top_positive_factors
assert recommendation.suggested_follow_up_research
assert recommendation.confidence_explanation
assert recommendation.evidence_summary
assert recommendation.investment_committee
assert recommendation.committee_members
assert recommendation.final_committee_summary

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(suffix=".db") as database_file:
    connection.DATABASE_PATH = database_file.name
    setup_database()
    save_recommendations(1, [recommendation])
    saved = get_recommendations_for_run(1)[0]

    assert saved["overall_conviction"] == recommendation.overall_conviction
    assert saved["bull_case"] == recommendation.fusion["bull_case"]
    assert saved["bear_case"] == recommendation.fusion["bear_case"]
    assert saved["neutral_case"] == recommendation.fusion["neutral_case"]
    assert (
        saved["strongest_positive_factor"]
        == recommendation.fusion["strongest_positive_factor"]
    )
    assert (
        saved["strongest_negative_factor"]
        == recommendation.fusion["strongest_negative_factor"]
    )
    assert (
        saved["conflicting_signals"]
        == recommendation.fusion["conflicting_signals"]
    )
    assert saved["missing_inputs"] == recommendation.fusion["missing_inputs"]
    assert saved["fusion_summary"] == recommendation.fusion_summary
    assert saved["top_positive_factors"] == recommendation.top_positive_factors
    assert saved["top_negative_factors"] == recommendation.top_negative_factors
    assert saved["missing_evidence"] == recommendation.missing_evidence
    assert (
        saved["suggested_follow_up_research"]
        == recommendation.suggested_follow_up_research
    )
    assert (
        saved["confidence_explanation"]
        == recommendation.confidence_explanation
    )
    assert saved["evidence_summary"] == recommendation.evidence_summary
    assert saved["committee_members"] == recommendation.committee_members
    assert saved["committee_bull_case"] == recommendation.committee_bull_case
    assert saved["committee_bear_case"] == recommendation.committee_bear_case
    assert saved["committee_agreement"] == recommendation.committee_agreement
    assert saved["bullish_members"] == recommendation.bullish_members
    assert saved["bearish_members"] == recommendation.bearish_members
    assert (
        saved["final_committee_summary"]
        == recommendation.final_committee_summary
    )

connection.DATABASE_PATH = original_database_path

print("IntelligenceFusionEngine test passed.")
