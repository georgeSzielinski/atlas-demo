import atexit
import os
import tempfile

import database.connection as connection
from api.main import (
    runtime_dashboard,
    runtime_status_dashboard,
    runtime_tasks_dashboard,
)
from database.repository import get_latest_runtime_state, get_runtime_states
from database.migrator import run_migrations
from database.setup import setup_database
from engines.runtime_engine import RuntimeEngine
from engines.runtime_state import RuntimeState


real_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as runtime_database_file:
    runtime_database_path = runtime_database_file.name


def cleanup_runtime_database():
    connection.DATABASE_PATH = real_database_path
    connection._wal_initialized_paths.discard(runtime_database_path)
    for candidate in (
        runtime_database_path,
        f"{runtime_database_path}-wal",
        f"{runtime_database_path}-shm",
    ):
        if os.path.exists(candidate):
            os.remove(candidate)


atexit.register(cleanup_runtime_database)
connection.DATABASE_PATH = runtime_database_path
connection._wal_initialized_paths.discard(runtime_database_path)
run_migrations()

engine = RuntimeEngine()
paper_portfolio = {
    "portfolio_value": 101500,
    "positions": {
        "AAPL": {"quantity": 10},
        "MSFT": {"quantity": 5},
    },
    "total_return": 1.5,
}
recommendations = [
    {"ticker": "AAPL", "action": "HOLD"},
    {"ticker": "MSFT", "action": "HOLD"},
]
provider_health = {
    "active_provider": "mock",
    "healthy": True,
    "latest_price_available": True,
}

state = engine.build_state(
    current_state="PRE_MARKET",
    market_date="2026-07-01",
    paper_portfolio=paper_portfolio,
    recommendations=recommendations,
    provider_health=provider_health,
)

assert state["runtime_id"].startswith("runtime-")
assert state["current_state"] == "PRE_MARKET"
assert state["market_phase"] == "pre_market"
assert state["paper_portfolio_value"] == 101500
assert state["active_watchlist_size"] == 2
assert state["open_positions"] == 2
assert state["recommendations_today"] == 2
assert state["health"]["status"] == "Warning"
assert state["next_cycle"]["next_state"] == "MARKET_OPEN"
assert state["tasks"]["current_task"] == (
    "Provider, macro, catalyst, and watchlist update"
)
assert state["policy"]["broker_integration"] is False
assert state["policy"]["automatic_execution"] is False

healthy = RuntimeState.build(
    current_state="IDLE",
    market_date="2026-07-01",
    market_phase="idle",
    last_cycle_time="2026-07-01T08:00:00",
    next_cycle={"next_state": "PRE_MARKET"},
    provider_health={"healthy": True},
    paper_portfolio_value=100000,
    active_watchlist_size=0,
    open_positions=0,
    recommendations_today=0,
    alerts=[],
    tasks={},
    operations_summary={},
)
assert healthy["health"]["status"] == "Healthy"

degraded = RuntimeState.build(
    current_state="PRE_MARKET",
    market_date="2026-07-01",
    market_phase="pre_market",
    last_cycle_time="2026-07-01T08:00:00",
    next_cycle={"next_state": "MARKET_OPEN"},
    provider_health={"healthy": False},
    paper_portfolio_value=100000,
    active_watchlist_size=0,
    open_positions=0,
    recommendations_today=0,
    alerts=[],
    tasks={},
    operations_summary={},
)
assert degraded["health"]["status"] == "Degraded"

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    setup_database()
    engine.persist_state(state)

    saved = get_runtime_states(limit=10)
    assert len(saved) == 1
    assert saved[0]["runtime_id"] == state["runtime_id"]
    assert saved[0]["current_state"] == "PRE_MARKET"

    latest = get_latest_runtime_state()
    assert latest["paper_portfolio_value"] == 101500

    runtime = runtime_dashboard()
    assert runtime["runtime"]["runtime_id"] == state["runtime_id"]
    assert runtime["policy"]["real_money"] is False

    status = runtime_status_dashboard()
    assert status["current_state"] == "PRE_MARKET"
    assert status["paper_portfolio_value"] == 101500
    assert status["system_health"]["status"] == "Warning"

    tasks = runtime_tasks_dashboard()
    assert tasks["current_task"] == (
        "Provider, macro, catalyst, and watchlist update"
    )
    assert tasks["next_cycle"]["next_state"] == "MARKET_OPEN"
finally:
    connection.DATABASE_PATH = original_database_path
    if os.path.exists(database_path):
        os.remove(database_path)

print("RuntimeEngine test passed.")
