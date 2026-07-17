from datetime import datetime, timedelta

from core.settings import APPROVED_TICKERS
from market.historical_data_adapter import HistoricalDataAdapter


class MockHistoricalDataAdapter(HistoricalDataAdapter):
    provider_name = "mock"

    def __init__(self):
        self.supported_tickers = list(APPROVED_TICKERS)
        self.fallback_used = False
        self.last_error = ""

    def get_supported_tickers(self):
        return self.supported_tickers

    def get_ohlcv(self, tickers, start_date, end_date):
        if not tickers:
            raise ValueError("At least one ticker is required.")

        start = self._date(start_date)
        end = self._date(end_date)

        if start > end:
            raise ValueError("Start date must be on or before end date.")

        unsupported = [
            ticker for ticker in tickers
            if ticker not in self.supported_tickers
        ]

        if unsupported:
            raise ValueError(
                "Unsupported historical ticker(s): "
                f"{', '.join(sorted(unsupported))}."
            )

        rows = []
        current = start

        while current <= end:
            for ticker in sorted(tickers):
                rows.append(self._row(ticker, current))

            current += timedelta(days=1)

        return sorted(rows, key=lambda row: (row["date"], row["ticker"]))

    def _row(self, ticker, date_value):
        index = (date_value - datetime(2020, 1, 1)).days
        ticker_seed = sum(ord(character) for character in ticker)
        base = 80 + (ticker_seed % 45)
        drift = (index % 37) * 0.35
        cycle = ((index + ticker_seed) % 9) - 4
        close = round(base + drift + cycle, 2)
        open_price = round(close - 0.45, 2)
        high = round(max(open_price, close) + 1.15, 2)
        low = round(min(open_price, close) - 1.1, 2)
        volume = 1000000 + (ticker_seed * 1000) + (index % 30) * 2500

        return {
            "date": date_value.strftime("%Y-%m-%d"),
            "ticker": ticker,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }

    def _date(self, value):
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Historical dates must use YYYY-MM-DD format."
            ) from error
