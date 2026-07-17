import json
import os
import tempfile

from fastapi import HTTPException

import database.connection as connection
from api.main import (
    app,
    paper_broker_status,
    paper_performance_dashboard,
    paper_portfolio_dashboard,
    paper_replay_health,
    paper_trades_dashboard,
    paper_trading_status_dashboard,
    reset_paper_simulation,
    run_paper_replay,
    run_paper_simulation,
)
from database.repository import (
    get_paper_performance_reports,
    get_paper_portfolio_history,
    get_paper_trades,
    save_paper_trading_report,
)
from database.setup import setup_database
from engines.paper_trading_engine import PaperTradingEngine


class _FallbackHistoricalAdapter:
    """Test fixture: adapter that returns rows but reports it fell back to mock."""

    fallback_used = True

    def get_ohlcv(self, tickers, start_date, end_date):
        return [
            {"date": "2024-01-02", "ticker": "AAPL", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000},
            {"date": "2024-01-03", "ticker": "AAPL", "open": 110, "high": 111, "low": 109, "close": 110, "volume": 1000},
        ]


# Historical replay must never silently use fallback rows: fail loudly instead.
fallback_replay = PaperTradingEngine().run_historical_price_replay(
    recommendations=[{"ticker": "AAPL", "action": "BUY"}],
    tickers=["AAPL"],
    start_date="2024-01-02",
    end_date="2024-01-03",
    historical_adapter=_FallbackHistoricalAdapter(),
)
assert fallback_replay["replay_status"] == "FAILED"
assert fallback_replay["price_backed"] is False
assert fallback_replay["error"] == "Historical prices unavailable"
assert fallback_replay["audit"]["fallback_used"] is True
assert fallback_replay["audit"]["rows_used_count"] == 0
assert fallback_replay["trades"] == []
assert fallback_replay["replay_history"] == []


engine = PaperTradingEngine()

# Recommendation behavior unchanged: paper trading never mutates its inputs
# and never changes recommendation logic.
recommendation_input = [
    {
        "ticker": "AAPL",
        "action": "BUY",
        "reason": "High-conviction paper entry.",
        "sector": "Technology",
    },
    {
        "ticker": "MSFT",
        "action": "BUY",
        "reason": "Diversified paper entry.",
        "sector": "Technology",
    },
    {
        "ticker": "NVDA",
        "action": "HOLD",
        "reason": "No virtual trade needed.",
        "sector": "Technology",
    },
]
recommendation_snapshot_before = json.dumps(recommendation_input, sort_keys=True)
day_one = engine.run(
    recommendations=recommendation_input,
    market_prices={"AAPL": 100, "MSFT": 200, "NVDA": 50},
    as_of_date="2026-06-30",
    benchmark_returns={
        "S&P 500": 0.2,
        "NASDAQ-100": 0.3,
        "Equal Weight Placeholder": 0.1,
    },
)
assert json.dumps(recommendation_input, sort_keys=True) == recommendation_snapshot_before
assert engine.policy()["changes_recommendation_behavior"] is False

assert day_one["portfolio"]["cash"] == 81000
assert day_one["portfolio"]["portfolio_value"] == 100000
assert day_one["positions"]["AAPL"]["quantity"] == 100
assert day_one["positions"]["MSFT"]["quantity"] == 45
assert len(day_one["trades"]) == 2
assert day_one["policy"]["broker_integration"] is False
assert day_one["policy"]["automatic_execution"] is False

portfolio_state = {
    "cash": day_one["portfolio"]["cash"],
    "positions": day_one["positions"],
    "realized_pl": day_one["portfolio"]["realized_pl"],
    "history": [day_one["portfolio"]],
    "trades": day_one["trades"],
}
day_two = engine.run(
    recommendations=[
        {
            "ticker": "AAPL",
            "action": "SELL",
            "reason": "Take paper profit.",
            "sector": "Technology",
        },
        {
            "ticker": "MSFT",
            "action": "SELL",
            "reason": "Cut paper loss.",
            "sector": "Technology",
        },
        {
            "ticker": "TSLA",
            "action": "AVOID",
            "reason": "No virtual position.",
            "sector": "Consumer Cyclical",
        },
    ],
    market_prices={"AAPL": 120, "MSFT": 180, "TSLA": 250},
    as_of_date="2026-07-01",
    portfolio=portfolio_state,
    benchmark_returns={
        "S&P 500": 0.4,
        "NASDAQ-100": 0.5,
        "Equal Weight Placeholder": 0.2,
    },
)

