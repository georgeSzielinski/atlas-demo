import os
import tempfile

import database.connection as connection
from api.main import simulation_arena_dashboard
from database.repository import (
    get_discovery_source_data,
    get_research_dashboard_data,
    get_scientific_validation_reports,
    get_simulation_arena_runs,
)
from database.setup import setup_database
from engines.discovery_engine import DiscoveryEngine
from engines.performance_observatory import PerformanceObservatory
from engines.research_engine import ResearchEngine
from engines.simulation_arena import SimulationArena


def row(index, ticker, price, future_price, month_return, volatility):
    return {
        "date": f"2024-01-{index:02d}",
        "validation_date": f"2024-02-{index:02d}",
        "ticker": ticker,
        "asset_type": "Stock",
        "price": price,
        "future_price": future_price,
        "week_return": month_return / 4,
        "month_return": month_return,
        "moving_average_20": price * 0.98,
        "moving_average_50": price * 0.95,
        "price_vs_20ma": 2,
        "price_vs_50ma": 5,
        "rsi": 58,
        "macd": 1,
        "macd_signal": 0.5,
        "macd_trend": "Bullish",
        "volatility": volatility,
        "trend": "Bullish" if month_return >= 0 else "Bearish",
        "score": 4,
        "fundamental_score": 68,
        "forecast_score": 72 if future_price >= price else 40,
        "news_confidence": 62,
        "portfolio_score": 66,
        "risk_score": 70,
        "committee_agreement": 74,
        "executive_confidence": 76,
        "stability_score": 79,
        "knowledge_score": 77,
    }


historical_data = []
for day in range(1, 16):
    historical_data.append(
        row(day, "AAPL", 100 + day, 104 + day, 3.0, 2.0)
    )
    historical_data.append(
        row(day, "MSFT", 200 + day, 198 + day, -1.5, 3.0)
    )

historical_data = sorted(
    historical_data,
    key=lambda item: (item["date"], item["ticker"]),
)

arena = SimulationArena()
report = arena.run(
    dataset="deterministic-arena-fixture",
    tickers=["AAPL", "MSFT"],
    date_range={"start": "2024-01-01", "end": "2024-01-15"},
    validation_window=10,
    historical_data=historical_data,
    run_date="2026-06-30T13:00:00",
)

assert report["arena_id"].startswith("arena-")
assert report["dataset"] == "deterministic-arena-fixture"
assert len(report["strategy_configs"]) == 10
assert len(report["results"]) == 10
assert report["policy"]["changes_recommendation_behavior"] is False
assert report["policy"]["automatic_execution"] is False

strategy_names = {item["strategy_name"] for item in report["results"]}
assert "Current Atlas" in strategy_names
assert "No News" in strategy_names
assert "No Forecast" in strategy_names
assert "No SEC" in strategy_names
assert "No Macro" in strategy_names
assert "No Catalysts" in strategy_names
assert "No Committee" in strategy_names
assert "No Executive Review" in strategy_names
assert "No Probability" in strategy_names
assert "Candidate Model Placeholder" in strategy_names

current = next(
    item for item in report["results"]
    if item["strategy_name"] == "Current Atlas"
)
candidate = next(
    item for item in report["results"]
    if item["strategy_name"] == "Candidate Model Placeholder"
)
assert set(current["metrics"].keys()) == {
    "win_rate",
    "average_return",
    "sharpe_ratio",
    "max_drawdown",
    "probability_calibration",
    "recommendation_accuracy",
    "trade_frequency",
    "average_holding_period",
    "stability_score",
    "knowledge_score",
}
assert candidate["recommendation"] == "Not recommended"
assert "Candidate Model Placeholder" in report["comparison"]["not_recommended"]
assert report["comparison"]["best_overall"] is not None
assert report["comparison"]["best_risk_adjusted"] is not None
assert report["comparison"]["best_low_drawdown"] is not None
assert report["comparison"]["most_stable"] is not None
assert report["comparison"]["most_knowledgeable"] is not None
assert report["scientific_validation"]["policy"]["automatic_adoption"] is False

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    setup_database()
    arena.persist_run(report)

    saved = get_simulation_arena_runs(limit=10)
    assert len(saved) == 1
    assert saved[0]["arena_id"] == report["arena_id"]
    assert saved[0]["comparison"]["best_overall"] == report["comparison"]["best_overall"]
    assert len(saved[0]["results"]) == 10

    scientific_reports = get_scientific_validation_reports(limit=10)
    assert scientific_reports[0]["feature_tested"].startswith(
        "Simulation Arena Strategy:"
    )

    research_dashboard = get_research_dashboard_data()
    assert research_dashboard["simulation_arena_runs"][0]["arena_id"] == report["arena_id"]

    research_report = ResearchEngine().research_dashboard_data()
    assert research_report["simulation_arena_report"]["arena_run_count"] == 1

    source_data = get_discovery_source_data()
    assert source_data["simulation_arena_runs"][0]["arena_id"] == report["arena_id"]

    observatory = PerformanceObservatory().generate(
        source_data=source_data,
        discovery_data={
            "recent_discoveries": [],
            "top_discoveries": [],
            "discovery_history": [],
        },
    )
    assert observatory["simulation_arena_summary"]["arena_run_count"] == 1

    discoveries = DiscoveryEngine().analyze(
        source_data=source_data,
        discovery_date="2026-06-30T13:05:00",
    )
    assert any(
        item["title"] == "Simulation Arena strategy leader"
        for item in discoveries
    )

    api_result = simulation_arena_dashboard()
    assert api_result["simulation_arena_runs"][0]["arena_id"] == report["arena_id"]
    assert api_result["policy"]["broker_integration"] is False
finally:
    connection.DATABASE_PATH = original_database_path
    if os.path.exists(database_path):
        os.remove(database_path)

print("SimulationArena test passed.")
