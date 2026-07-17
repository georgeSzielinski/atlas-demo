import os
import tempfile

import database.connection as connection
from api.main import risk_decisions, risk_limits
from database.connection import get_connection
from database.migrator import run_migrations
from database.repository import save_risk_decision
from engines.risk_management_engine import RiskManagementEngine


def cleanup_database(path):
    connection._wal_initialized_paths.discard(path)
    for candidate in (path, f"{path}-wal", f"{path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


def table_counts():
    db = get_connection()
    try:
        return {
            table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "schema_migrations",
                "risk_decisions",
                "paper_fund_orders",
                "paper_fund_snapshots",
                "paper_fund_activity",
            )
        }
    finally:
        db.close()


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
    {"symbol": "MSFT", "side": "BUY", "quantity": 5, "price": 100},
    portfolio=portfolio,
    limits=limits,
)
rejected = engine.evaluate(
    {"symbol": "AAPL", "side": "SELL", "quantity": 11, "price": 100},
    portfolio=portfolio,
    limits=limits,
)

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()

    save_risk_decision({
        **approved,
        "decision_id": "api-risk-approved",
        "run_id": 7,
        "created_at": "2026-07-04T10:00:00",
    })
    save_risk_decision({
        **rejected,
        "decision_id": "api-risk-rejected",
        "cycle_id": "cycle-api",
        "created_at": "2026-07-04T10:01:00",
    })

    before = table_counts()

    limits_response = risk_limits()
    assert limits_response["limits"] == RiskManagementEngine.DEFAULT_LIMITS
    assert limits_response["deterministic"] is True
    assert limits_response["read_only"] is True
    assert limits_response["paper_only"] is True
    assert limits_response["broker_integration"] is False
    assert limits_response["real_money"] is False
    assert limits_response["human_approval_required_for_real_trading"] is True

    decisions_response = risk_decisions(limit=10)
    assert decisions_response["read_only"] is True
    assert decisions_response["paper_only"] is True
    assert decisions_response["broker_integration"] is False
    assert decisions_response["real_money"] is False
    assert decisions_response["count"] == 2
    assert [item["decision_id"] for item in decisions_response["decisions"]] == [
        "api-risk-rejected",
        "api-risk-approved",
    ]

    rejected_row = decisions_response["decisions"][0]
    assert rejected_row["verdict"] == "REJECTED"
    assert rejected_row["checks"] == rejected["checks"]
    assert rejected_row["policy"]["paper_only"] is True

    approved_row = decisions_response["decisions"][1]
    assert approved_row["verdict"] == "APPROVED"
    assert approved_row["checks"] == approved["checks"]
    assert approved_row["run_id"] == 7

    latest_only = risk_decisions(limit=1)
    assert latest_only["count"] == 1
    assert latest_only["decisions"][0]["decision_id"] == "api-risk-rejected"

    after = table_counts()
    assert after == before
finally:
    connection.DATABASE_PATH = original_database_path
    cleanup_database(database_path)


print("Risk API test passed.")
