import os
import sqlite3
import tempfile

import database.connection as connection
from database.migrator import run_migrations
from database.repository import (
    add_paper_fund_learning,
    save_paper_fund_order,
    save_paper_fund_snapshot,
    save_paper_fund_state,
    save_risk_decision,
)


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
    "does_not_modify_recommendations",
    "does_not_modify_trades",
    "does_not_modify_risk_limits",
    "does_not_place_orders",
}

REQUIRED_SECTIONS = (
    "portfolio_status",
    "portfolio_return_drivers",
    "symbol_contribution",
    "trade_contribution",
    "sector_contribution",
    "risk_decision_impact",
    "cash_drag",
    "realized_vs_unrealized",
    "attribution_confidence",
    "source_counts",
    "policy",
)


def seed_portfolio_history():
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
            "unrealized_pl": 500,
        },
        "MSFT": {
            "ticker": "MSFT",
            "quantity": 20,
            "cost_basis": 95,
            "current_price": 100,
            "current_value": 2000,
            "unrealized_pl": 100,
        },
        "XLE": {
            "ticker": "XLE",
            "quantity": 20,
            "cost_basis": 110,
            "current_price": 100,
            "current_value": 2000,
            "unrealized_pl": -200,
        },
        "ZZZZ": {
            "ticker": "ZZZZ",
            "quantity": 5,
            "cost_basis": 100,
            "current_price": 100,
            "current_value": 500,
            "unrealized_pl": 0,
        },
    }

    save_paper_fund_state({
        "updated_at": "2026-07-03T10:15:00",
        "fund_status": "RUNNING",
        "watchlist": ["AAPL", "MSFT", "XLE", "ZZZZ"],
        "starting_cash": 10000,
        "cash": 500,
        "positions": positions,
        "realized_pl": 150,
        "interval_minutes": 30,
        "last_update": "2026-07-03T10:15:00",
        "next_update": "2026-07-03T10:45:00",
        "last_error": None,
        "price_provider": "test_live_prices",
        "policy": policy,
    })
    save_paper_fund_snapshot({
        "as_of": "2026-07-03T10:15:00",
        "cycle_id": "cycle-3",
        "cash": 500,
        "positions": positions,
        "current_value": 9500,
        "realized_pl": 150,
        "unrealized_pl": 400,
        "portfolio_value": 10000,
        "daily_return": 0.5,
        "total_return": 0,
        "price_source": "test_live_prices",
        "policy": policy,
    })

    for order in (
        {
            "order_id": "order-buy-aapl",
            "cycle_id": "cycle-3",
            "ticker": "AAPL",
            "side": "BUY",
            "quantity": 50,
            "status": "FILLED_SIMULATED",
            "created_at": "2026-07-03T10:10:00",
            "fill_price": 90,
        },
        {
            "order_id": "order-sell-tsla",
            "cycle_id": "cycle-3",
            "ticker": "TSLA",
            "side": "SELL",
            "quantity": 10,
            "status": "FILLED_SIMULATED",
            "created_at": "2026-07-03T10:11:00",
            "fill_price": 200,
        },
    ):
        save_paper_fund_order({**order, "policy": policy})

    construction_targets = [
        {"ticker": "AAPL", "sector": "Technology", "suggested_allocation": 30},
        {"ticker": "MSFT", "sector": "Technology", "suggested_allocation": 20},
        {"ticker": "XLE", "sector": "Energy", "suggested_allocation": 20},
    ]
    add_paper_fund_learning({
        "at": "2026-07-03T10:16:00",
        "cycle_id": "cycle-3",
        "lesson": "Performance attribution API seed.",
        "details": {
            "learning_summary": {
                "recommended_symbols": ["AAPL", "MSFT", "XLE", "ZZZZ"],
                "construction_targets": construction_targets,
            },
        },
    })
    save_risk_decision({
        "decision_id": "risk-rejected-msft-1",
        "cycle_id": "cycle-3",
        "symbol": "MSFT",
        "side": "BUY",
        "quantity": 20,
        "verdict": "REJECTED",
        "checks": {
            "checks": [],
            "rejections": [
                {
                    "rule": "affordability",
                    "status": "REJECTED",
                    "limit": 1000,
                    "measured": 1500,
                    "reason": "Buy order value exceeds available cash.",
                }
            ],
            "reasons": ["Buy order value exceeds available cash."],
        },
        "policy": policy,
        "created_at": "2026-07-03T10:11:00",
    })


