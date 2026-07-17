from core.settings import APPROVED_TICKERS
from market.provider_health import EXPERIMENTAL, provider_health
from market.yahoo_data_provider import YahooDataProvider


class YahooProvider:
    """Market Data Manager wrapper around the existing Yahoo data provider.

    Reuses YahooDataProvider (live data only; failures raise instead of
    substituting mock values) and exposes the manager provider interface. The
    manager's explicit fallback path handles failures and reports them as
    fallback_used. Optional and non-deterministic; mock remains the default
    for tests.
    """

    name = "yahoo"
    requires_api_key = False
    supports_offline = False
    deterministic = False

    def __init__(self):
        self._provider = YahooDataProvider()

    def available(self):
        try:
            import yfinance  # noqa: F401

            return True
        except Exception:
            return False

    def get_latest_price(self, ticker):
        price = self._provider.get_latest_price(ticker)

        if price is None:
            raise ValueError(f"Yahoo provider returned no price for {ticker}.")

        return round(float(price), 4)

    def get_supported_tickers(self):
        return self._provider.get_supported_tickers()

    def health(self):
        available = self.available()
        message = (
            "yfinance available; live Yahoo data (failures raise and are "
            "reported as manager fallback)."
            if available
            else (
                "yfinance not installed; Yahoo provider fails and the "
                "manager reports fallback_used."
            )
        )

        return provider_health(EXPERIMENTAL, healthy=available, message=message)
