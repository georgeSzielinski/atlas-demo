from engines.recommendation_engine import RecommendationEngine
from models.investment_recommendation import InvestmentRecommendation
from models.stock_analysis import StockAnalysis


stock = StockAnalysis(
    ticker="AAPL",
    asset_type="Stock",
    price=280,
    week_return=2,
    month_return=5,
    moving_average_20=275,
    moving_average_50=270,
    price_vs_20ma=2,
    price_vs_50ma=4,
    rsi=55,
    macd=1.2,
    macd_signal=1.0,
    macd_trend="Bullish",
    volatility=1.3,
    trend="Bullish",
    score=5,
)

engine = RecommendationEngine()
recommendation = engine.build_recommendations([stock])[0]

assert recommendation.ticker == "AAPL"
assert recommendation.action in {"BUY", "HOLD", "AVOID"}
assert recommendation.confidence > 0
assert recommendation.evidence_breakdown
assert recommendation.fusion
assert recommendation.top_positive_factors
assert recommendation.suggested_follow_up_research
assert recommendation.confidence_explanation
assert recommendation.evidence_summary
assert recommendation.stability_score > 0
assert recommendation.stability_level
assert recommendation.most_sensitive_factor
assert recommendation.stability_explanation
assert recommendation.knowledge_score > 0
assert recommendation.knowledge_level
assert recommendation.knowledge_explanation


def evidence_rows():
    return [
        {"category": "Technical", "name": "Technical", "score": 90},
        {"category": "Fundamental", "name": "Fundamental", "score": 88},
        {"category": "Forecast", "name": "Forecast", "score": 86},
        {"category": "News", "name": "News", "score": 84},
        {"category": "Risk", "name": "Risk", "score": 82},
        {"category": "Benchmark", "name": "Benchmark", "score": 80},
    ]


stable = InvestmentRecommendation(
    ticker="STABLE",
    action="BUY",
    confidence=92,
)
stable.technical_score = 91
stable.fundamental_score = 89
stable.forecast_confidence = 88
stable.news_confidence = 86
stable.portfolio_score = 84
stable.risk_score = 90
stable.committee_agreement = 87
stable.executive_confidence = 91
stable.executive_status = "READY"
stable.validation_status = "Validated"
stable.evidence_breakdown = evidence_rows()
stable.similar_historical_recommendations = [{"ticker": "A"}, {"ticker": "B"}]
stable.discovery_support = ["Repeated high-quality setup."]
stable_action = stable.action
engine._attach_stability_and_knowledge(stable)

assert stable.action == stable_action
assert stable.stability_score >= 85
assert stable.stability_level == "Very Stable"
assert stable.knowledge_score >= 85
assert stable.knowledge_level == "Deep Knowledge"

fragile = InvestmentRecommendation(
    ticker="FRAGILE",
    action="HOLD",
    confidence=55,
)
fragile.technical_score = 0
fragile.fundamental_score = 0
fragile.forecast_confidence = 0
fragile.news_confidence = 0
fragile.portfolio_score = 0
fragile.risk_score = 10
fragile.committee_agreement = 10
fragile.executive_confidence = 0
fragile.executive_status = "INSUFFICIENT_DATA"
fragile.missing_evidence = [
    "Forecast unavailable.",
    "News unavailable.",
    "Validation history unavailable.",
]
fragile.evidence_breakdown = [
    {"category": "Technical", "name": "Technical", "score": 25}
]
fragile_action = fragile.action
engine._attach_stability_and_knowledge(fragile)

assert fragile.action == fragile_action
assert fragile.stability_score < stable.stability_score
assert fragile.stability_score <= 40
assert fragile.stability_level in {"Fragile", "Highly Fragile"}
assert fragile.knowledge_score < stable.knowledge_score
assert fragile.knowledge_level in {
    "Low Knowledge",
    "Insufficient Knowledge",
}

print("RecommendationEngine test passed.")
