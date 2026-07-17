import builtins

import pandas as pd

from core.settings import (
    DATA_PROVIDER,
    HISTORICAL_DATA_PROVIDER,
    SUPPORTED_HISTORICAL_DATA_PROVIDERS,
)
from api.main import _data_provider_health
from market.data import (
    HistoricalDataProviderFactory,
    data_provider_health,
    get_data_provider,
    get_historical_data_adapter,
    get_market_data,
    historical_data_provider_health,
)
from market.mock_historical_data_adapter import MockHistoricalDataAdapter
from market.mock_data_provider import MockDataProvider
from market.yahoo_historical_data_adapter import YahooHistoricalDataAdapter
from market.yahoo_data_provider import YahooDataProvider


mock_provider = MockDataProvider()
mock_history = mock_provider.get_price_history("AAPL")

assert DATA_PROVIDER == "mock"
assert HISTORICAL_DATA_PROVIDER == "mock"
assert {"mock", "yahoo", "polygon", "alpha_vantage", "csv", "parquet"} <= set(
    SUPPORTED_HISTORICAL_DATA_PROVIDERS
)
assert not mock_history.empty
assert len(mock_history) >= 50
assert mock_provider.get_latest_price("AAPL") == mock_history["Close"].iloc[-1]
assert "AAPL" in mock_provider.get_supported_tickers()

invalid_provider = get_data_provider("invalid")

assert isinstance(invalid_provider, MockDataProvider)

health = data_provider_health()

assert health["active_provider"] == "mock"
assert health["supported_tickers_count"] > 0
assert health["latest_price_available"] is True
assert health["healthy"] is True
assert health["failure_message"] == ""

invalid_health = data_provider_health(provider_name="invalid")

assert invalid_health["active_provider"] == "mock"
assert invalid_health["latest_price_available"] is True
assert invalid_health["healthy"] is True

historical_adapter = get_historical_data_adapter()
historical_rows = historical_adapter.get_ohlcv(
    ["AAPL"],
    "2024-01-01",
    "2024-01-05",
)
repeat_historical_rows = historical_adapter.get_ohlcv(
    ["AAPL"],
    "2024-01-01",
    "2024-01-05",
)
invalid_historical_adapter = get_historical_data_adapter("invalid")
future_historical_adapter = get_historical_data_adapter("polygon")
yahoo_historical_adapter = get_historical_data_adapter("yahoo")
historical_health = historical_data_provider_health()

assert isinstance(historical_adapter, MockHistoricalDataAdapter)
assert isinstance(invalid_historical_adapter, MockHistoricalDataAdapter)
assert isinstance(future_historical_adapter, MockHistoricalDataAdapter)
assert isinstance(yahoo_historical_adapter, YahooHistoricalDataAdapter)
assert isinstance(
    HistoricalDataProviderFactory.create("alpha_vantage"),
    MockHistoricalDataAdapter,
)
assert historical_rows == repeat_historical_rows
assert len(historical_rows) == 5
assert historical_rows == sorted(
    historical_rows,
    key=lambda row: (row["date"], row["ticker"]),
)
assert {"date", "ticker", "open", "high", "low", "close", "volume"} <= set(
    historical_rows[0]
)
assert historical_health["active_provider"] == "mock"
assert historical_health["requested_provider"] == "mock"
assert historical_health["rows_available"] == 5
assert historical_health["date_range"] == {
    "start_date": "2024-01-01",
    "end_date": "2024-01-05",
}
assert historical_health["healthy"] is True
assert historical_health["fallback_used"] is False
assert historical_health["failure_message"] == ""

real_yahoo_adapter = YahooHistoricalDataAdapter()
yahoo_real_import = builtins.__import__


class FakeYahooTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    def history(self, start, end, auto_adjust=False):
        return pd.DataFrame(
            {
                "Open": [100.123, 101.234, 102.345],
                "High": [101.123, 102.234, 103.345],
                "Low": [99.123, 100.234, 101.345],
                "Close": [100.789, 101.789, 102.789],
                "Volume": [1000, 1100, 1200],
            },
            index=pd.to_datetime([
                "2024-01-01",
                "2024-01-02",
                "2024-01-03",
            ]),
        )


class FakeYahooModule:
    Ticker = FakeYahooTicker


def available_yfinance(name, *args, **kwargs):
    if name == "yfinance":
        return FakeYahooModule()

    return yahoo_real_import(name, *args, **kwargs)


builtins.__import__ = available_yfinance

