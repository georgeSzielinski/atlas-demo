from datetime import datetime

from core.settings import APPROVED_TICKERS
from market.historical_data_adapter import HistoricalDataAdapter
from market.mock_historical_data_adapter import MockHistoricalDataAdapter


class YahooHistoricalDataAdapter(HistoricalDataAdapter):
    provider_name = "yahoo"
    MIN_ROWS = 2

    def __init__(self):
        self.fallback_provider = MockHistoricalDataAdapter()
        self.supported_tickers = list(APPROVED_TICKERS)
        self.fallback_used = False
        self.last_error = ""

    def get_supported_tickers(self):
        return self.supported_tickers

    def get_ohlcv(self, tickers, start_date, end_date):
        self._validate_request(tickers, start_date, end_date)

        try:
            rows = self._fetch_yahoo_rows(tickers, start_date, end_date)
            self._validate_rows(rows, tickers)
            self.fallback_used = False
            self.last_error = ""

            return rows
        except Exception as error:
            self.fallback_used = True
            self.last_error = str(error)

            return self.fallback_provider.get_ohlcv(
                tickers,
                start_date,
                end_date,
            )

    def _fetch_yahoo_rows(self, tickers, start_date, end_date):
        import yfinance as yf

        rows = []
        for ticker in sorted(tickers):
            history = yf.Ticker(ticker).history(
                start=start_date,
                end=end_date,
                auto_adjust=False,
            )
            if history.empty:
                raise ValueError(f"No Yahoo historical rows for {ticker}.")

            rows.extend(self._normalize_history(ticker, history))

        return sorted(rows, key=lambda row: (row["date"], row["ticker"]))

    def _normalize_history(self, ticker, history):
        rows = []

        for index, row in history.iterrows():
            date = self._date_string(index)
            values = {
                "open": self._number(row.get("Open")),
                "high": self._number(row.get("High")),
                "low": self._number(row.get("Low")),
                "close": self._number(row.get("Close")),
                "volume": self._integer(row.get("Volume")),
            }

            if any(value is None for value in values.values()):
                raise ValueError(f"Missing Yahoo OHLCV value for {ticker} on {date}.")

            rows.append({
                "date": date,
                "timestamp": date,
                "ticker": ticker,
                **values,
            })

        return rows

    def _validate_request(self, tickers, start_date, end_date):
        if not tickers:
            raise ValueError("At least one ticker is required.")

        self._date(start_date)
        self._date(end_date)
        if start_date > end_date:
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

    def _validate_rows(self, rows, tickers):
        if not rows:
            raise ValueError("No Yahoo historical rows returned.")

        keys = [(row["date"], row["ticker"]) for row in rows]
        if keys != sorted(keys):
            raise ValueError("Yahoo historical rows must be sorted by date and ticker.")

        required = {"date", "timestamp", "ticker", "open", "high", "low", "close", "volume"}
        for row in rows:
            missing = required - set(row)
            if missing:
                raise ValueError(
                    "Yahoo historical row is missing required field(s): "
                    f"{', '.join(sorted(missing))}."
                )
            if any(row[key] is None for key in required):
                raise ValueError("Yahoo historical rows contain missing values.")

        returned_tickers = {row["ticker"] for row in rows}
        missing_tickers = set(tickers) - returned_tickers
        if missing_tickers:
            raise ValueError(
                "Yahoo returned no rows for ticker(s): "
                f"{', '.join(sorted(missing_tickers))}."
            )

        for ticker in tickers:
            count = len([row for row in rows if row["ticker"] == ticker])
            if count < self.MIN_ROWS:
                raise ValueError(
                    f"Insufficient Yahoo historical rows for {ticker}: "
                    f"expected at least {self.MIN_ROWS}, got {count}."
                )

    def _date_string(self, value):
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d")

        return self._date(value).strftime("%Y-%m-%d")

    def _date(self, value):
        try:
            if hasattr(value, "strftime"):
                return value

            return datetime.strptime(value, "%Y-%m-%d")
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Historical dates must use YYYY-MM-DD format."
            ) from error

    def _number(self, value):
        try:
            if value != value:
                return None

            return round(float(value), 2)
        except (TypeError, ValueError):
            return None

    def _integer(self, value):
        try:
            if value != value:
                return None

            return int(value)
        except (TypeError, ValueError):
            return None
