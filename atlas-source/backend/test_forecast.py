from core.settings import APPROVED_TICKERS, FORECAST_PROVIDER
from engines.forecast_engine import ForecastEngine
from engines.mock_forecast_provider import MockForecastProvider


engine = ForecastEngine()
unknown_engine = ForecastEngine(forecast_provider="invalid")

assert FORECAST_PROVIDER == "mock"
assert isinstance(engine.provider, MockForecastProvider)
assert isinstance(unknown_engine.provider, MockForecastProvider)

for ticker in APPROVED_TICKERS:
    forecast = engine.forecast(ticker)

    print("Ticker:", ticker)
    print("Direction:", forecast["direction"])
    print("Confidence:", forecast["confidence"])
    print("Expected %:", forecast["expected_change"])
    print("Forecast Score:", forecast["forecast_score"])
    print()

print("ForecastEngine test passed.")
