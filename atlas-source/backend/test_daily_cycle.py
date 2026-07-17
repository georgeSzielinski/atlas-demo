import os
import tempfile

import database.connection as connection
from api.main import (
    daily_cycle_dashboard,
    latest_daily_cycle_dashboard,
    run_daily_cycle,
)
from database.repository import (
    get_daily_cycle_runs,
    get_latest_daily_cycle_run,
)
from database.setup import setup_database
from engines.daily_cycle_engine import DailyCycleEngine


engine = DailyCycleEngine()

watchlist = [
    {
        "ticker": "AAPL",
        "action": "HOLD",
        "reason": "Daily paper watchlist.",
        "sector": "Technology",
    },
    {
        "ticker": "MSFT",
        "action": "HOLD",
        "reason": "Daily paper watchlist.",
        "sector": "Technology",
    },
]

pre_market = engine.run_phase(
    "pre_market",
    cycle_date="2026-07-01",
    recommendations=watchlist,
)
assert pre_market["phase"] == "pre_market"
assert pre_market["recommendations_count"] == 2
assert pre_market["policy"]["broker_integration"] is False
assert "watchlist_recommendations" in pre_market["details"]

market_open = engine.run_phase(
    "market_open",
    cycle_date="2026-07-01",
    recommendations=watchlist,
)
assert market_open["phase"] == "market_open"
assert market_open["status"] == "MONITORING"

portfolio = {
    "cash": 90000,
    "positions": {
        "AAPL": {
            "ticker": "AAPL",
            "quantity": 100,
            "cost_basis": 100,
            "entry_date": "2026-06-30",
        }
    },
    "realized_pl": 0,
    "history": [
        {
            "date": "2026-06-30",
            "portfolio_value": 100000,
        }
    ],
    "trades": [],
}
market_close = engine.run_phase(
    "market_close",
    cycle_date="2026-07-01",
    recommendations=[],
    market_prices={"AAPL": 110},
    portfolio=portfolio,
    benchmark_returns={"S&P 500": 0.3},
)
assert market_close["phase"] == "market_close"
assert market_close["paper_portfolio_value"] == 101000
assert market_close["daily_return"] == 1
assert market_close["alpha_vs_sp500"] == 0.7
assert market_close["details"]["paper_report"]["policy"]["real_money"] is False

post_market = engine.run_phase("post_market", cycle_date="2026-07-01")
assert post_market["phase"] == "post_market"
assert post_market["status"] == "REVIEW_READY"
assert post_market["details"]["follow_up_research_items"]

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    setup_database()
    engine.persist_cycle(pre_market)
    engine.persist_cycle(market_close)
    engine.persist_cycle(post_market)

    runs = get_daily_cycle_runs(limit=10)
    assert len(runs) == 3
    assert runs[0]["phase"] == "post_market"
    assert runs[1]["paper_portfolio_value"] == 101000

    latest = get_latest_daily_cycle_run()
    assert latest["cycle_id"] == post_market["cycle_id"]

    api_runs = daily_cycle_dashboard()
    assert len(api_runs["daily_cycle_runs"]) == 3
    assert api_runs["policy"]["broker_integration"] is False

    api_latest = latest_daily_cycle_dashboard()
    assert api_latest["latest_daily_cycle"]["phase"] == "post_market"
    assert (
        api_latest["policy"]["human_approval_required_for_real_trading"]
        is True
    )

    run_result = run_daily_cycle()
    assert run_result["simulation"]["mode"] == "full_daily_cycle"
    assert run_result["simulation"]["status"] == "SIMULATED"
    assert len(run_result["simulation"]["phases"]) == 4
    assert run_result["policy"]["broker_integration"] is False
    assert run_result["policy"]["real_money"] is False
    assert run_result["policy"]["human_approval_required_for_real_trading"] is True
    assert run_result["daily_cycle"]["daily_cycle_runs"]
    assert run_result["daily_journal"]["daily_journals"]
    # Simulated daily-cycle prices are research context only; they never
    # create paper trading records, which must stay price-backed or absent.
    assert run_result["paper_portfolio"]["latest_portfolio"] is None
finally:
    connection.DATABASE_PATH = original_database_path
    if os.path.exists(database_path):
        os.remove(database_path)

print("DailyCycleEngine test passed.")