try:
    real_yahoo_rows = real_yahoo_adapter.get_ohlcv(
        ["AAPL"],
        "2024-01-01",
        "2024-01-04",
    )
    real_yahoo_health = historical_data_provider_health("yahoo")
finally:
    builtins.__import__ = yahoo_real_import

assert real_yahoo_adapter.fallback_used is False
assert real_yahoo_adapter.last_error == ""
assert len(real_yahoo_rows) == 3
assert real_yahoo_rows == sorted(
    real_yahoo_rows,
    key=lambda row: (row["date"], row["ticker"]),
)
assert real_yahoo_rows[0] == {
    "date": "2024-01-01",
    "timestamp": "2024-01-01",
    "ticker": "AAPL",
    "open": 100.12,
    "high": 101.12,
    "low": 99.12,
    "close": 100.79,
    "volume": 1000,
}
assert real_yahoo_health["requested_provider"] == "yahoo"
assert real_yahoo_health["active_provider"] == "yahoo"
assert real_yahoo_health["rows_available"] == 3
assert real_yahoo_health["date_range"] == {
    "start_date": "2024-01-01",
    "end_date": "2024-01-03",
}
assert real_yahoo_health["fallback_used"] is False
assert real_yahoo_health["failure_message"] == ""

yahoo_original_import = builtins.__import__


def unavailable_historical_yfinance(name, *args, **kwargs):
    if name == "yfinance":
        raise ImportError("yfinance unavailable in deterministic test")

    return yahoo_original_import(name, *args, **kwargs)


builtins.__import__ = unavailable_historical_yfinance

try:
    yahoo_fallback_rows = yahoo_historical_adapter.get_ohlcv(
        ["AAPL"],
        "2024-01-01",
        "2024-01-05",
    )
    yahoo_fallback_health = historical_data_provider_health("yahoo")
finally:
    builtins.__import__ = yahoo_original_import

assert yahoo_fallback_rows == historical_rows
assert yahoo_historical_adapter.fallback_used is True
assert "yfinance unavailable" in yahoo_historical_adapter.last_error
assert yahoo_fallback_health["requested_provider"] == "yahoo"
assert yahoo_fallback_health["active_provider"] == "mock"
assert yahoo_fallback_health["rows_available"] == 5
assert yahoo_fallback_health["healthy"] is True
assert yahoo_fallback_health["fallback_used"] is True
assert "yfinance unavailable" in yahoo_fallback_health["failure_message"]


class MissingYahooTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    def history(self, start, end, auto_adjust=False):
        return pd.DataFrame(
            {
                "Open": [100, None],
                "High": [101, 102],
                "Low": [99, 100],
                "Close": [100.5, 101.5],
                "Volume": [1000, 1100],
            },
            index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
        )


class MissingYahooModule:
    Ticker = MissingYahooTicker


def missing_yfinance(name, *args, **kwargs):
    if name == "yfinance":
        return MissingYahooModule()

    return yahoo_original_import(name, *args, **kwargs)


builtins.__import__ = missing_yfinance
missing_adapter = YahooHistoricalDataAdapter()

try:
    missing_rows = missing_adapter.get_ohlcv(
        ["AAPL"],
        "2024-01-01",
        "2024-01-05",
    )
finally:
    builtins.__import__ = yahoo_original_import

assert missing_rows == historical_rows
assert missing_adapter.fallback_used is True
assert "Missing Yahoo OHLCV value" in missing_adapter.last_error


class InsufficientYahooTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    def history(self, start, end, auto_adjust=False):
        return pd.DataFrame(
            {
                "Open": [100],
                "High": [101],
                "Low": [99],
                "Close": [100.5],
                "Volume": [1000],
            },
            index=pd.to_datetime(["2024-01-01"]),
        )


class InsufficientYahooModule:
    Ticker = InsufficientYahooTicker


def insufficient_yfinance(name, *args, **kwargs):
    if name == "yfinance":
        return InsufficientYahooModule()

    return yahoo_original_import(name, *args, **kwargs)


builtins.__import__ = insufficient_yfinance
insufficient_adapter = YahooHistoricalDataAdapter()

try:
    insufficient_rows = insufficient_adapter.get_ohlcv(
        ["AAPL"],
        "2024-01-01",
        "2024-01-05",
    )
finally:
    builtins.__import__ = yahoo_original_import

assert insufficient_rows == historical_rows
assert insufficient_adapter.fallback_used is True
assert "Insufficient Yahoo historical rows" in insufficient_adapter.last_error

