import tempfile

import database.connection as connection
from database.repository import get_recommendations_for_run, save_recommendations
from database.setup import setup_database
from engines.hypothesis_engine import HypothesisEngine
from engines.recommendation_engine import RecommendationEngine
from engines.research_engine import ResearchEngine
from models.investment_recommendation import InvestmentRecommendation
from models.stock_analysis import StockAnalysis


recommendation = InvestmentRecommendation(
    ticker="AAPL",
    action="BUY",
    confidence=86,
    reasons=["Bullish technical trend"],
    risks=[],
    score=5,
    technical_score=88,
    fundamental_score=72,
    portfolio_score=60,
    risk_score=70,
    forecast_score=64,
    news_confidence=45,
    overall_conviction=74,
)
recommendation.evidence_breakdown = [
    {
        "name": "Technical",
        "score": 88,
        "confidence": 90,
        "weight": 0.25,
        "reason": "Technical evidence supports the recommendation.",
    },
    {
        "name": "Fundamental",
        "score": 72,
        "confidence": 70,
        "weight": 0.2,
        "reason": "Fundamental evidence supports the recommendation.",
    },
    {
        "name": "Forecast",
        "score": 64,
        "confidence": 64,
        "weight": 0.2,
        "reason": "Forecast evidence supports the recommendation.",
    },
    {
        "name": "News",
        "score": 45,
        "confidence": 45,
        "weight": 0.1,
        "reason": "News evidence is a weaker input.",
    },
    {
        "name": "Portfolio",
        "score": 60,
        "confidence": 60,
        "weight": 0.1,
        "reason": "Portfolio evidence is mixed.",
    },
    {
        "name": "Risk",
        "score": 70,
        "confidence": 70,
        "weight": 0.1,
        "reason": "Risk evidence supports the recommendation.",
    },
]

original_action = recommendation.action
hypothesis = HypothesisEngine().generate(recommendation)

assert recommendation.action == original_action
assert hypothesis["key_assumptions"]
assert hypothesis["weakest_assumption"].startswith("Atlas is vulnerable")
assert len(hypothesis["counterfactuals"]) == 5
assert hypothesis["counterfactuals"][0]["scenario"] == (
    "If technical score falls"
)
assert hypothesis["confidence_drivers"][0]["source"] == "Technical"
assert hypothesis["recommendation_flip_conditions"]

recommendation.assumptions = (
    hypothesis["key_assumptions"]
    + hypothesis["supporting_assumptions"]
    + hypothesis["weakest_assumptions"]
)
recommendation.strongest_assumption = hypothesis["strongest_assumption"]
recommendation.weakest_assumption = hypothesis["weakest_assumption"]
recommendation.counterfactuals = hypothesis["counterfactuals"]
recommendation.recommendation_flip_conditions = (
    hypothesis["recommendation_flip_conditions"]
)
recommendation.confidence_drivers = hypothesis["confidence_drivers"]

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(suffix=".db") as database_file:
    connection.DATABASE_PATH = database_file.name
    setup_database()
    save_recommendations(1, [recommendation])
    saved = get_recommendations_for_run(1)[0]

    assert saved["assumptions"] == recommendation.assumptions
    assert saved["strongest_assumption"] == recommendation.strongest_assumption
    assert saved["weakest_assumption"] == recommendation.weakest_assumption
    assert saved["counterfactuals"] == recommendation.counterfactuals
    assert (
        saved["recommendation_flip_conditions"]
        == recommendation.recommendation_flip_conditions
    )
    assert saved["confidence_drivers"] == recommendation.confidence_drivers

connection.DATABASE_PATH = original_database_path

stock = StockAnalysis(
    ticker="MSFT",
    asset_type="Stock",
    price=300,
    week_return=2,
    month_return=4,
    moving_average_20=295,
    moving_average_50=290,
    price_vs_20ma=2,
    price_vs_50ma=3,
    rsi=55,
    macd=1.1,
    macd_signal=0.9,
    macd_trend="Bullish",
    volatility=1.0,
    trend="Bullish",
    score=5,
)
integrated = RecommendationEngine().build_recommendations([stock])[0]

assert integrated.assumptions
assert integrated.strongest_assumption
assert integrated.weakest_assumption
assert integrated.counterfactuals
assert integrated.recommendation_flip_conditions
assert integrated.confidence_drivers
assert integrated.action in {"BUY", "HOLD", "AVOID"}

analysis = ResearchEngine().analyze_hypotheses([
    {
        "assumptions": integrated.assumptions,
        "counterfactuals": integrated.counterfactuals,
        "validation_result": {"success": True},
    },
    {
        "assumptions": recommendation.assumptions,
        "counterfactuals": recommendation.counterfactuals,
        "validation_result": {"success": False},
    },
])

assert analysis["highest_accuracy_assumptions"]
assert analysis["failed_assumptions"]
assert analysis["frequent_counterfactuals"][0] == "If forecast improves"

print("HypothesisEngine test passed.")
