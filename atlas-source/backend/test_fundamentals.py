from engines.fundamental_engine import FundamentalEngine


sample_data = {
    "earnings_growth": 18,
    "revenue_growth": 12,
    "debt_to_equity": 0.4,
    "profit_margin": 28,
    "pe_ratio": 26,
}

engine = FundamentalEngine()
analysis = engine.analyze(sample_data)

print("Fundamental Score:", analysis["score"])

print("Strengths")
for strength in analysis["strengths"]:
    print("-", strength)

print("Weaknesses")
if not analysis["weaknesses"]:
    print("- None")
else:
    for weakness in analysis["weaknesses"]:
        print("-", weakness)
