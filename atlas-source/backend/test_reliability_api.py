import os
import tempfile

import database.connection as connection
from database.migrator import run_migrations
from backend.status import count_rows
from engines.reliability_engine import ReliabilityEngine

# Deterministic offline provider so the endpoint never touches the network.
os.environ["MARKET_DATA_PROVIDER"] = "mock"

from api.main import app, reliability_center


REQUIRED_KEYS = (
    "overall_reliability",
    "confidence",
    "subsystem_scores",
    "subsystem_weights",
    "contributors",
    "scheduler_reliability",
    "market_data_reliability",
    "provider_reliability",
    "database_reliability",
    "paper_fund_reliability",
    "learning_reliability",
    "api_reliability",
    "warning_count",
    "error_count",
    "critical_count",
    "consecutive_failures",
    "uptime",
    "availability",
    "recent_incidents",
    "reliability_recommendations",
    "reliability_trend",
    "operational_policy",
)


# ----------------------------------------------------------------------
# Route registration: GET /reliability is exposed exactly once.
# ----------------------------------------------------------------------
reliability_routes = [
    route for route in app.routes if getattr(route, "path", "") == "/reliability"
]
assert len(reliability_routes) == 1
assert "GET" in reliability_routes[0].methods


original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()

    tables = [
        "atlas_runs",
        "recommendations",
        "runtime_states",
        "market_data_snapshots",
        "paper_fund_activity",
    ]
    before = {table: count_rows(table) for table in tables}

    # The endpoint delegates directly to ReliabilityEngine().report().
    report = reliability_center()

    for key in REQUIRED_KEYS:
        assert key in report, key

    assert report["version"] == "reliability-framework-v1"
    assert report["overall_reliability"]["grade"] in {
        "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F",
        "NOT_EVALUATED",
    }
    assert report["overall_reliability"]["status"] in {
        "Reliable", "Watch", "Degraded", "Critical", "NOT_EVALUATED",
    }
    assert report["confidence"]["level"] in {"HIGH", "MEDIUM", "LOW"}
    assert report["operational_policy"]["read_only"] is True
    assert report["operational_policy"]["writes"] is False
    assert report["operational_policy"]["broker_integration"] is False
    assert report["operational_policy"]["real_money"] is False
    assert isinstance(report["recent_incidents"], list)
    assert isinstance(report["reliability_recommendations"], list)
    assert isinstance(report["contributors"], list)
    for name in ReliabilityEngine.SUBSYSTEMS:
        assert name in report["subsystem_scores"]
        assert name in report["subsystem_weights"]

    # The endpoint must not write to the database.
    after = {table: count_rows(table) for table in tables}
    assert before == after, "GET /reliability must not write to the database."
finally:
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(database_path)
    for candidate in (database_path, f"{database_path}-wal", f"{database_path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


print("Reliability API test passed.")
