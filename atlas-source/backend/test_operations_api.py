import os
import tempfile

import database.connection as connection
from database.migrator import run_migrations
from backend.status import count_rows
from engines.operations_engine import OperationsEngine

# Deterministic offline provider so the endpoint never touches the network.
os.environ["MARKET_DATA_PROVIDER"] = "mock"

from api.main import operations_center


REQUIRED_SECTIONS = (
    "overall_health",
    "scheduler",
    "market_data",
    "paper_fund",
    "learning",
    "database",
    "uptime",
    "recent_errors",
    "operational_recommendations",
    "warnings",
    "operational_mode",
    "policy",
)


original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()

    tables = list(OperationsEngine.DEFAULT_TABLES)
    before = {table: count_rows(table) for table in tables}

    # The endpoint delegates directly to OperationsEngine().report().
    report = operations_center()

    # Every requested section is present.
    for section in REQUIRED_SECTIONS:
        assert section in report, section

    assert report["version"] == "operations-center-v1"
    assert report["overall_health"]["status"] in {
        "Healthy",
        "Warning",
        "Degraded",
        "Offline",
    }
    # Read-only, paper-only, no broker/real money.
    assert report["policy"]["read_only"] is True
    assert report["policy"]["writes"] is False
    assert report["policy"]["broker_integration"] is False
    assert report["policy"]["real_money"] is False
    # Offline default -> mock provider, OFFLINE_MOCK mode.
    assert report["operational_mode"]["mode"] == "OFFLINE_MOCK"
    assert report["operational_mode"]["broker_integration"] is False
    # Each subsystem section resolved (EVALUATED) or gracefully degraded.
    for section in ("scheduler", "market_data", "paper_fund", "learning", "database"):
        assert report[section]["status"] in {"EVALUATED", "Unavailable"}
    assert isinstance(report["recent_errors"], list)
    assert isinstance(report["warnings"], list)
    assert isinstance(report["operational_recommendations"], list)

    # The endpoint must not write to the database.
    after = {table: count_rows(table) for table in tables}
    assert before == after, "GET /operations must not write to the database."
finally:
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(database_path)
    for candidate in (database_path, f"{database_path}-wal", f"{database_path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


print("Operations API test passed.")
