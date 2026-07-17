SAMPLE_FUNDAMENTALS = {
    "AAPL": {
        "earnings_growth": 12,
        "revenue_growth": 8,
        "debt_to_equity": 1.5,
        "profit_margin": 24,
        "pe_ratio": 30,
    },
    "MSFT": {
        "earnings_growth": 18,
        "revenue_growth": 15,
        "debt_to_equity": 0.4,
        "profit_margin": 36,
        "pe_ratio": 34,
    },
    "NVDA": {
        "earnings_growth": 45,
        "revenue_growth": 38,
        "debt_to_equity": 0.2,
        "profit_margin": 55,
        "pe_ratio": 55,
    },
    "AMZN": {
        "earnings_growth": 22,
        "revenue_growth": 11,
        "debt_to_equity": 0.7,
        "profit_margin": 10,
        "pe_ratio": 42,
    },
    "GOOGL": {
        "earnings_growth": 16,
        "revenue_growth": 13,
        "debt_to_equity": 0.1,
        "profit_margin": 27,
        "pe_ratio": 25,
    },
    "COST": {
        "earnings_growth": 9,
        "revenue_growth": 7,
        "debt_to_equity": 0.5,
        "profit_margin": 3,
        "pe_ratio": 48,
    },
    "VOO": {
        "earnings_growth": 8,
        "revenue_growth": 6,
        "debt_to_equity": 0.6,
        "profit_margin": 12,
        "pe_ratio": 24,
    },
    "VTI": {
        "earnings_growth": 7,
        "revenue_growth": 5,
        "debt_to_equity": 0.7,
        "profit_margin": 11,
        "pe_ratio": 23,
    },
    "QQQ": {
        "earnings_growth": 15,
        "revenue_growth": 12,
        "debt_to_equity": 0.5,
        "profit_margin": 22,
        "pe_ratio": 32,
    },
    "SCHD": {
        "earnings_growth": 6,
        "revenue_growth": 4,
        "debt_to_equity": 0.8,
        "profit_margin": 18,
        "pe_ratio": 19,
    },
}

NEUTRAL_FUNDAMENTALS = {
    "earnings_growth": 0,
    "revenue_growth": 0,
    "debt_to_equity": 1.0,
    "profit_margin": 0,
    "pe_ratio": 30,
}


def get_fundamentals(ticker):
    return SAMPLE_FUNDAMENTALS.get(ticker, NEUTRAL_FUNDAMENTALS)
