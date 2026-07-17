from engines.confidence_engine import ConfidenceEngine
from engines.evidence_engine import EvidenceEngine
from models.investment_recommendation import InvestmentRecommendation


engine = ConfidenceEngine()
metadata = engine.calibrate({"name": "Technical", "score": 85})

assert set(metadata.keys()) == {
    "confidence",
    "reliability_label",
    "explanation",
}
assert metadata["reliability_label"] in ("Low", "Medium", "High")
assert metadata["confidence"] >= 0
assert metadata["explanation"]

recommendation = InvestmentRecommendation(
    ticker="AAPL",
    action="BUY",
    confidence=80,
    technical_score=85,
    fundamental_score=70,
    forecast_score=65,
    news_confidence=50,
    portfolio_score=75,
    risk_score=80,
    signal_quality_score=8,
)

evidence = EvidenceEngine().build(recommendation)

for item in evidence:
    assert "confidence_metadata" in item
    assert item["confidence_metadata"]["reliability_label"] in (
        "Low",
        "Medium",
        "High",
    )

print("ConfidenceEngine test passed.")
