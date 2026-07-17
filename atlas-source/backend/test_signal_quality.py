from engines.signal_quality_engine import SignalQualityEngine


engine = SignalQualityEngine()

strong = engine.evaluate(
    technical_score=90,
    fundamental_score=85,
    forecast_score=88,
    news_confidence=75,
    risk_score=90,
    volatility=8
)

assert strong["signal_quality_score"] >= 8
assert strong["signal_label"] in ("Strong", "High Conviction")
assert strong["false_positive_warnings"] == []

weak = engine.evaluate(
    technical_score=25,
    fundamental_score=40,
    forecast_score=30,
    news_confidence=0,
    risk_score=35,
    volatility=55
)

assert weak["signal_quality_score"] < 5
assert weak["signal_label"] == "Weak"
assert weak["false_positive_warnings"]

print("SignalQualityEngine test passed.")
