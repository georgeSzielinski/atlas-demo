from datetime import datetime, timedelta


class IndexHistoryProvider:
    """Read-only daily close history for market-level gauge symbols.

    Serves the Market Regime Engine with SPY, QQQ, and ^VIX closes. These are
    observation-only market gauges, never trade candidates, so this provider
    intentionally does not enforce APPROVED_TICKERS. It also has no mock
    fallback: when Yahoo data is unavailable it returns whatever it could
    fetch (possibly nothing) and records the error, so the caller reports
    NOT_EVALUATED instead of classifying synthetic data.
    """

    provider_name = "yahoo"
    DEFAULT_LOOKBACK_DAYS = 420

    def __init__(self, lookback_days=None):
        self.lookback_days = lookback_days or self.DEFAULT_LOOKBACK_DAYS
        self.last_error = ""

    def get_daily_closes(self, symbols):
        """Return {symbol: [{"date", "close"}, ...]} sorted by date.

        Symbols that cannot be fetched are omitted from the result and the
        failure is recorded in ``last_error``.
        """
        self.last_error = ""

        try:
            import yfinance as yf
        except Exception as error:
            self.last_error = f"yfinance unavailable: {error}"

            return {}

        start = datetime.now() - timedelta(days=self.lookback_days)
        history = {}
        errors = []

        for symbol in symbols:
            try:
                rows = self._fetch_symbol(yf, symbol, start)

                if not rows:
                    raise ValueError(f"No Yahoo daily closes for {symbol}.")

                history[symbol] = rows
            except Exception as error:
                errors.append(f"{symbol}: {error}")

        if errors:
            self.last_error = "; ".join(errors)

        return history

    def _fetch_symbol(self, yf, symbol, start):
        frame = yf.Ticker(symbol).history(
            start=start.strftime("%Y-%m-%d"),
            auto_adjust=False,
        )
        rows = []

        for index, row in frame.iterrows():
            close = row.get("Close")

            if close is None or close != close:
                continue

            rows.append({
                "date": index.strftime("%Y-%m-%d"),
                "close": round(float(close), 4),
            })

        return sorted(rows, key=lambda entry: entry["date"])
