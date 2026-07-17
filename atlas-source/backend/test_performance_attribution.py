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
from engines.performance_attribution_engine import PerformanceAttributionEngine


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

POSITIONS = {
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

CONSTRUCTION_TARGETS = [
    {"ticker": "AAPL", "sector": "Technology", "suggested_allocation": 30},
    {"ticker": "MSFT", "sector": "Technology", "suggested_allocation": 20},
    {"ticker": "XLE", "sector": "Energy", "suggested_allocation": 20},
]

STATE = {
    "fund_status": "RUNNING",
    "cash": 500,
    "positions": POSITIONS,
    "realized_pl": 150,
    "last_update": "2026-07-03T10:15:00",
    "updated_at": "2026-07-03T10:15:00",
}

SNAPSHOTS = [{
    "as_of": "2026-07-03T10:15:00",
    "date": "2026-07-03T10:15:00",
    "cycle_id": "cycle-3",
    "cash": 500,
    "positions": POSITIONS,
    "current_value": 9500,
    "realized_pl": 150,
    "unrealized_pl": 400,
    "portfolio_value": 10000,
    "daily_return": 0.5,
    "total_return": 0,
}]

ORDERS = [
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
]

RISK_DECISIONS = [
    {
        "decision_id": "risk-approved-aapl",
        "cycle_id": "cycle-3",
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": 5,
        "verdict": "APPROVED",
        "checks": {
            "checks": [
                {
                    "rule": "max_position_size",
                    "status": "APPROVED",
                    "limit": 0.25,
                    "measured": 0.2,
                    "reason": "Within limit.",
                }
            ],
            "rejections": [],
            "reasons": [],
        },
        "created_at": "2026-07-03T10:10:00",
    },
    {
        "decision_id": "risk-rejected-msft",
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
        "created_at": "2026-07-03T10:11:00",
    },
]

LEARNING = [{
    "at": "2026-07-03T10:16:00",
    "cycle_id": "cycle-3",
    "lesson": "Attribution seed.",
    "details": {
        "learning_summary": {
            "recommended_symbols": ["AAPL", "MSFT", "XLE", "ZZZZ"],
            "construction_targets": CONSTRUCTION_TARGETS,
        },
    },
}]


engine = PerformanceAttributionEngine()


def injected_report():
    return engine.generate(
        state=dict(STATE),
        snapshots=[dict(SNAPSHOTS[0])],
        orders=[dict(order) for order in ORDERS],
        risk_decisions=[dict(decision) for decision in RISK_DECISIONS],
        learning=[dict(LEARNING[0])],
        activity=[],
        limit=100,
    )


report = injected_report()
repeated = injected_report()

# Deterministic: identical output for identical inputs.
assert report == repeated, "Attribution must be deterministic."

# Policy safety fields.
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

# All required sections present.
for section in (
    "portfolio_return_drivers",
    "symbol_contribution",
    "trade_contribution",
    "sector_contribution",
    "risk_decision_impact",
    "cash_drag",
    "realized_vs_unrealized",
    "attribution_confidence",
    "policy",
):
    assert section in report, section

# --- Symbol contribution math ---
symbol = report["symbol_contribution"]
assert symbol["status"] == "EVALUATED"
assert symbol["total_unrealized_pl"] == 400
by_symbol = {item["symbol"]: item for item in symbol["items"]}
assert by_symbol["AAPL"]["unrealized_pl"] == 500
assert by_symbol["AAPL"]["contribution_to_unrealized_percent"] == 125.0
assert by_symbol["AAPL"]["contribution_to_portfolio_percent"] == 5.0
assert by_symbol["AAPL"]["result"] == "HELPED"
assert by_symbol["XLE"]["contribution_to_unrealized_percent"] == -50.0
assert by_symbol["XLE"]["result"] == "HURT"
assert by_symbol["ZZZZ"]["result"] == "FLAT"
assert symbol["best"]["symbol"] == "AAPL"
assert symbol["worst"]["symbol"] == "XLE"

# --- Sector contribution with missing-sector handling ---
sector = report["sector_contribution"]
assert sector["status"] == "PARTIAL"
by_sector = {item["sector"]: item for item in sector["items"]}
assert by_sector["Technology"]["unrealized_pl"] == 600
assert by_sector["Technology"]["contribution_to_unrealized_percent"] == 150.0
assert by_sector["Technology"]["result"] == "HELPED"
assert by_sector["Energy"]["unrealized_pl"] == -200
assert by_sector["Energy"]["result"] == "HURT"
assert sector["best"]["sector"] == "Technology"
assert sector["worst"]["sector"] == "Energy"
assert sector["missing_sector"] == [
    {
        "symbol": "ZZZZ",
        "status": "NOT_EVALUATED",
        "reason": "Sector metadata is unavailable for this symbol.",
    }
]

# --- Trade contribution: buys attributed, sells NOT_EVALUATED ---
trade = report["trade_contribution"]
assert trade["status"] == "EVALUATED"
assert trade["buy_count"] == 1
assert trade["sell_count"] == 1
assert trade["unattributed_sells"] == 1
trades_by_id = {item["order_id"]: item for item in trade["items"]}
buy = trades_by_id["order-buy-aapl"]
assert buy["attribution_status"] == "EVALUATED"
assert buy["contribution"]["type"] == "open_position_unrealized_pl"
assert buy["contribution"]["unrealized_pl"] == 500
sell = trades_by_id["order-sell-tsla"]
assert sell["attribution_status"] == "NOT_EVALUATED"
assert sell["result"] == "NOT_EVALUATED"
assert "Realized P/L is not stored per symbol" in sell["reason"]

# --- Risk-decision impact: counts blockers, never fabricates P/L ---
risk = report["risk_decision_impact"]
assert risk["status"] == "EVALUATED"
assert risk["total_decisions"] == 2
assert risk["total_rejected_decisions"] == 1
rule_names = {row["rule"] for row in risk["by_rule"]}
assert "affordability" in rule_names
assert risk["prevented_exposure"]["rejected_orders"] == [
    {"symbol": "MSFT", "side": "BUY", "quantity": 20, "cycle_id": "cycle-3"}
]
assert risk["pl_impact"]["status"] == "NOT_EVALUATED"

# --- Cash drag ---
cash = report["cash_drag"]
assert cash["status"] == "EVALUATED"
assert cash["cash_weight_percent"] == 5.0
assert cash["invested_weight_percent"] == 95.0
assert cash["cash_pl_contribution"] == 0.0

# --- Realized vs unrealized split ---
split = report["realized_vs_unrealized"]
assert split["status"] == "EVALUATED"
assert split["realized_pl"] == 150
assert split["unrealized_pl"] == 400
assert split["total_pl"] == 550
assert split["realized_share_percent"] == 27.2727
assert split["unrealized_share_percent"] == 72.7273
assert split["realized_attribution"]["status"] == "NOT_EVALUATED"

# --- Portfolio return drivers ---
drivers = report["portfolio_return_drivers"]
assert drivers["status"] == "EVALUATED"
assert drivers["drivers"][0]["symbol"] == "AAPL"
assert drivers["top_positive_driver"]["symbol"] == "AAPL"
assert drivers["top_negative_driver"]["symbol"] == "XLE"

# --- Attribution confidence limitations ---
confidence = report["attribution_confidence"]
assert confidence["status"] == "EVALUATED"
assert confidence["confidence_level"] == "LOW"
limitation_areas = {item["area"] for item in confidence["limitations"]}
assert "realized_pl_attribution" in limitation_areas
assert "trade_sell_attribution" in limitation_areas
assert "risk_decision_pl_impact" in limitation_areas
assert "sector_attribution" in limitation_areas


# ----------------------------------------------------------------------
# Missing-data behavior: never fabricated, always NOT_EVALUATED.
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
assert empty_report["symbol_contribution"]["status"] == "NOT_EVALUATED"
assert empty_report["sector_contribution"]["status"] == "NOT_EVALUATED"
assert empty_report["trade_contribution"]["status"] == "NOT_EVALUATED"
assert empty_report["risk_decision_impact"]["status"] == "NOT_EVALUATED"
assert empty_report["cash_drag"]["status"] == "EVALUATED"  # cash present, no positions
assert empty_report["cash_drag"]["invested_weight_percent"] == 0.0
assert empty_report["realized_vs_unrealized"]["status"] == "NOT_EVALUATED"
assert empty_report["portfolio_return_drivers"]["status"] == "NOT_EVALUATED"
assert empty_report["attribution_confidence"]["confidence_level"] == "NONE"
assert REQUIRED_POLICY_KEYS.issubset(empty_report["policy"].keys())


# ----------------------------------------------------------------------
# Database-backed test: read-only, deterministic, no writes.
# ----------------------------------------------------------------------
original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()

    policy = {"paper_only": True, "broker_integration": False, "real_money": False}
    save_paper_fund_state({**STATE, "policy": policy})
    save_paper_fund_snapshot({**SNAPSHOTS[0], "price_source": "test", "policy": policy})
    for order in ORDERS:
        save_paper_fund_order({**order, "policy": policy})
    for decision in RISK_DECISIONS:
        save_risk_decision({**decision, "policy": policy})
    add_paper_fund_learning(LEARNING[0])

    counts_before = table_counts(database_path)
    db_report = engine.generate(limit=100)
    db_repeated = engine.generate(limit=100)
    counts_after = table_counts(database_path)

    # Read-only: no rows are written by attribution.
    assert counts_before == counts_after
    # Deterministic over repository-backed reads.
    assert db_report == db_repeated

    assert db_report["symbol_contribution"]["total_unrealized_pl"] == 400
    assert db_report["realized_vs_unrealized"]["total_pl"] == 550
    assert db_report["trade_contribution"]["unattributed_sells"] == 1
    assert db_report["risk_decision_impact"]["total_rejected_decisions"] == 1
    assert REQUIRED_POLICY_KEYS.issubset(db_report["policy"].keys())
finally:
    connection.DATABASE_PATH = original_database_path
    cleanup_database(database_path)


print("PerformanceAttributionEngine test passed.")