try:
    YahooHistoricalDataAdapter().get_ohlcv(
        ["INVALID"],
        "2024-01-01",
        "2024-01-05",
    )
    raise AssertionError("Invalid Yahoo ticker should fail before fetch.")
except ValueError as error:
    assert "Unsupported historical ticker" in str(error)

try:
    YahooHistoricalDataAdapter().get_ohlcv(
        ["AAPL"],
        "2024-01-05",
        "2024-01-01",
    )
    raise AssertionError("Invalid Yahoo date range should fail before fetch.")
except ValueError as error:
    assert "Start date" in str(error)

api_health = _data_provider_health()

assert api_health["active_provider"] == "mock"
assert api_health["supported_tickers_count"] > 0
assert api_health["latest_price_available"] is True
assert api_health["healthy"] is True

# ---------------------------------------------------------------------------
# YahooDataProvider never silently substitutes mock data. Failures and empty
# history raise; the MarketDataManager's explicit fallback path then reports
# provider=mock and fallback_used=True instead of labeling mock data as Yahoo.
# ---------------------------------------------------------------------------
from market.market_data_manager import MarketDataManager

yahoo_provider = YahooDataProvider()
original_import = builtins.__import__


def unavailable_yfinance(name, *args, **kwargs):
    if name == "yfinance":
        raise ImportError("yfinance unavailable in deterministic test")

    return original_import(name, *args, **kwargs)


builtins.__import__ = unavailable_yfinance

try:
    try:
        yahoo_provider.get_price_history("AAPL")
        raise AssertionError("Yahoo failure must raise, never return mock data.")
    except ValueError as error:
        assert "Yahoo price history unavailable" in str(error)

    try:
        yahoo_provider.get_latest_price("AAPL")
        raise AssertionError("Yahoo failure must raise, never return a mock price.")
    except ValueError as error:
        assert "Yahoo price history unavailable" in str(error)

    failed_manager = MarketDataManager(provider_name="yahoo")
    failed_result = failed_manager.latest_price("AAPL", use_cache=False)
finally:
    builtins.__import__ = original_import

assert failed_result["requested_provider"] == "yahoo"
assert failed_result["provider"] == "mock", (
    "A failing Yahoo provider must surface as an explicit mock fallback, "
    "never as a Yahoo-labeled price."
)
assert failed_result["fallback_used"] is True
assert "yahoo" in failed_manager.last_error


class EmptyYahooTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    def history(self, period):
        return pd.DataFrame()


class EmptyYahooModule:
    Ticker = EmptyYahooTicker


def empty_yfinance(name, *args, **kwargs):
    if name == "yfinance":
        return EmptyYahooModule()

    return original_import(name, *args, **kwargs)


builtins.__import__ = empty_yfinance

try:
    try:
        yahoo_provider.get_price_history("AAPL")
        raise AssertionError("Empty Yahoo history must raise, never return mock data.")
    except ValueError as error:
        assert "empty price history" in str(error)

    empty_manager = MarketDataManager(provider_name="yahoo")
    empty_result = empty_manager.latest_price("AAPL", use_cache=False)
finally:
    builtins.__import__ = original_import

assert empty_result["provider"] == "mock"
assert empty_result["fallback_used"] is True
assert "yahoo" in empty_manager.last_error


class LiveYahooTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    def history(self, period):
        return pd.DataFrame({
            "Close": [100.0 + index * 0.5 for index in range(60)],
        })


class LiveYahooModule:
    Ticker = LiveYahooTicker


def live_yfinance(name, *args, **kwargs):
    if name == "yfinance":
        return LiveYahooModule()

    return original_import(name, *args, **kwargs)


builtins.__import__ = live_yfinance

try:
    live_history = yahoo_provider.get_price_history("AAPL")
    live_price = yahoo_provider.get_latest_price("AAPL")
    live_manager = MarketDataManager(provider_name="yahoo")
    live_result = live_manager.latest_price("AAPL", use_cache=False)
finally:
    builtins.__import__ = original_import

assert len(live_history) == 60
assert live_price == live_history["Close"].iloc[-1] == 129.5
assert live_result["provider"] == "yahoo"
assert live_result["fallback_used"] is False
assert live_result["validated"] is True
assert live_result["price"] == 129.5

market_data = get_market_data("AAPL")

assert market_data["ticker"] == "AAPL"
assert market_data["price"] is not None
assert market_data["moving_average_20"] is not None
assert market_data["moving_average_50"] is not None
assert market_data["trend"] in {"Bullish", "Bearish", "Neutral"}

print("DataProvider test passed.")
