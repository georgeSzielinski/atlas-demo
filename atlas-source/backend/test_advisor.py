from engines.advisor_engine import AdvisorEngine


sample_recommendations = [
    {
        "ticker": "AAPL",
        "overall_score": 76,
    },
    {
        "ticker": "MSFT",
        "overall_score": 84,
    },
    {
        "ticker": "NVDA",
        "overall_score": 81,
    },
]

advisor = AdvisorEngine()

advice = advisor.advise(
    portfolio_health=75,
    recommendations=sample_recommendations,
    available_cash=500
)

print("Recommendation:", advice["best_investment"])
print("Amount:", advice["amount"])
print("Reason:", advice["reason"])

print("Warnings")
if not advice["warnings"]:
    print("- None")
else:
    for warning in advice["warnings"]:
        print("-", warning)
