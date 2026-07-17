import os

from core.settings import APPROVED_TICKERS
from market.provider_health import UNAVAILABLE, provider_health


class AlpacaMarketProvider:
    """Alpaca Market Data placeholder.

    Registered but not integrated. This is market data only; it does not place
    orders, connect a broker, or execute trades. It always reports unavailable
    offline so the Market Data Manager falls back gracefully.
    """

    name = "alpaca"
    requires_api_key = True
    supports_offline = False
    deterministic = False

    def __init__(self):
        self.api_key = os.environ.get("ALPACA_API_KEY")
        self.api_secret = os.environ.get("ALPACA_API_SECRET")

    def available(self):
        return False

    def get_latest_price(self, ticker):
        raise NotImplementedError(
            "Alpaca market data provider is a placeholder and not integrated. "
            "It is market data only and never executes trades."
        )

    def get_supported_tickers(self):
        return list(APPROVED_TICKERS)

    def health(self):
        return provider_health(
            UNAVAILABLE,
            healthy=False,
            message=(
                "Alpaca market data provider is a registered placeholder; not "
                "integrated. Market data only, no broker or execution."
            ),
        )
