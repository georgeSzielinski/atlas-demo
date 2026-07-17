import os

from core.settings import APPROVED_TICKERS
from market.provider_health import UNAVAILABLE, provider_health


class PolygonProvider:
    """Polygon.io market data placeholder.

    Registered but not integrated. It always reports unavailable offline so the
    Market Data Manager falls back gracefully. No network calls are made.
    """

    name = "polygon"
    requires_api_key = True
    supports_offline = False
    deterministic = False

    def __init__(self):
        self.api_key = os.environ.get("POLYGON_API_KEY")

    def available(self):
        return False

    def get_latest_price(self, ticker):
        raise NotImplementedError(
            "Polygon market data provider is a placeholder and not integrated."
        )

    def get_supported_tickers(self):
        return list(APPROVED_TICKERS)

    def health(self):
        return provider_health(
            UNAVAILABLE,
            healthy=False,
            message="Polygon provider is a registered placeholder; not integrated.",
        )
