from datetime import date, timedelta

from core.settings import FORECAST_PROVIDER
from engines.forecast_engine import ForecastEngine
from engines.kronos_forecast_provider import (
    KronosForecastProvider,
    KronosUnavailableError,
)
from engines.mock_forecast_provider import MockForecastProvider


provider = KronosForecastProvider()
history = [
    {
        "date": (date(2026, 1, 1) + timedelta(days=day)).isoformat(),
        "open": 100.0,
        "high": 105.0,
        "low": 99.0,
        "close": 102.0,
        "volume": 1000,
    }
    for day in range(60)
]
payload = provider._to_kronos_payload({"history": history})
dataframe = payload["dataframe"]
kronos_dataframe = provider._to_kronos_dataframe(dataframe)

assert list(dataframe.keys()) == [
    "timestamps",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
]
assert len(dataframe["timestamps"]) == 60
assert dataframe["timestamps"][0] == "2026-01-01"
assert dataframe["amount"][0] == 102000.0
assert list(kronos_dataframe.columns) == [
    "timestamps",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
]

try:
    provider._to_kronos_payload({"history": list(reversed(history))})
except ValueError as error:
    assert "timestamps" in str(error)
else:
    raise AssertionError("Unsorted timestamps should be rejected.")

invalid_history = [dict(row) for row in history]
invalid_history[0]["close"] = "102"

try:
    provider._to_kronos_payload({"history": invalid_history})
except ValueError as error:
    assert "numeric" in str(error)
else:
    raise AssertionError("Non-numeric OHLCV values should be rejected.")

try:
    prediction = provider._run_temporary_kronos_prediction(kronos_dataframe)
except Exception as error:
    print(f"Kronos prediction error: {type(error).__name__}: {error}")
else:
    print(f"Kronos prediction shape: {prediction.shape}")
    print("Kronos prediction head:")
    print(prediction.head())

bullish_forecast = provider._score_prediction(
    historical_close=[100.0],
    predicted_close=[102.0, 104.0]
)
bearish_forecast = provider._score_prediction(
    historical_close=[100.0],
    predicted_close=[99.0, 96.0]
)
neutral_forecast = provider._score_prediction(
    historical_close=[100.0],
    predicted_close=[100.4]
)

assert bullish_forecast["direction"] == "Bullish"
assert bullish_forecast["expected_change"] == 4.0
assert bullish_forecast["forecast_score"] > 50
assert 1 <= bullish_forecast["confidence"] <= 99
assert bullish_forecast["days"] == 2

assert bearish_forecast["direction"] == "Bearish"
assert bearish_forecast["expected_change"] == -4.0
assert bearish_forecast["forecast_score"] < 50
assert 1 <= bearish_forecast["confidence"] <= 99

assert neutral_forecast["direction"] == "Neutral"
assert neutral_forecast["forecast_score"] == 50
assert 1 <= neutral_forecast["confidence"] <= 99

try:
    unavailable_provider = KronosForecastProvider(repo_path="/missing/kronos")
    unavailable_provider.forecast({"ticker": "AAPL", "history": history})
except KronosUnavailableError as error:
    print(error)
else:
    raise AssertionError("Missing Kronos repo path should be unavailable.")

default_engine = ForecastEngine()
kronos_engine = ForecastEngine(forecast_provider="kronos")
unknown_engine = ForecastEngine(forecast_provider="unknown")
forced_unavailable_engine = ForecastEngine(provider=unavailable_provider)
forced_unavailable_forecast = forced_unavailable_engine.forecast("AAPL")

assert FORECAST_PROVIDER == "mock"
assert isinstance(default_engine.provider, MockForecastProvider)
assert isinstance(unknown_engine.provider, MockForecastProvider)
assert forced_unavailable_forecast["direction"] == "Bullish"
assert forced_unavailable_forecast["forecast_score"] > 50
assert KronosForecastProvider.is_available(repo_path="/missing/kronos") is False

if not KronosForecastProvider.is_available():
    assert isinstance(kronos_engine.provider, MockForecastProvider)

print("Kronos optional provider test passed.")
