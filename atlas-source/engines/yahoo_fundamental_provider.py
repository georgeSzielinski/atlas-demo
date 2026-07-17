from engines.fundamental_provider import FundamentalProvider
from engines.mock_fundamental_provider import MockFundamentalProvider


class YahooFundamentalProvider(FundamentalProvider):

    def __init__(self):
        self.fallback_provider = MockFundamentalProvider()
        self.last_error = ""

    def get_company_profile(self, ticker):
        try:
            info = self._get_info(ticker)
            self.last_error = ""

            return {
                "ticker": str(ticker).upper(),
                "name": info.get("longName") or info.get("shortName") or "",
                "sector": info.get("sector") or "",
            }
        except Exception as error:
            self.last_error = str(error)

            return self.fallback_provider.get_company_profile(ticker)

    def get_fundamentals(self, ticker):
        try:
            info = self._get_info(ticker)
            self.last_error = ""

            return {
                "revenue": info.get("totalRevenue") or 0,
                "eps": info.get("trailingEps") or 0,
                "pe_ratio": info.get("trailingPE") or 0,
                "debt": info.get("totalDebt") or 0,
                "cash": info.get("totalCash") or 0,
                "market_cap": info.get("marketCap") or 0,
                "profit_margin": self._percent(info.get("profitMargins")),
                "roe": self._percent(info.get("returnOnEquity")),
                "earnings_growth": self._percent(info.get("earningsGrowth")),
                "revenue_growth": self._percent(info.get("revenueGrowth")),
                "debt_to_equity": info.get("debtToEquity") or 1.0,
            }
        except Exception as error:
            self.last_error = str(error)

            return self.fallback_provider.get_fundamentals(ticker)

    def health_check(self):
        return {
            "provider": self.provider_name(),
            "healthy": True,
            "message": "Yahoo fundamental provider is optional and failure-safe.",
        }

    def provider_name(self):
        return "yahoo"

    def _get_info(self, ticker):
        import yfinance as yf

        return yf.Ticker(ticker).info or {}

    def _percent(self, value):
        if value is None:
            return 0

        return round(value * 100, 2)