assert day_two["portfolio"]["cash"] == 101100
assert day_two["portfolio"]["portfolio_value"] == 101100
assert day_two["portfolio"]["realized_pl"] == 1100
assert day_two["portfolio"]["total_return"] == 1.1
assert day_two["performance"]["win_rate"] == 50
assert day_two["performance"]["alpha_vs_sp"] == 0.7
assert day_two["performance"]["paper_validation_source"] is True
assert day_two["research"]["best_trades"][0]["ticker"] == "AAPL"
assert day_two["research"]["worst_trades"][0]["ticker"] == "MSFT"

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    setup_database()

    # 1 + 2: The Paper Trading API returns NO demo data by default. An empty
    # database means an empty setup state, never a fake portfolio.
    empty_api_portfolio = paper_portfolio_dashboard()
    assert empty_api_portfolio["latest_portfolio"] is None
    assert empty_api_portfolio["portfolio_history"] == []
    assert empty_api_portfolio["empty_state"] == (
        "No paper replay has run yet. Configure Historical Price Replay."
    )
    assert empty_api_portfolio["policy"].get("demo_data") is not True
    assert "status" not in empty_api_portfolio["policy"]

    empty_api_trades = paper_trades_dashboard()
    assert empty_api_trades["paper_trades"] == []
    assert empty_api_trades["policy"].get("demo_data") is not True

    empty_api_performance = paper_performance_dashboard()
    assert empty_api_performance["paper_performance_reports"] == []
    assert empty_api_performance["policy"].get("demo_data") is not True

    # Removed demo product modes are rejected loudly.
    for removed_mode in ["demo_simulation", "demo_preview", "fake_paper"]:
        try:
            run_paper_simulation(mode="market_close", paper_mode=removed_mode)
            raise AssertionError(f"{removed_mode} must be rejected")
        except HTTPException as error:
            assert error.status_code == 400
            assert "removed" in error.detail.lower()

    # Non-price-backed reports can never enter the paper tables.
    refused = save_paper_trading_report(day_two)
    assert refused["persisted"] is False
    assert refused["price_backed"] is False
    assert get_paper_portfolio_history(limit=10) == []

    # Daily-cycle simulations still run for research context, but they no
    # longer create paper portfolio/trade/performance records.
    market_close_sim = run_paper_simulation(mode="market_close")
    assert market_close_sim["simulation"]["status"] == "SIMULATED"
    assert get_paper_portfolio_history(limit=10) == []
    assert market_close_sim["paper_portfolio"]["latest_portfolio"] is None

    full_cycle_sim = run_paper_simulation(mode="full_daily_cycle")
    assert full_cycle_sim["simulation"]["mode"] == "full_daily_cycle"
    assert len(full_cycle_sim["simulation"]["phases"]) == 4
    assert get_paper_portfolio_history(limit=10) == []
    assert get_paper_trades(limit=10) == []
    assert get_paper_performance_reports(limit=10) == []

    # 9: Learning status before any replay.
    status_before = paper_trading_status_dashboard()
    assert status_before["paper_trading_status"] == "Not started"
    assert status_before["current_mode"] == "not_started"
    assert status_before["price_backed"] is False
    assert status_before["replays_completed"] == 0
    assert status_before["learning"]["learning_active"] is False
    assert status_before["learning"]["message"] == (
        "Atlas has not started learning from paper trading yet."
    )

    # 3 + 4 + 5: Historical replay with mocked OHLCV rows completes using
    # actual close prices: entry 100 -> 110 with qty 100 = $1,000 unrealized.
    replay_result = run_paper_replay(
        payload={
            "tickers": ["AAPL"],
            "start_date": "2024-01-02",
            "end_date": "2024-01-04",
            "starting_cash": 100000,
            "allocation_percent": 10,
            "mode": "historical_price_replay",
            "historical_rows": [
                {
                    "date": "2024-01-02",
                    "ticker": "AAPL",
                    "open": 100,
                    "high": 101,
                    "low": 99,
                    "close": 100,
                    "volume": 1000,
                },
                {
                    "date": "2024-01-03",
                    "ticker": "AAPL",
                    "open": 105,
                    "high": 106,
                    "low": 104,
                    "close": 105,
                    "volume": 1000,
                },
                {
                    "date": "2024-01-04",
                    "ticker": "AAPL",
                    "open": 110,
                    "high": 111,
                    "low": 109,
                    "close": 110,
                    "volume": 1000,
                },
            ],
        }
    )
    replay = replay_result["replay"]
    replay_portfolio = replay_result["paper_portfolio"]["latest_portfolio"]
    replay_trades = replay_result["paper_trades"]["paper_trades"]
    replay_history = replay_result["paper_portfolio"]["portfolio_history"]
    replay_trade = replay["trades"][0]
    assert replay["replay_status"] == "COMPLETED"
    assert replay["metadata"]["mode"] == "historical_price_replay"
    assert replay["metadata"]["price_backed"] is True
    assert replay["metadata"]["data_source"] == "mocked_historical_prices"
    assert replay["dates_tested"] == ["2024-01-02", "2024-01-03", "2024-01-04"]
    assert len(replay["replay_history"]) == 3
    assert replay_trade["entry_price"] == 100
    assert replay_trade["quantity"] == 100
    assert replay_trade["transaction_cost"] == 0
    assert replay_trade["slippage"] == 0
    assert replay["portfolio"]["positions"]["AAPL"]["current_price"] == 110
    assert replay["portfolio"]["positions"]["AAPL"]["unrealized_pl"] == (110 - 100) * 100
    assert replay["portfolio"]["portfolio_value"] == 101000
    assert replay["policy"]["changes_recommendation_behavior"] is False
    assert replay_portfolio["policy"]["price_backed"] is True
    assert replay_portfolio["policy"]["mode"] == "historical_price_replay"
    assert replay_portfolio["policy"].get("demo_data") is not True
    assert replay_portfolio["policy"]["broker_integration"] is False
    assert replay_trades[0]["transaction_cost"] == 0
    assert replay_trades[0]["slippage"] == 0
    # 8: P/L graph data exists only now, after a price-backed replay.
    assert len(replay_history) == 3

    # Replay audit trail proves the run was price-backed by real rows.
    audit = replay["audit"]
    assert replay_result["audit"] == audit
    assert replay_result["price_backed"] is True
    assert replay["price_backed"] is True
    assert audit["price_backed"] is True
    assert audit["fallback_used"] is False
    assert audit["price_source"] == "mocked_historical_prices"
    assert audit["requested_tickers"] == ["AAPL"]
    assert audit["rows_used_count"] == 3
    assert audit["first_price_date"] == "2024-01-02"
    assert audit["last_price_date"] == "2024-01-04"
    assert audit["trades_generated"] == 1
    assert audit["portfolio_points_generated"] == 3
    assert audit["failure_reason"] is None
    assert len(audit["price_rows_used"]) == 3
    assert audit["price_rows_used"][0]["close"] == 100
    assert audit["price_rows_used"][-1]["close"] == 110

    # 9: Learning status activates only after a price-backed replay.
    status_after = paper_trading_status_dashboard()
    assert status_after["paper_trading_status"] == "Replay completed"
    assert status_after["current_mode"] == "historical_price_replay"
    assert status_after["price_backed"] is True
    assert status_after["replays_completed"] == 1
    assert status_after["trades_generated"] == 1
    assert status_after["portfolio_points_generated"] == 3
    assert status_after["last_successful_replay"] is not None
    assert status_after["learning"]["learning_active"] is True
    assert status_after["learning"]["message"] == (
        "Atlas is learning from historical replay results."
    )
    assert status_after["learning"]["latest_replay_result"]["price_backed"] is True

    # 6: Missing rows for a requested ticker fail loudly.
    missing_price_replay = run_paper_replay(
        payload={
            "tickers": ["AAPL", "MSFT"],
            "start_date": "2024-01-02",
            "end_date": "2024-01-03",
            "starting_cash": 100000,
            "mode": "historical_price_replay",
            "historical_rows": [
                {
                    "date": "2024-01-02",
                    "ticker": "AAPL",
                    "open": 100,
                    "high": 101,
                    "low": 99,
                    "close": 100,
                    "volume": 1000,
                },
                {
                    "date": "2024-01-03",
                    "ticker": "AAPL",
                    "open": 110,
                    "high": 111,
                    "low": 109,
                    "close": 110,
                    "volume": 1000,
                },
            ],
        }
    )
    assert missing_price_replay["replay"]["replay_status"] == "FAILED"
    assert missing_price_replay["replay"]["trades"] == []
    assert missing_price_replay["replay"]["replay_history"] == []
    assert missing_price_replay["replay"]["policy"]["broker_integration"] is False

    # No historical rows at all -> FAILED, not price-backed, no fake data.
    no_rows_replay = run_paper_replay(
        payload={
            "tickers": ["AAPL"],
            "start_date": "2024-01-02",
            "end_date": "2024-01-04",
            "mode": "historical_price_replay",
            "historical_rows": [],
        }
    )
    assert no_rows_replay["replay"]["replay_status"] == "FAILED"
    assert no_rows_replay["price_backed"] is False
    assert no_rows_replay["replay"]["price_backed"] is False
    assert no_rows_replay["replay"]["error"] == "Historical prices unavailable"
    assert no_rows_replay["replay"]["trades"] == []
    assert no_rows_replay["replay"]["replay_history"] == []
    assert no_rows_replay["audit"]["price_backed"] is False
    assert no_rows_replay["audit"]["rows_used_count"] == 0
    assert no_rows_replay["audit"]["failure_reason"] == "Historical prices unavailable"
    # A failed replay never returns a chart, trades, or P/L.
    assert no_rows_replay["paper_portfolio"]["latest_portfolio"] is None
    assert no_rows_replay["paper_trades"]["paper_trades"] == []
    assert no_rows_replay["paper_performance"]["paper_performance_reports"] == []
    # 7: Failed/fallback replays never pollute the stored price-backed data.
    assert len(get_paper_portfolio_history(limit=10)) == 3
    assert len(get_paper_trades(limit=10)) == 1
    assert len(get_paper_performance_reports(limit=10)) == 1

    # 10: Broker paper foundation exists, but execution stays disabled.
    broker = paper_broker_status()
    assert broker["broker_paper_supported"] == "pending"
    assert broker["mode"] == "broker_paper_pending"
    assert broker["provider"] == "alpaca_paper"
    assert broker["execution_enabled"] is False
    assert broker["real_money"] is False
    assert broker["order_endpoints"] == []
    assert isinstance(broker["missing_config"], list)
    assert isinstance(broker["configured"], bool)

    # 11: No live order/execution endpoint exists anywhere in the API.
    route_paths = [getattr(route, "path", "") for route in app.routes]
    assert all("order" not in path.lower() for path in route_paths)
    assert all("execute" not in path.lower() for path in route_paths)
    broker_posts = [
        route
        for route in app.routes
        if getattr(route, "path", "").startswith("/paper-broker")
        and "POST" in (getattr(route, "methods", None) or set())
    ]
    assert broker_posts == []

    # Data source health surface for the replay UI.
    health = paper_replay_health()
    assert isinstance(health["yfinance_installed"], bool)
    assert health["historical_provider"] == "yahoo"
    assert isinstance(health["how_to_fix"], list)
    if not health["yfinance_installed"]:
        assert "pip install yfinance" in health["how_to_fix"][0]

    # Reset returns Paper Trading to its empty setup state, not demo data.
    reset_result = reset_paper_simulation()
    assert reset_result["paper_portfolio"]["latest_portfolio"] is None
    assert reset_result["paper_portfolio"]["portfolio_history"] == []
    assert reset_result["paper_trades"]["paper_trades"] == []
    assert reset_result["paper_performance"]["paper_performance_reports"] == []
    assert reset_result["paper_portfolio"]["policy"].get("demo_data") is not True
finally:
    connection.DATABASE_PATH = original_database_path
    if os.path.exists(database_path):
        os.remove(database_path)

print("PaperTradingEngine test passed.")