from api.main import app, performance_attribution

# Route is registered as a read-only GET.
assert any(
    route.path == "/performance-attribution" and "GET" in route.methods
    for route in app.routes
), "GET /performance-attribution route must be registered."


def assert_policy(report):
    policy = report["policy"]
    assert REQUIRED_POLICY_KEYS.issubset(policy.keys())
    assert policy["read_only"] is True
    assert policy["descriptive_only"] is True
    assert policy["deterministic"] is True
    assert policy["paper_only"] is True
    assert policy["broker_integration"] is False
    assert policy["real_money"] is False
    assert policy["does_not_modify_recommendations"] is True
    assert policy["does_not_modify_trades"] is True
    assert policy["does_not_modify_risk_limits"] is True
    assert policy["does_not_place_orders"] is True


def assert_sections(report):
    for section in REQUIRED_SECTIONS:
        assert section in report, section


original_database_path = connection.DATABASE_PATH

# ----------------------------------------------------------------------
# Seeded database: endpoint returns full attribution with no writes.
# ----------------------------------------------------------------------
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()
    seed_portfolio_history()

    counts_before = table_counts(database_path)
    report = performance_attribution(limit=100)
    repeated = performance_attribution(limit=100)
    counts_after = table_counts(database_path)

    # Endpoint does not write to the database.
    assert counts_before == counts_after
    # Deterministic across calls.
    assert report == repeated

    # Endpoint returns every attribution section.
    assert_sections(report)

    # Symbol contribution is attributable from the seeded snapshot.
    symbol = report["symbol_contribution"]
    assert symbol["status"] == "EVALUATED"
    assert symbol["total_unrealized_pl"] == 400
    assert symbol["best"]["symbol"] == "AAPL"
    assert symbol["worst"]["symbol"] == "XLE"

    # Sector contribution reports partial coverage (ZZZZ has no sector).
    sector = report["sector_contribution"]
    assert sector["status"] == "PARTIAL"

    # Trades: buys attributed, sells left NOT_EVALUATED (never fabricated).
    trade = report["trade_contribution"]
    assert trade["status"] == "EVALUATED"
    assert trade["unattributed_sells"] == 1

    # Risk decisions counted; P/L impact never fabricated.
    risk = report["risk_decision_impact"]
    assert risk["status"] == "EVALUATED"
    assert risk["total_rejected_decisions"] == 1
    assert risk["pl_impact"]["status"] == "NOT_EVALUATED"

    # Realized/unrealized split adds up.
    split = report["realized_vs_unrealized"]
    assert split["status"] == "EVALUATED"
    assert split["total_pl"] == 550

    # Endpoint returns policy fields.
    assert_policy(report)
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
    empty_report = performance_attribution(limit=100)
    empty_counts_after = table_counts(empty_database_path)

    # No writes even when nothing can be evaluated.
    assert empty_counts_before == empty_counts_after

    # Every section is still present.
    assert_sections(empty_report)

    # Missing data is handled cleanly: never fabricated, always NOT_EVALUATED.
    assert empty_report["symbol_contribution"]["status"] == "NOT_EVALUATED"
    assert empty_report["sector_contribution"]["status"] == "NOT_EVALUATED"
    assert empty_report["trade_contribution"]["status"] == "NOT_EVALUATED"
    assert empty_report["risk_decision_impact"]["status"] == "NOT_EVALUATED"
    assert empty_report["realized_vs_unrealized"]["status"] == "NOT_EVALUATED"
    assert empty_report["portfolio_return_drivers"]["status"] == "NOT_EVALUATED"
    assert (
        empty_report["attribution_confidence"]["confidence_level"] == "NONE"
    )
    assert_policy(empty_report)
finally:
    connection.DATABASE_PATH = original_database_path
    cleanup_database(empty_database_path)


print("PerformanceAttribution API test passed.")
