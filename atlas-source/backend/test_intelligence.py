from engines.explainability_engine import ExplainabilityEngine
from engines.investment_intelligence_engine import InvestmentIntelligenceEngine


technical_score = 84
fundamental_score = 92
portfolio_score = 75
risk_score = 80
recommendation = "BUY"

intelligence_engine = InvestmentIntelligenceEngine()
explainability_engine = ExplainabilityEngine()

analysis = intelligence_engine.evaluate(
    technical_score=technical_score,
    fundamental_score=fundamental_score,
    portfolio_health_score=portfolio_score,
    risk_score=risk_score
)
explanation = explainability_engine.generate_explanation(
    recommendation=recommendation,
    technical_score=technical_score,
    fundamental_score=fundamental_score,
    portfolio_score=portfolio_score,
    risk_score=risk_score
)

print("Overall Score:", analysis["overall_score"])
print("Rating:", analysis["rating"])

print("Strengths")
for strength in explanation["strengths"]:
    print("-", strength)

print("Concerns")
if not explanation["concerns"]:
    print("- None")
else:
    for concern in explanation["concerns"]:
        print("-", concern)

print("Summary:", explanation["summary"])
