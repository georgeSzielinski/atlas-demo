import pandas as pd

from core.settings import APPROVED_TICKERS
from market.data_provider import DataProvider


class MockDataProvider(DataProvider):
    HISTORY_LENGTH = 126

    def get_price_history(self, ticker):
        base_price = self._base_price(ticker)
        drift = self._drift(ticker)
        closes = [
            round(base_price + (index * drift) + ((index % 5) - 2) * 0.15, 2)
            for index in range(self.HISTORY_LENGTH)
        ]

        return pd.DataFrame({"Close": closes})

    def get_latest_price(self, ticker):
        history = self.get_price_history(ticker)

        return history["Close"].iloc[-1]

    def get_supported_tickers(self):
        return list(APPROVED_TICKERS)

    def _base_price(self, ticker):
        return 80 + (sum(ord(character) for character in ticker) % 120)

    def _drift(self, ticker):
        direction = 1 if sum(ord(character) for character in ticker) % 2 == 0 else -1

        return direction * 0.12
