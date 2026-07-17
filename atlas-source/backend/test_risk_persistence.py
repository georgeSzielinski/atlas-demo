import os
import tempfile

import database.connection as connection
from database.migrator import run_migrations
from database.repository import get_recent_risk_decisions, save_risk_decision
from engines.risk_management_engine import RiskManagementEngine


def cleanup_database(path):
    connection._wal_initialized_paths.discard(path)
    for candidate in (path, f"{path}-wal", f"{path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


engine = RiskManagementEngine()
portfolio = {
    "cash": 5000,
    "positions": {
        "AAPL": {"quantity": 10, "price": 100, "sector": "Technology"},
    },
}
limits = {
    "max_position_size": 1,
    "max_portfolio_exposure": 1,
    "minimum_cash_reserve": 0,
    "max_sector_exposure": 1,
    "max_position_count": 10,
    "max_correlation": 0.75,
}

approved = engine.evaluate(
    {"symbol": "MSFT", "side": "BUY", "quantity": 5, "price": 100, "sector": "Technology"},
    portfolio=portfolio,
    limits=limits,
)
rejected = engine.evaluate(
    {"symbol": "AAPL", "side": "SELL", "quantity": 11, "price": 100, "sector": "Technology"},
    portfolio=portfolio,
    limits=limits,
)

assert approved["status"] == "APPROVED"
assert rejected["status"] == "REJECTED"

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()

    approved_decision = {
        **approved,
        "decision_id": "risk-approved-001",
        "run_id": 42,
        "created_at": "2026-07-04T10:00:00",
    }
    rejected_decision = {
        **rejected,
        "decision_id": "risk-rejected-001",
        "cycle_id": "cycle-123",
        "created_at": "2026-07-04T10:01:00",
    }

    assert save_risk_decision(approved_decision) == "risk-approved-001"
    assert save_risk_decision(rejected_decision) == "risk-rejected-001"

    recent = get_recent_risk_decisions(limit=10)
    assert [item["decision_id"] for item in recent] == [
        "risk-rejected-001",
        "risk-approved-001",
    ]

    rejected_row = recent[0]
    assert rejected_row["cycle_id"] == "cycle-123"
    assert rejected_row["run_id"] is None
    assert rejected_row["symbol"] == "AAPL"
    assert rejected_row["side"] == "SELL"
    assert rejected_row["quantity"] == 11
    assert rejected_row["verdict"] == "REJECTED"
    assert rejected_row["checks"] == rejected["checks"]
    assert rejected_row["policy"] == {
        "paper_only": True,
        "broker_integration": False,
        "real_money": False,
        "human_approval_required_for_real_trading": True,
    }

    approved_row = recent[1]
    assert approved_row["cycle_id"] is None
    assert approved_row["run_id"] == 42
    assert approved_row["symbol"] == "MSFT"
    assert approved_row["side"] == "BUY"
    assert approved_row["quantity"] == 5
    assert approved_row["verdict"] == "APPROVED"
    assert approved_row["checks"] == approved["checks"]
    assert approved_row["policy"]["paper_only"] is True

    latest_only = get_recent_risk_decisions(limit=1)
    assert len(latest_only) == 1
    assert latest_only[0]["decision_id"] == "risk-rejected-001"
finally:
    connection.DATABASE_PATH = original_database_path
    cleanup_database(database_path)


print("Risk persistence test passed.")
