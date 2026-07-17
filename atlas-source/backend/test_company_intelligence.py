from core.settings import APPROVED_TICKERS
from engines.fundamental_engine import FundamentalEngine
from market.fundamentals import get_fundamentals


engine = FundamentalEngine()

for ticker in APPROVED_TICKERS:
    fundamentals = get_fundamentals(ticker)
    analysis = engine.analyze(fundamentals)

    print("Ticker:", ticker)
    print("Fundamental Score:", analysis["score"])

    print("Strengths")
    if not analysis["strengths"]:
        print("- None")
    else:
        for strength in analysis["strengths"]:
            print("-", strength)

    print("Weaknesses")
    if not analysis["weaknesses"]:
        print("- None")
    else:
        for weakness in analysis["weaknesses"]:
            print("-", weakness)

    print()
