from core.settings import (
    FUNDAMENTAL_PROVIDER,
    SUPPORTED_FUNDAMENTAL_PROVIDERS,
)
from engines.mock_fundamental_provider import MockFundamentalProvider
from engines.yahoo_fundamental_provider import YahooFundamentalProvider


class FundamentalEngine:

    def __init__(self, fundamental_provider=None):
        self.provider = self._select_provider(fundamental_provider)

    def analyze_ticker(self, ticker):
        return self.analyze(self.provider.get_fundamentals(ticker))

    def analyze(self, stock_data):
        if isinstance(stock_data, str):
            return self.analyze_ticker(stock_data)

        score = 50
        strengths = []
        weaknesses = []

        earnings_growth = stock_data.get("earnings_growth", 0)
        revenue_growth = stock_data.get("revenue_growth", 0)
        debt_to_equity = stock_data.get("debt_to_equity", 0)
        profit_margin = stock_data.get("profit_margin", 0)
        pe_ratio = stock_data.get("pe_ratio", 0)

        if earnings_growth > 0:
            score += 10
            strengths.append("Positive earnings growth")

        elif earnings_growth < 0:
            score -= 10
            weaknesses.append("Negative earnings growth")

        if revenue_growth > 0:
            score += 10
            strengths.append("Positive revenue growth")

        elif revenue_growth < 0:
            score -= 10
            weaknesses.append("Negative revenue growth")

        if debt_to_equity <= 0.5:
            score += 10
            strengths.append("Low debt")

        elif debt_to_equity > 1.5:
            score -= 10
            weaknesses.append("High debt")

        if profit_margin > 0:
            score += 10
            strengths.append("Positive profit margin")

        elif profit_margin < 0:
            score -= 10
            weaknesses.append("Negative profit margin")

        if pe_ratio <= 30:
            score += 10
            strengths.append("Reasonable valuation")

        elif pe_ratio > 50:
            score -= 10
            weaknesses.append("Very high valuation")

        score = max(0, min(100, score))

        return {
            "score": score,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "revenue": stock_data.get("revenue", 0),
            "eps": stock_data.get("eps", 0),
            "pe_ratio": pe_ratio,
            "debt": stock_data.get("debt", 0),
            "cash": stock_data.get("cash", 0),
            "market_cap": stock_data.get("market_cap", 0),
            "profit_margin": profit_margin,
            "roe": stock_data.get("roe", 0),
            "confidence": self._confidence(score, stock_data),
            "provider": self.provider.provider_name(),
        }

    def health_check(self):
        return self.provider.health_check()

    def _select_provider(self, fundamental_provider):
        selected_provider = fundamental_provider or FUNDAMENTAL_PROVIDER

        if selected_provider not in SUPPORTED_FUNDAMENTAL_PROVIDERS:
            return MockFundamentalProvider()

        if selected_provider == "yahoo":
            return YahooFundamentalProvider()

        return MockFundamentalProvider()

    def _confidence(self, score, stock_data):
        populated_fields = [
            "revenue",
            "eps",
            "pe_ratio",
            "debt",
            "cash",
            "market_cap",
            "profit_margin",
            "roe",
        ]
        available = [
            field for field in populated_fields
            if stock_data.get(field) not in (None, "")
        ]
        coverage = len(available) / len(populated_fields)

        return round((score * 0.6) + (coverage * 40), 2)
