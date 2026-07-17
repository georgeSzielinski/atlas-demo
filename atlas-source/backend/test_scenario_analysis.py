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
from engines.scenario_analysis_engine import ScenarioAnalysisEngine


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
    learning_policy = {
        "descriptive_only": True,
        "does_not_modify_recommendations": True,
        "does_not_modify_trades": True,
        "paper_only": True,
        "real_money": False,
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
        "lesson": "Scenario analysis seed.",
        "details": {
            "learning_summary": {
                "recommended_symbols": ["AAPL", "MSFT", "XLE", "ZZZZ"],
                "construction_targets": construction_targets,
                "policy": learning_policy,
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

engine = ScenarioAnalysisEngine()


# ----------------------------------------------------------------------
# Pure injected-data tests (no database access at all).
# ----------------------------------------------------------------------
SEED_POSITIONS = {
    "AAPL": {"ticker": "AAPL", "current_price": 100, "current_value": 5000},
    "MSFT": {"ticker": "MSFT", "current_price": 100, "current_value": 2000},
    "XLE": {"ticker": "XLE", "current_price": 100, "current_value": 2000},
    "ZZZZ": {"ticker": "ZZZZ", "current_price": 100, "current_value": 500},
}


def injected_report():
    return engine.generate(
        state={
            "fund_status": "RUNNING",
            "cash": 500,
            "positions": SEED_POSITIONS,
            "last_update": "2026-07-03T10:15:00",
        },
        snapshots=[{
            "as_of": "2026-07-03T10:15:00",
            "cycle_id": "cycle-3",
            "cash": 500,
            "positions": SEED_POSITIONS,
            "current_value": 9500,
            "portfolio_value": 10000,
            "unrealized_pl": 600,
            "total_return": 0,
        }],
        orders=[],
        risk_decisions=[],
        learning=[{
            "at": "2026-07-03T10:16:00",
            "cycle_id": "cycle-3",
            "details": {
                "learning_summary": {
                    "recommended_symbols": ["AAPL", "MSFT", "XLE", "ZZZZ"],
                    "construction_targets": [
                        {"ticker": "AAPL", "sector": "Technology"},
                        {"ticker": "MSFT", "sector": "Technology"},
                        {"ticker": "XLE", "sector": "Energy"},
                    ],
                },
            },
        }],
        activity=[],
        limit=100,
    )


report = injected_report()
repeated = injected_report()

# Deterministic: identical output for identical inputs.
assert report == repeated, "Scenario analysis must be deterministic."

# Policy safety flags.
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

# All six market scenarios present and in deterministic order.
scenario_names = [scenario["name"] for scenario in report["scenarios"]]
assert scenario_names == [
    "Market -20%",
    "Market -10%",
    "Market -5%",
    "Market +5%",
    "Market +10%",
    "Market +20%",
], scenario_names
assert all(scenario["status"] == "EVALUATED" for scenario in report["scenarios"])

scenarios_by_name = {scenario["name"]: scenario for scenario in report["scenarios"]}

# Concentration + cash + value math for Market -10%.
down10 = scenarios_by_name["Market -10%"]
assert down10["estimated_portfolio_value"]["value"] == 9050.0
assert down10["estimated_portfolio_return"]["value"] == -9.5
assert down10["estimated_drawdown"]["value"] == 9.5
assert down10["estimated_cash_percent"]["value"] == 5.5249
assert down10["estimated_concentration"]["status"] == "FAIL"
assert down10["estimated_concentration"]["value"] == 49.7238
assert down10["estimated_largest_position"]["symbol"] == "AAPL"

# Up scenario math for Market +20%.
up20 = scenarios_by_name["Market +20%"]
assert up20["estimated_portfolio_value"]["value"] == 11900.0
assert up20["estimated_portfolio_return"]["value"] == 19.0
assert up20["estimated_drawdown"]["value"] == 0.0

# Constraint violations: position size + sector concentration under stress.
down20 = scenarios_by_name["Market -20%"]
violated = [
    violation
    for violation in down20["constraint_violations"]
    if violation["status"] == "VIOLATED"
]
violated_constraints = {violation["constraint"] for violation in violated}
assert "max_position_size" in violated_constraints
assert "max_sector_exposure" in violated_constraints

# Risk utilization is reused from the risk-management default limits.
utilization = down20["estimated_risk_utilization"]
assert utilization["status"] == "EVALUATED"
assert utilization["limits"]["max_position_size"] == 0.25
by_limit = {row["limit_name"]: row for row in utilization["by_limit"]}
assert by_limit["max_position_size"]["status"] == "BREACH"

# Stress summary: best / base / worst.
summary = report["stress_summary"]
assert summary["status"] == "EVALUATED"
assert summary["best_case"]["name"] == "Market +20%"
assert summary["worst_case"]["name"] == "Market -20%"
assert summary["base_case"]["status"] == "EVALUATED"
assert summary["base_case"]["estimated_portfolio_value"]["value"] == 10000.0

# Top contributors ranked by holding value.
top = summary["top_contributors"]
assert [item["symbol"] for item in top] == ["AAPL", "MSFT", "XLE"]
assert top[0]["weight_percent"] == round(5000 / 9500 * 100, 4)

# Resilience score deterministic and bounded.
resilience = summary["portfolio_resilience_score"]
assert resilience["status"] == "EVALUATED"
assert isinstance(resilience["score"], int)
assert 0 <= resilience["score"] <= 100
assert resilience["deterministic"] is True
assert resilience["rating"] in {"RESILIENT", "MODERATE", "FRAGILE"}

# Largest risks + watch items surface stress breaches.
assert any(
    risk["type"] == "STRESS_CONSTRAINT_BREACH"
    for risk in summary["largest_risks"]
)
assert any(
    item.get("type") == "STRESS_WATCH"
    for item in summary["watch_items"]
)


# ----------------------------------------------------------------------
# Missing-data behavior: everything NOT_EVALUATED, never fabricated.
# ----------------------------------------------------------------------
empty_report = engine.generate(
    state={"fund_status": "READY", "cash": 10000, "positions": {}},
    snapshots=[],
    orders=[],
    risk_decisions=[],
    learning=[],
    activity=[],
    limit=100,
)
assert empty_report["base_portfolio"]["status"] == "NOT_EVALUATED"
assert empty_report["base_case"]["status"] == "NOT_EVALUATED"
assert empty_report["stress_summary"]["status"] == "NOT_EVALUATED"
assert (
    empty_report["stress_summary"]["portfolio_resilience_score"]["status"]
    == "NOT_EVALUATED"
)
for scenario in empty_report["scenarios"]:
    assert scenario["status"] == "NOT_EVALUATED"
    assert scenario["estimated_portfolio_value"]["status"] == "NOT_EVALUATED"
    assert scenario["estimated_portfolio_value"]["value"] is None
    assert scenario["estimated_concentration"]["status"] == "NOT_EVALUATED"


# ----------------------------------------------------------------------
# Database-backed test: no writes, deterministic, reads existing helpers.
# ----------------------------------------------------------------------
original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()
    seed_portfolio_history()

    counts_before = table_counts(database_path)
    db_report = engine.generate(limit=100)
    db_repeated = engine.generate(limit=100)
    counts_after = table_counts(database_path)

    # Read-only: no database rows are written by scenario analysis.
    assert counts_before == counts_after
    # Deterministic across repository-backed reads.
    assert db_report == db_repeated

    db_by_name = {
        scenario["name"]: scenario for scenario in db_report["scenarios"]
    }
    assert len(db_by_name) == 6
    assert db_by_name["Market -10%"]["estimated_portfolio_value"]["value"] == 9050.0
    assert db_report["stress_summary"]["best_case"]["name"] == "Market +20%"
    assert db_report["stress_summary"]["worst_case"]["name"] == "Market -20%"
    assert REQUIRED_POLICY_KEYS.issubset(db_report["policy"].keys())
finally:
    connection.DATABASE_PATH = original_database_path
    cleanup_database(database_path)


print("ScenarioAnalysisEngine test passed.")
