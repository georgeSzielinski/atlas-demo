import os
import tempfile

import database.connection as connection
from database.migrator import run_migrations
from backend.status import count_rows

# Deterministic offline provider so the endpoint never touches the network.
os.environ["MARKET_DATA_PROVIDER"] = "mock"

from api.main import app, dashboard, dashboard_v2


SECTIONS = (
    "operations",
    "reliability",
    "paper_fund",
    "portfolio",
    "performance",
    "scenarios",
    "correlation",
    "learning",
    "risk",
    "market",
    "scheduler",
    "notifications",
    "generated_at",
    "version",
    "policy",
)


# ----------------------------------------------------------------------
# Route registration: GET /dashboard/v2 exists exactly once, and the
# existing GET /dashboard route is preserved untouched.
# ----------------------------------------------------------------------
v2_routes = [r for r in app.routes if getattr(r, "path", "") == "/dashboard/v2"]
assert len(v2_routes) == 1
assert "GET" in v2_routes[0].methods

v1_routes = [r for r in app.routes if getattr(r, "path", "") == "/dashboard"]
assert len(v1_routes) == 1
assert "GET" in v1_routes[0].methods
assert callable(dashboard)  # v1 handler still importable/unchanged


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
        "paper_fund_snapshots",
        "paper_fund_orders",
        "paper_fund_activity",
        "risk_decisions",
        "runtime_states",
    ]
    before = {table: count_rows(table) for table in tables}

    # The endpoint delegates directly to DashboardV2Engine().report().
    report = dashboard_v2()

    for section in SECTIONS:
        assert section in report, section

    assert report["version"] == "dashboard-v2"
    assert report["notifications"] == []
    assert report["policy"]["read_only"] is True
    assert report["policy"]["writes"] is False
    assert isinstance(report["risk"]["decisions"], list)
    assert isinstance(report["correlation"], dict)

    # The endpoint must not write to the database.
    after = {table: count_rows(table) for table in tables}
    assert before == after, "GET /dashboard/v2 must not write to the database."
finally:
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(database_path)
    for candidate in (database_path, f"{database_path}-wal", f"{database_path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


print("Dashboard API test passed.")
