from core.settings import APPROVED_TICKERS
from engines.forecast_engine import ForecastEngine


engine = ForecastEngine()
provider_name = engine.provider.__class__.__name__

for ticker in APPROVED_TICKERS:
    forecast = engine.forecast(ticker)

    print("Ticker:", ticker)
    print("Provider:", provider_name)
    print("Direction:", forecast["direction"])
    print("Confidence:", forecast["confidence"])
    print("Expected Change:", forecast["expected_change"])
    print("Forecast Score:", forecast["forecast_score"])
    print()
