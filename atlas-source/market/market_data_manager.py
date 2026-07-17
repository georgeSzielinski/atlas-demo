import os
from datetime import datetime

from core.settings import APPROVED_TICKERS, DATA_PROVIDER
from market.alpaca_market_provider import AlpacaMarketProvider
from market.data_cache import MarketDataCache
from market.data_validator import MarketDataValidator
from market.mock_data_provider import MockDataProvider
from market.polygon_provider import PolygonProvider
from market.provider_health import HEALTHY, MOCK, provider_health
from market.yahoo_provider import YahooProvider


class MarketDataManager:
    """Single entry point for all market data.

    Responsibilities: provider selection, validation, fallback, caching, and
    health. Mock is the default so tests and offline operation stay
    deterministic. Atlas never fails because one provider is unavailable; every
    external dependency falls back to the deterministic mock provider.

    This layer observes the market only. It does not connect brokers, execute
    trades, or change recommendation logic.
    """

    SUPPORTED_PROVIDERS = ["mock", "yahoo", "polygon", "alpaca"]
    DEFAULT_PROVIDER = "mock"
    FALLBACK_PROVIDER = "mock"

    def __init__(self, provider_name=None, cache=None, validator=None, clock=None):
        requested = (
            provider_name
            or os.environ.get("MARKET_DATA_PROVIDER")
            or DATA_PROVIDER
            or self.DEFAULT_PROVIDER
        )
        self.provider_name = (
            requested if requested in self.SUPPORTED_PROVIDERS else self.DEFAULT_PROVIDER
        )
        self.cache = cache or MarketDataCache(clock=clock)
        self.validator = validator or MarketDataValidator()
        self.last_error = ""

    # ------------------------------------------------------------------
    # Prices
    # ------------------------------------------------------------------
    def latest_price(self, ticker, use_cache=True):
        ticker = ticker.upper()
        key = f"latest:{self.provider_name}:{ticker}"

        if use_cache:
            cached = self.cache.get(key)
            if cached is not None:
                return self._result(
                    ticker=ticker,
                    price=cached["value"],
                    provider=cached["provider"],
                    fallback_used=cached["fallback_used"],
                    cache_hit=True,
                    cache_age=cached["cache_age"],
                    validated=True,
                )

        price, provider, fallback_used = self._fetch(self.provider_name, ticker)
        validation = self.validator.validate_price(
            price,
            ticker,
            self._supported_tickers(provider),
        )

        if not validation["valid"] and provider != self.FALLBACK_PROVIDER:
            price, provider, _ = self._fetch(self.FALLBACK_PROVIDER, ticker)
            fallback_used = True
            validation = self.validator.validate_price(
                price,
                ticker,
                self._supported_tickers(provider),
            )

        self.cache.set(key, price, provider, fallback_used=fallback_used)

        return self._result(
            ticker=ticker,
            price=price,
            provider=provider,
            fallback_used=fallback_used,
            cache_hit=False,
            cache_age=0,
            validated=validation["valid"],
            validation=validation,
        )

    def latest_prices(self, tickers, use_cache=True):
        tickers = [ticker.upper() for ticker in tickers]
        results = {
            ticker: self.latest_price(ticker, use_cache=use_cache)
            for ticker in tickers
        }
        prices = {
            ticker: result["price"]
            for ticker, result in results.items()
        }
        fallback_used = any(result["fallback_used"] for result in results.values())
        validated = all(result["validated"] for result in results.values())

        return {
            "requested_provider": self.provider_name,
            "prices": prices,
            "results": results,
            "fallback_used": fallback_used,
            "validated": validated,
            "as_of": datetime.now().isoformat(),
            "policy": self.policy(),
        }

    def historical_prices(self, tickers, start_date, end_date, adapter=None):
        if adapter is None:
            from market.yahoo_historical_data_adapter import YahooHistoricalDataAdapter

            adapter = YahooHistoricalDataAdapter()

        rows = adapter.get_ohlcv(
            [ticker.upper() for ticker in tickers],
            start_date,
            end_date,
        )

        return {
            "requested_provider": "yahoo",
            "rows": rows,
            "fallback_used": bool(getattr(adapter, "fallback_used", False)),
            "validated": bool(rows),
            "data_source": (
                "historical Yahoo data"
                if not getattr(adapter, "fallback_used", False)
                else "historical fallback data"
            ),
            "last_price_date": rows[-1]["date"] if rows else None,
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Status / health / cache
    # ------------------------------------------------------------------
    def market_status(self, as_of=None):
        """Single source of truth for market session state.

        Delegates to the timezone-aware exchange trading calendar
        (:class:`market.market_calendar.MarketCalendar`), which handles
        weekends, US market holidays, and early closes in America/New_York, and
        returns an explicit unavailable state rather than guessing when the
        session cannot be determined.
        """
        from market.market_calendar import MarketCalendar

        status = MarketCalendar().session(as_of)
        status["policy"] = self.policy()

        return status

    def health(self, probe_ticker="AAPL"):
        probe = self.latest_price(probe_ticker)
        market_providers = self._registry_market_providers()

        return {
            "requested_provider": self.provider_name,
            "active_provider": probe["provider"],
            "healthy": probe["validated"],
            "fallback_used": probe["fallback_used"],
            "default_provider": self.DEFAULT_PROVIDER,
            "fallback_provider": self.FALLBACK_PROVIDER,
            "offline_capable": self.provider_name in {"mock"},
            "providers": market_providers,
            "last_error": self.last_error,
            "policy": self.policy(),
        }

    def cache_status(self):
        return {
            "entries": self.cache.entries(),
            "stats": self.cache.stats(),
            "policy": self.policy(),
        }

    def provider_summary(self):
        return {
            "current_provider": self.provider_name,
            "default_provider": self.DEFAULT_PROVIDER,
            "fallback_provider": self.FALLBACK_PROVIDER,
            "supported_providers": list(self.SUPPORTED_PROVIDERS),
            "configurable_via": [
                "MARKET_DATA_PROVIDER environment variable",
                "DATA_PROVIDER environment variable",
                "MarketDataManager(provider_name=...)",
            ],
            "provider_details": self._provider_details(),
            "policy": self.policy(),
        }

    def snapshot(self, tickers=None, as_of=None):
        tickers = tickers or list(APPROVED_TICKERS)[:4]
        prices = self.latest_prices(tickers)
        status = self.market_status(as_of)

        return {
            "snapshot_date": prices["as_of"],
            "provider": self._dominant_provider(prices),
            "requested_provider": self.provider_name,
            "fallback_used": prices["fallback_used"],
            "validated": prices["validated"],
            "ticker_count": len(prices["prices"]),
            "prices": prices["prices"],
            "market_status": status,
            "policy": self.policy(),
        }

    def persist_snapshot(self, snapshot):
        from database.repository import save_market_data_snapshot

        save_market_data_snapshot(snapshot)

    def policy(self):
        return {
            "read_only": True,
            "paper_trading_only": True,
            "broker_integration": False,
            "automatic_execution": False,
            "changes_recommendation_behavior": False,
            "mock_default": True,
            "graceful_fallback": True,
            "human_approval_required": True,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _make_provider(self, name):
        if name == "yahoo":
            return YahooProvider()

        if name == "polygon":
            return PolygonProvider()

        if name == "alpaca":
            return AlpacaMarketProvider()

        return MockDataProvider()

    def _fetch(self, name, ticker):
        provider = self._make_provider(name)

        try:
            price = provider.get_latest_price(ticker)

            if price is None:
                raise ValueError(f"No price returned by {name} for {ticker}.")

            return round(float(price), 4), name, name != self.provider_name
        except Exception as error:
            self.last_error = f"{name}: {error}"
            mock = MockDataProvider()
            price = round(float(mock.get_latest_price(ticker)), 4)

            return price, self.FALLBACK_PROVIDER, True

    def _supported_tickers(self, provider_name):
        provider = self._make_provider(provider_name)

        try:
            return provider.get_supported_tickers()
        except Exception:
            return list(APPROVED_TICKERS)

    def _registry_market_providers(self):
        try:
            from market.provider_registry import ProviderRegistry

            return [
                provider for provider in ProviderRegistry().health()["providers"]
                if provider["category"] == "Market Data"
            ]
        except Exception:
            return []

    def _provider_details(self):
        details = []

        for name in self.SUPPORTED_PROVIDERS:
            provider = self._make_provider(name)
            details.append({
                "name": name,
                "requires_api_key": getattr(provider, "requires_api_key", False),
                "supports_offline": getattr(provider, "supports_offline", name == "mock"),
                "deterministic": getattr(provider, "deterministic", name == "mock"),
                "available": self._provider_available(provider, name),
                "current": name == self.provider_name,
            })

        return details

    def _provider_available(self, provider, name):
        if name == "mock":
            return True

        available = getattr(provider, "available", None)
        if callable(available):
            try:
                return bool(available())
            except Exception:
                return False

        return False

    def _dominant_provider(self, prices):
        providers = [
            result["provider"] for result in prices["results"].values()
        ]

        if not providers:
            return self.provider_name

        return max(set(providers), key=providers.count)

    def _result(
        self,
        ticker,
        price,
        provider,
        fallback_used,
        cache_hit,
        cache_age,
        validated,
        validation=None,
    ):
        return {
            "ticker": ticker,
            "price": price,
            "provider": provider,
            "requested_provider": self.provider_name,
            "fallback_used": fallback_used,
            "cache_hit": cache_hit,
            "cache_age": cache_age,
            "validated": validated,
            "validation": validation or {"valid": validated},
        }
