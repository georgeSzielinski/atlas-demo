import os
import sqlite3
import tempfile

import database.connection as connection
from database.migrator import run_migrations
from database.repository import (
    save_paper_fund_snapshot,
    save_paper_fund_state,
)

# Force the deterministic mock market-data provider so the endpoint never
# touches the network and exercises the "real price-backed history required"
# path. Correlation must return NOT_EVALUATED under the mock provider.
os.environ["MARKET_DATA_PROVIDER"] = "mock"


def cleanup_database(path):
    connection._wal_initialized_paths.discard(path)
    for candidate in (path, f"{path}-wal", f"{path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


def table_counts(path):
    database = sqlite3.connect(path)
    cursor = database.cursor()
    counts = {}
    for table in (
        "paper_fund_states",
        "paper_fund_snapshots",
        "paper_fund_orders",
        "paper_fund_learning",
        "paper_fund_activity",
        "risk_decisions",
    ):
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]
    database.close()
    return counts


REQUIRED_POLICY_KEYS = {
    "read_only",
    "descriptive_only",
    "deterministic",
    "paper_only",
    "broker_integration",
    "real_money",
    "uses_real_price_history_only",
    "does_not_modify_recommendations",
    "does_not_modify_trades",
    "does_not_modify_risk_limits",
    "does_not_place_orders",
    "does_not_feed_risk_gate",
}

REQUIRED_SECTIONS = (
    "coverage",
    "correlation_matrix",
    "high_correlation_pairs",
    "clusters",
    "limit_violations",
    "insufficient_data",
    "data_source",
    "source_counts",
    "policy",
)


def seed_portfolio():
    policy = {
        "paper_only": True,
        "broker_integration": False,
        "real_money": False,
        "execution": "simulated_only",
        "human_approval_required_for_real_trading": True,
    }
    positions = {
        "AAPL": {
            "ticker": "AAPL",
            "quantity": 50,
            "cost_basis": 90,
            "current_price": 100,
            "current_value": 5000,
        },
        "MSFT": {
            "ticker": "MSFT",
            "quantity": 20,
            "cost_basis": 95,
            "current_price": 100,
            "current_value": 2000,
        },
    }
    save_paper_fund_state({
        "updated_at": "2026-07-03T10:15:00",
        "fund_status": "RUNNING",
        "watchlist": ["AAPL", "MSFT"],
        "starting_cash": 10000,
        "cash": 3000,
        "positions": positions,
        "realized_pl": 0,
        "last_update": "2026-07-03T10:15:00",
        "policy": policy,
    })
    save_paper_fund_snapshot({
        "as_of": "2026-07-03T10:15:00",
        "cycle_id": "cycle-3",
        "cash": 3000,
        "positions": positions,
        "current_value": 7000,
        "realized_pl": 0,
        "unrealized_pl": 0,
        "portfolio_value": 10000,
        "price_source": "test_live_prices",
        "policy": policy,
    })


from api.main import app, portfolio_correlation

# Route is registered as a read-only GET.
assert any(
    route.path == "/portfolio/correlation" and "GET" in route.methods
    for route in app.routes
), "GET /portfolio/correlation route must be registered."


def assert_sections(report):
    for section in REQUIRED_SECTIONS:
        assert section in report, section


def assert_policy(report):
    policy = report["policy"]
    assert REQUIRED_POLICY_KEYS.issubset(policy.keys())
    assert policy["read_only"] is True
    assert policy["deterministic"] is True
    assert policy["paper_only"] is True
    assert policy["broker_integration"] is False
    assert policy["real_money"] is False
    assert policy["uses_real_price_history_only"] is True
    assert policy["does_not_modify_recommendations"] is True
    assert policy["does_not_modify_trades"] is True
    assert policy["does_not_modify_risk_limits"] is True
    assert policy["does_not_place_orders"] is True
    assert policy["does_not_feed_risk_gate"] is True


original_database_path = connection.DATABASE_PATH

# ----------------------------------------------------------------------
# Seeded positions, mock provider: endpoint returns all sections,
# NOT_EVALUATED (real price-backed history required), and writes nothing.
# ----------------------------------------------------------------------
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()
    seed_portfolio()

    counts_before = table_counts(database_path)
    report = portfolio_correlation(limit=100)
    repeated = portfolio_correlation(limit=100)
    counts_after = table_counts(database_path)

    # Endpoint does not write to the database.
    assert counts_before == counts_after
    # Deterministic across calls.
    assert report == repeated

    # Endpoint returns every correlation section and policy fields.
    assert_sections(report)
    assert_policy(report)

    # Mock provider is not real price-backed history.
    assert report["status"] == "NOT_EVALUATED"
    assert report["data_source"]["price_backed"] is False
    assert "real price-backed" in report["reason"].lower()
    for section in (
        "correlation_matrix",
        "high_correlation_pairs",
        "clusters",
        "limit_violations",
    ):
        assert report[section]["status"] == "NOT_EVALUATED"
        assert report[section]["items"] == []
finally:
    connection.DATABASE_PATH = original_database_path
    cleanup_database(database_path)


# ----------------------------------------------------------------------
# Empty database: endpoint handles missing data cleanly (no writes).
# ----------------------------------------------------------------------
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as empty_database_file:
    empty_database_path = empty_database_file.name

try:
    connection.DATABASE_PATH = empty_database_path
    connection._wal_initialized_paths.discard(empty_database_path)
    run_migrations()

    empty_counts_before = table_counts(empty_database_path)
    empty_report = portfolio_correlation(limit=100)
    empty_counts_after = table_counts(empty_database_path)

    # No writes even when nothing can be evaluated.
    assert empty_counts_before == empty_counts_after

    assert_sections(empty_report)
    assert_policy(empty_report)
    assert empty_report["status"] == "NOT_EVALUATED"
    assert empty_report["coverage"]["symbols_held"] == 0
finally:
    connection.DATABASE_PATH = original_database_path
    cleanup_database(empty_database_path)


print("Correlation API test passed.")
