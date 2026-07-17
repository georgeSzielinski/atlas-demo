from core.settings import APPROVED_TICKERS
from market.data_provider import DataProvider


class YahooDataProvider(DataProvider):
    """Live Yahoo (yfinance) data only — never substitutes synthetic values.

    Failures and empty history raise so callers handle them through their
    explicit failure/fallback paths (MarketDataManager reports fallback_used
    honestly; market analysis skips the ticker). Mock data is only ever served
    by MockDataProvider under the mock provider identity.
    """

    def get_price_history(self, ticker):
        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            history = stock.history(period="6mo")
        except Exception as error:
            raise ValueError(
                f"Yahoo price history unavailable for {ticker}: {error}"
            ) from error

        if history.empty:
            raise ValueError(
                f"Yahoo returned empty price history for {ticker}."
            )

        return history

    def get_latest_price(self, ticker):
        history = self.get_price_history(ticker)

        return history["Close"].iloc[-1]

    def get_supported_tickers(self):
        return list(APPROVED_TICKERS)
