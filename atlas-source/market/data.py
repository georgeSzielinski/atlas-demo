from core.settings import (
    DATA_PROVIDER,
    HISTORICAL_DATA_PROVIDER,
    SUPPORTED_DATA_PROVIDERS,
    SUPPORTED_HISTORICAL_DATA_PROVIDERS,
)
from market.indicators import calculate_indicators
from market.mock_historical_data_adapter import MockHistoricalDataAdapter
from market.mock_data_provider import MockDataProvider
from market.yahoo_historical_data_adapter import YahooHistoricalDataAdapter
from market.yahoo_data_provider import YahooDataProvider


def get_data_provider(provider_name=None):
    selected_provider = provider_name or DATA_PROVIDER

    if selected_provider not in SUPPORTED_DATA_PROVIDERS:
        return MockDataProvider()

    if selected_provider == "yahoo":
        return YahooDataProvider()

    return MockDataProvider()


class HistoricalDataProviderFactory:
    available_providers = {
        "mock": MockHistoricalDataAdapter,
        "yahoo": YahooHistoricalDataAdapter,
    }
    future_providers = ["polygon", "alpha_vantage", "csv", "parquet"]

    @classmethod
    def create(cls, provider_name=None):
        selected_provider = provider_name or HISTORICAL_DATA_PROVIDER
        provider_class = cls.available_providers.get(selected_provider)

        if provider_class is None:
            return MockHistoricalDataAdapter()

        return provider_class()


def get_historical_data_adapter(provider_name=None):
    return HistoricalDataProviderFactory.create(provider_name)


def historical_data_provider_health(provider_name=None):
    selected_provider = provider_name or HISTORICAL_DATA_PROVIDER
    adapter = get_historical_data_adapter(selected_provider)
    supported_tickers = adapter.get_supported_tickers()
    active_provider = adapter.provider_name
    start_date = "2024-01-01"
    end_date = "2024-01-05"

    try:
        rows = adapter.get_ohlcv(
            [supported_tickers[0]],
            start_date,
            end_date,
        )
        rows_available = len(rows) > 0
        metadata = adapter.health_metadata()
        active_provider = (
            "mock" if metadata["fallback_used"] else adapter.provider_name
        )

        return {
            "requested_provider": selected_provider,
            "active_provider": active_provider,
            "supported_tickers_count": len(supported_tickers),
            "rows_available": len(rows),
            "date_range": {
                "start_date": rows[0]["date"] if rows else start_date,
                "end_date": rows[-1]["date"] if rows else end_date,
            },
            "healthy": rows_available,
            "fallback_used": metadata["fallback_used"],
            "failure_message": metadata["last_error"]
            if metadata["fallback_used"]
            else (
                ""
                if rows_available
                else "No historical rows available."
            ),
        }
    except Exception as error:
        return {
            "requested_provider": selected_provider,
            "active_provider": active_provider,
            "supported_tickers_count": len(supported_tickers),
            "rows_available": 0,
            "date_range": {
                "start_date": start_date,
                "end_date": end_date,
            },
            "healthy": False,
            "fallback_used": getattr(adapter, "fallback_used", False),
            "failure_message": str(error),
        }


def data_provider_health(provider_name=None, ticker=None):
    selected_provider = provider_name or DATA_PROVIDER
    provider = get_data_provider(selected_provider)
    supported_tickers = provider.get_supported_tickers()
    probe_ticker = ticker or (
        supported_tickers[0] if supported_tickers else "AAPL"
    )

    try:
        latest_price = provider.get_latest_price(probe_ticker)
        latest_price_available = latest_price is not None

        return {
            "active_provider": selected_provider
            if selected_provider in SUPPORTED_DATA_PROVIDERS
            else "mock",
            "supported_tickers_count": len(supported_tickers),
            "latest_price_available": latest_price_available,
            "healthy": latest_price_available,
            "failure_message": ""
            if latest_price_available
            else f"No latest price available for {probe_ticker}.",
        }
    except Exception as error:
        return {
            "active_provider": selected_provider
            if selected_provider in SUPPORTED_DATA_PROVIDERS
            else "mock",
            "supported_tickers_count": len(supported_tickers),
            "latest_price_available": False,
            "healthy": False,
            "failure_message": str(error),
        }


def get_market_data(ticker):
    provider = get_data_provider()
    history = provider.get_price_history(ticker)

    if history.empty:
        raise ValueError(f"No market history returned for ticker {ticker}.")

    if len(history) < 50:
        raise ValueError(
            f"Not enough market history for ticker {ticker}: "
            f"expected at least 50 rows, got {len(history)}."
        )

    current_price = history["Close"].iloc[-1]

    one_week_return = (
        (history["Close"].iloc[-1] - history["Close"].iloc[-6])
        / history["Close"].iloc[-6]
    ) * 100

    one_month_return = (
        (history["Close"].iloc[-1] - history["Close"].iloc[-22])
        / history["Close"].iloc[-22]
    ) * 100

    indicators = calculate_indicators(history)

    return {
        "ticker": ticker,
        "price": current_price,
        "week_return": one_week_return,
        "month_return": one_month_return,
        "volatility": indicators["volatility"],
        "moving_average_20": indicators["moving_average_20"],
        "moving_average_50": indicators["moving_average_50"],
        "rsi": indicators["rsi"],
        "price_vs_20ma": indicators["price_vs_20ma"],
        "price_vs_50ma": indicators["price_vs_50ma"],
        "trend": indicators["trend"],
        "macd": indicators["macd"],
        "macd_signal": indicators["macd_signal"],
        "macd_trend": indicators["macd_trend"],
    }
