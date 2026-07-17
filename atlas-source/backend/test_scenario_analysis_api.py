import os
import sqlite3
import tempfile

import database.connection as connection
from database.migrator import run_migrations
from database.repository import (
    add_paper_fund_activity,
    add_paper_fund_learning,
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
            "cost_basis": 100,
            "current_price": 100,
            "current_value": 2000,
            "unrealized_pl": 0,
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
        "realized_pl": 0,
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
        "realized_pl": 0,
        "unrealized_pl": 600,
        "portfolio_value": 10000,
        "daily_return": 0.5,
        "total_return": 0,
        "price_source": "test_live_prices",
        "policy": policy,
    })

    construction_targets = [
        {"ticker": "AAPL", "sector": "Technology", "suggested_allocation": 30},
        {"ticker": "MSFT", "sector": "Technology", "suggested_allocation": 20},
        {"ticker": "XLE", "sector": "Energy", "suggested_allocation": 20},
    ]
    add_paper_fund_learning({
        "at": "2026-07-03T10:16:00",
        "cycle_id": "cycle-3",
        "lesson": "Scenario analysis API seed.",
        "details": {
            "learning_summary": {
                "recommended_symbols": ["AAPL", "MSFT", "XLE", "ZZZZ"],
                "construction_targets": construction_targets,
            },
        },
    })
    add_paper_fund_activity({
        "at": "2026-07-03T10:12:00",
        "cycle_id": "cycle-3",
        "activity_type": "CONSTRUCTION_BUILT",
        "message": "Construction summary built.",
        "details": {
            "construction_summary": {
                "recommended_allocations": construction_targets,
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


REQUIRED_POLICY_KEYS = {
    "read_only",
    "descriptive_only",
    "paper_only",
    "broker_integration",
    "real_money",
    "does_not_modify_recommendations",
    "does_not_modify_trades",
    "does_not_modify_risk_limits",
}

EXPECTED_SCENARIOS = [
    "Market -20%",
    "Market -10%",
    "Market -5%",
    "Market +5%",
    "Market +10%",
    "Market +20%",
]


from api.main import app, scenario_analysis

# Route is registered as a read-only GET.
assert any(
    route.path == "/scenario-analysis" and "GET" in route.methods
    for route in app.routes
), "GET /scenario-analysis route must be registered."


def assert_policy(report):
    policy = report["policy"]
    assert REQUIRED_POLICY_KEYS.issubset(policy.keys())
    assert policy["read_only"] is True
    assert policy["descriptive_only"] is True
    assert policy["paper_only"] is True
    assert policy["broker_integration"] is False
    assert policy["real_money"] is False
    assert policy["does_not_modify_recommendations"] is True
    assert policy["does_not_modify_trades"] is True
    assert policy["does_not_modify_risk_limits"] is True


original_database_path = connection.DATABASE_PATH

# ----------------------------------------------------------------------
# Seeded database: endpoint returns full scenario analysis with no writes.
# ----------------------------------------------------------------------
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()
    seed_portfolio_history()

    counts_before = table_counts(database_path)
    report = scenario_analysis(limit=100)
    repeated = scenario_analysis(limit=100)
    counts_after = table_counts(database_path)

    # Endpoint does not write to the database.
    assert counts_before == counts_after
    # Deterministic across calls.
    assert report == repeated

    # Endpoint returns all six scenarios.
    scenario_names = [scenario["name"] for scenario in report["scenarios"]]
    assert scenario_names == EXPECTED_SCENARIOS, scenario_names
    assert all(
        scenario["status"] == "EVALUATED" for scenario in report["scenarios"]
    )

    # Endpoint returns a stress summary with best / base / worst.
    summary = report["stress_summary"]
    assert summary["status"] == "EVALUATED"
    assert summary["best_case"]["name"] == "Market +20%"
    assert summary["worst_case"]["name"] == "Market -20%"
    assert summary["base_case"]["status"] == "EVALUATED"
    assert summary["portfolio_resilience_score"]["status"] == "EVALUATED"

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
    empty_report = scenario_analysis(limit=100)
    empty_counts_after = table_counts(empty_database_path)

    # No writes even when nothing can be evaluated.
    assert empty_counts_before == empty_counts_after

    # Missing data is handled cleanly: never fabricated, always NOT_EVALUATED.
    assert len(empty_report["scenarios"]) == 6
    for scenario in empty_report["scenarios"]:
        assert scenario["status"] == "NOT_EVALUATED"
        assert scenario["estimated_portfolio_value"]["value"] is None
    assert empty_report["base_case"]["status"] == "NOT_EVALUATED"
    assert empty_report["stress_summary"]["status"] == "NOT_EVALUATED"
    assert (
        empty_report["stress_summary"]["portfolio_resilience_score"]["status"]
        == "NOT_EVALUATED"
    )
    assert_policy(empty_report)
finally:
    connection.DATABASE_PATH = original_database_path
    cleanup_database(empty_database_path)


print("ScenarioAnalysis API test passed.")
