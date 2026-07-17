from engines.fundamental_provider import FundamentalProvider


MOCK_FUNDAMENTALS = {
    "AAPL": {
        "revenue": 383_000_000_000,
        "eps": 6.13,
        "pe_ratio": 30,
        "debt": 108_000_000_000,
        "cash": 62_000_000_000,
        "market_cap": 3_000_000_000_000,
        "profit_margin": 24,
        "roe": 150,
        "earnings_growth": 12,
        "revenue_growth": 8,
        "debt_to_equity": 1.5,
    },
    "MSFT": {
        "revenue": 245_000_000_000,
        "eps": 11.8,
        "pe_ratio": 34,
        "debt": 78_000_000_000,
        "cash": 80_000_000_000,
        "market_cap": 3_200_000_000_000,
        "profit_margin": 36,
        "roe": 37,
        "earnings_growth": 18,
        "revenue_growth": 15,
        "debt_to_equity": 0.4,
    },
}

NEUTRAL_FUNDAMENTALS = {
    "revenue": 0,
    "eps": 0,
    "pe_ratio": 30,
    "debt": 0,
    "cash": 0,
    "market_cap": 0,
    "profit_margin": 0,
    "roe": 0,
    "earnings_growth": 0,
    "revenue_growth": 0,
    "debt_to_equity": 1.0,
}


class MockFundamentalProvider(FundamentalProvider):

    def get_company_profile(self, ticker):
        symbol = str(ticker).upper()

        return {
            "ticker": symbol,
            "name": f"{symbol} Mock Company",
            "sector": "Unknown",
        }

    def get_fundamentals(self, ticker):
        symbol = str(ticker).upper()
        fundamentals = MOCK_FUNDAMENTALS.get(symbol, NEUTRAL_FUNDAMENTALS)

        return dict(fundamentals)

    def health_check(self):
        return {
            "provider": self.provider_name(),
            "healthy": True,
            "message": "Mock fundamental provider is available offline.",
        }

    def provider_name(self):
        return "mock"
