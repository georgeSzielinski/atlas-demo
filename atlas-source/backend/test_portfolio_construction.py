import os
import tempfile

import database.connection as connection
from api.main import (
    allocation_dashboard,
    portfolio_construction_dashboard,
    rebalance_dashboard,
    risk_budget_dashboard,
)
from database.repository import (
    get_portfolio_construction_reports,
    save_portfolio_construction_report,
)
from database.setup import setup_database
from engines.portfolio_construction_engine import PortfolioConstructionEngine


recommendations = [
    {
        "ticker": "AAPL",
        "action": "BUY",
        "confidence": 92,
        "overall_conviction": 90,
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "country": "US",
        "knowledge_score": 88,
        "stability_score": 82,
        "portfolio_score": 78,
    },
    {
        "ticker": "MSFT",
        "action": "BUY",
        "confidence": 84,
        "sector": "Technology",
        "industry": "Software",
        "country": "US",
        "knowledge_score": 86,
        "stability_score": 87,
        "portfolio_score": 74,
    },
    {
        "ticker": "JNJ",
        "action": "HOLD",
        "confidence": 72,
        "sector": "Healthcare",
        "industry": "Pharmaceuticals",
        "country": "US",
        "knowledge_score": 75,
        "stability_score": 80,
        "portfolio_score": 69,
    },
    {
        "ticker": "TSLA",
        "action": "AVOID",
        "confidence": 65,
        "sector": "Consumer Cyclical",
        "industry": "Auto",
        "country": "US",
        "knowledge_score": 60,
        "stability_score": 45,
        "portfolio_score": 48,
    },
]
paper_portfolio = {
    "cash": 20000,
    "portfolio_value": 100000,
    "positions": {
        "AAPL": {"ticker": "AAPL", "current_value": 30000},
        "MSFT": {"ticker": "MSFT", "current_value": 12000},
    },
}
probabilities = [
    {
        "ticker": "AAPL",
        "probabilities": {
            "outperformance": 70,
            "market_performance": 20,
            "underperformance": 10,
        },
    },
    {
        "ticker": "MSFT",
        "probabilities": {
            "outperformance": 62,
            "market_performance": 24,
            "underperformance": 14,
        },
    },
    {
        "ticker": "JNJ",
        "probabilities": {
            "outperformance": 46,
            "market_performance": 34,
            "underperformance": 20,
        },
    },
]

report = PortfolioConstructionEngine().build(
    recommendations=recommendations,
    paper_portfolio=paper_portfolio,
    macro_state={
        "current_macro_regime": "Sideways",
        "macro_risk_score": 55,
    },
    probabilities=probabilities,
    risk_metrics={"volatility": 13.5, "max_drawdown": -4.2, "beta": 1.02},
)

allocations = report["recommended_allocations"]
ranking = report["capital_allocation_ranking"]
actions = report["portfolio_actions"]

assert report["policy"]["paper_only"] is True
assert report["policy"]["broker_integration"] is False
assert report["policy"]["automatic_execution"] is False
assert len(allocations) == 3
assert allocations[0]["ticker"] == "AAPL"
assert allocations[0]["position_priority"] == "Highest Priority"
assert allocations[0]["suggested_allocation"] <= report["constraints"][
    "max_single_position"
]
assert allocations[0]["capital_required"] >= allocations[1]["capital_required"]
assert allocations[0]["confidence_adjusted_allocation"] > 0
assert allocations[0]["probability_adjusted_allocation"] > 0
assert allocations[0]["knowledge_adjusted_allocation"] > 0
assert allocations[0]["stability_adjusted_allocation"] > 0
assert ranking[0]["priority"] == "Highest Priority"
assert report["diversification"]["sector_exposure"]["Technology"] > 0
assert report["diversification"]["cash_allocation"] >= 0
assert report["diversification"]["portfolio_health"] in {
    "Strong",
    "Healthy",
    "Watch",
    "Concentrated",
}
assert report["risk_budget"]["summary"]["risk_budget"] in {
    "Low",
    "Moderate",
    "Elevated",
    "High",
}
assert len(report["risk_budget"]["holdings"]) == 3
assert any(item["action"] in {"Reduce", "Maintain"} for item in actions)
assert len(report["scenario_analysis"]) == 7
assert report["scientific_validation"]["simulation_arena_required"] is True
assert report["scientific_validation"]["scientific_validation_required"] is True
assert report["operations_summary"]["suggested_rebalance"] in {
    "Increase",
    "Reduce",
    "Maintain",
    "Diversify",
    "Raise Cash",
    "Rebalance",
}

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    setup_database()
    save_portfolio_construction_report(report)

    stored = get_portfolio_construction_reports(limit=10)
    assert len(stored) == 1
    assert stored[0]["recommended_allocations"][0]["ticker"] == "AAPL"
    assert stored[0]["policy"]["real_money"] is False

    api_report = portfolio_construction_dashboard()
    assert api_report["policy"]["paper_only"] is True
    assert api_report["portfolio_construction"]["policy"]["real_money"] is False
    assert len(api_report["stored_reports"]) == 1

    api_allocation = allocation_dashboard()
    assert api_allocation["capital_allocation_ranking"][0]["priority"] == (
        "Highest Priority"
    )

    api_rebalance = rebalance_dashboard()
    assert api_rebalance["policy"]["automatic_execution"] is False
    assert len(api_rebalance["portfolio_actions"]) > 0

    api_risk = risk_budget_dashboard()
    assert api_risk["risk_summary"]["risk_budget"] in {
        "Low",
        "Moderate",
        "Elevated",
        "High",
    }
finally:
    connection.DATABASE_PATH = original_database_path
    if os.path.exists(database_path):
        os.remove(database_path)

print("PortfolioConstructionEngine test passed.")
