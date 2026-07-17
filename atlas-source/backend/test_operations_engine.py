import os
import tempfile
from datetime import datetime

import database.connection as connection
from database.migrator import run_migrations
from backend.status import count_rows
from engines.operations_engine import OperationsEngine


# ----------------------------------------------------------------------
# Deterministic fakes: every collaborator is injectable, so no real DB,
# network, scheduler loop, or paper fund is touched by these tests.
# ----------------------------------------------------------------------
class FakeScheduler:
    def __init__(self, status):
        self._status = status

    def status(self):
        return dict(self._status)


class RaisingScheduler:
    def status(self):
        raise RuntimeError("scheduler boom")


class FakeFund:
    def __init__(self, status):
        self._status = status

    def status(self):
        return dict(self._status)


class RaisingFund:
    def status(self):
        raise RuntimeError("fund boom")


class FakeMarketManager:
    def __init__(self, health, snapshot, entries=(), latest_age=10):
        self._health = health
        self._snapshot = snapshot
        self._entries = list(entries)
        self._latest_age = latest_age

    def health(self):
        return dict(self._health)

    def cache_status(self):
        return {"entries": self._entries, "stats": {"latest_age": self._latest_age}}

    def snapshot(self):
        return dict(self._snapshot)


class RaisingMarketManager:
    def health(self):
        raise RuntimeError("market boom")

    def cache_status(self):
        raise RuntimeError("market boom")

    def snapshot(self):
        raise RuntimeError("market boom")


class FakeSettings:
    def __init__(self, auto_fund=False, scheduler=False, data_provider="mock"):
        self.AUTO_FUND_ENABLED = auto_fund
        self.ATLAS_SCHEDULER_ENABLED = scheduler
        self.DATA_PROVIDER = data_provider


class FakePath:
    def __init__(self, exists=True):
        self._exists = exists

    def exists(self):
        return self._exists


def healthy_scheduler():
    return {
        "enabled": True,
        "running": True,
        "owned": True,
        "interval_seconds": 300,
        "started_at": "2026-07-04T09:00:00",
        "tick_count": 5,
        "last_tick_at": "2026-07-04T09:55:00",
        "last_status": "COMPLETED",
        "last_reason": None,
        "error_count": 0,
        "last_error_at": None,
    }


def healthy_market_health():
    return {
        "requested_provider": "yahoo",
        "active_provider": "yahoo",
        "healthy": True,
        "fallback_used": False,
        "offline_capable": False,
        "last_error": None,
    }


def healthy_snapshot():
    return {
        "validated": True,
        "ticker_count": 4,
        "market_status": {"session": "open", "is_open": True},
    }


def healthy_fund():
    return {
        "fund_status": "RUNNING",
        "watchlist": ["AAPL", "MSFT"],
        "cash": 90000,
        "realized_pl": 0,
        "interval_minutes": 30,
        "last_update": "2026-07-04T09:50:00",
        "next_update": "2026-07-04T10:20:00",
        "last_error": None,
        "price_provider": "yahoo",
        "open_positions": {"AAPL": {"quantity": 10}},
        "snapshots": [{"portfolio_value": 100000}],
        "latest_snapshot": {"portfolio_value": 100000, "total_return": 0.0},
        "learning_log": [{"lesson": "Filled orders.", "at": "2026-07-04T09:50:00"}],
    }


def healthy_counts(table):
    return {"atlas_runs": 3, "recommendations": 12}.get(table, 1)


NOW = datetime(2026, 7, 4, 10, 0, 0)

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


def healthy_report(**overrides):
    kwargs = {
        "scheduler": FakeScheduler(healthy_scheduler()),
        "market_manager": FakeMarketManager(
            healthy_market_health(), healthy_snapshot()
        ),
        "fund": FakeFund(healthy_fund()),
        "settings": FakeSettings(auto_fund=True, scheduler=True, data_provider="yahoo"),
        "now": NOW,
        "row_counter": healthy_counts,
        "db_path": FakePath(True),
        "tables": ["atlas_runs", "recommendations"],
    }
    kwargs.update(overrides)
    return OperationsEngine().report(**kwargs)


# ----------------------------------------------------------------------
# Healthy report.
# ----------------------------------------------------------------------
report = healthy_report()

for section in REQUIRED_SECTIONS:
    assert section in report, section

assert report["version"] == "operations-center-v1"
assert report["overall_health"]["status"] == "Healthy"
assert report["scheduler"]["status"] == "EVALUATED"
assert report["market_data"]["status"] == "EVALUATED"
assert report["paper_fund"]["status"] == "EVALUATED"
assert report["learning"]["status"] == "EVALUATED"
assert report["database"]["status"] == "EVALUATED"
assert report["uptime"]["status"] == "EVALUATED"
assert report["recent_errors"] == []
assert report["warnings"] == []
assert report["operational_recommendations"] == ["No operational action required."]
assert report["operational_mode"]["mode"] == "LIVE_PAPER"
assert report["policy"]["read_only"] is True
assert report["policy"]["writes"] is False
assert report["policy"]["broker_integration"] is False
assert report["policy"]["real_money"] is False
# Section projections read from the injected collaborators.
assert report["scheduler"]["tick_count"] == 5
assert report["scheduler"]["auto_fund_enabled"] is True
assert report["market_data"]["active_provider"] == "yahoo"
assert report["paper_fund"]["fund_status"] == "RUNNING"
assert report["paper_fund"]["open_position_count"] == 1
assert report["learning"]["learning_active"] is True
assert report["learning"]["latest_lesson"] == "Filled orders."


# ----------------------------------------------------------------------
# Deterministic output: identical inputs -> identical report.
# ----------------------------------------------------------------------
assert healthy_report() == healthy_report(), "OperationsEngine must be deterministic."


# ----------------------------------------------------------------------
# Degraded report: errors across subsystems drive Degraded overall health.
# ----------------------------------------------------------------------
degraded_scheduler = healthy_scheduler()
degraded_scheduler.update({"error_count": 2, "last_error_at": "2026-07-04T09:30:00"})

degraded_health = healthy_market_health()
degraded_health.update(
    {
        "active_provider": "mock",
        "healthy": False,
        "fallback_used": True,
        "offline_capable": True,
        "last_error": "provider down",
    }
)
degraded_snapshot = healthy_snapshot()
degraded_snapshot["validated"] = False

degraded_fund = healthy_fund()
degraded_fund.update(
    {"fund_status": "ERROR", "last_error": "Validated real market prices unavailable."}
)

degraded = OperationsEngine().report(
    scheduler=FakeScheduler(degraded_scheduler),
    market_manager=FakeMarketManager(
        degraded_health, degraded_snapshot, latest_age=999
    ),
    fund=FakeFund(degraded_fund),
    settings=FakeSettings(auto_fund=False, scheduler=False, data_provider="mock"),
    now=NOW,
    row_counter=healthy_counts,
    db_path=FakePath(True),
    tables=["atlas_runs"],
)

assert degraded["overall_health"]["status"] == "Degraded"


# ----------------------------------------------------------------------
# Merged recent errors: sources combine, de-duplicate, and order stably.
# ----------------------------------------------------------------------
error_sources = [error["source"] for error in degraded["recent_errors"]]
assert error_sources == ["scheduler", "market_data", "paper_fund"]
messages = {error["source"]: error["message"] for error in degraded["recent_errors"]}
assert "2 scheduler tick error(s)" in messages["scheduler"]
assert messages["market_data"] == "provider down"
assert messages["paper_fund"] == "Validated real market prices unavailable."
# de-dup: no repeated (source, message) pairs.
pairs = [(error["source"], error["message"]) for error in degraded["recent_errors"]]
assert len(pairs) == len(set(pairs))
# Operational recommendations reflect the degraded state.
recommendations = degraded["operational_recommendations"]
assert any("resume the fund" in item for item in recommendations)
assert any("scheduler tick errors" in item for item in recommendations)
assert any("MARKET_DATA_PROVIDER=yahoo" in item for item in recommendations)


# ----------------------------------------------------------------------
# Operational mode matrix.
# ----------------------------------------------------------------------
def mode_for(active_provider, auto_fund, data_provider="mock"):
    market = FakeMarketManager(
        {**healthy_market_health(), "active_provider": active_provider},
        healthy_snapshot(),
    )
    result = healthy_report(
        market_manager=market,
        settings=FakeSettings(
            auto_fund=auto_fund, scheduler=True, data_provider=data_provider
        ),
    )
    return result["operational_mode"]["mode"]


assert mode_for("mock", auto_fund=False) == "OFFLINE_MOCK"
assert mode_for("yahoo", auto_fund=False) == "OFFLINE_MOCK"
assert mode_for("mock", auto_fund=True) == "OFFLINE_MOCK"
assert mode_for("yahoo", auto_fund=True) == "LIVE_PAPER"

# Provider falls back to settings.DATA_PROVIDER when market data is unavailable.
mode_unavailable = OperationsEngine().report(
    scheduler=FakeScheduler(healthy_scheduler()),
    market_manager=RaisingMarketManager(),
    fund=FakeFund(healthy_fund()),
    settings=FakeSettings(auto_fund=True, scheduler=True, data_provider="yahoo"),
    now=NOW,
    row_counter=healthy_counts,
    db_path=FakePath(True),
    tables=["atlas_runs"],
)
assert mode_unavailable["operational_mode"]["data_provider"] == "yahoo"


# ----------------------------------------------------------------------
# Warning generation: each non-fatal condition surfaces a stable warning.
# ----------------------------------------------------------------------
warn_health = healthy_market_health()
warn_health.update(
    {"active_provider": "mock", "fallback_used": True, "healthy": False}
)
warn_snapshot = healthy_snapshot()
warn_snapshot["validated"] = False
warn_fund = healthy_fund()
warn_fund["fund_status"] = "PAUSED"

warned = OperationsEngine().report(
    scheduler=FakeScheduler({**healthy_scheduler(), "enabled": False}),
    market_manager=FakeMarketManager(warn_health, warn_snapshot, latest_age=999),
    fund=FakeFund(warn_fund),
    settings=FakeSettings(auto_fund=False, scheduler=False, data_provider="mock"),
    now=NOW,
    row_counter=healthy_counts,
    db_path=FakePath(True),
    tables=["atlas_runs"],
)
warnings = warned["warnings"]
assert warnings == sorted(warnings)
assert "Mock market data provider is active (offline mode)." in warnings
assert "Market data fell back to a non-primary provider." in warnings
assert "Latest market prices are not validated." in warnings
assert "Market data cache is stale." in warnings
assert "Automatic scheduler is disabled." in warnings
assert "Automatic paper-fund operation is disabled." in warnings
assert "Live paper fund is not running (status=PAUSED)." in warnings


# ----------------------------------------------------------------------
# Uptime calculation.
# ----------------------------------------------------------------------
# From the scheduler start time.
assert report["uptime"]["source"] == "scheduler"
assert report["uptime"]["started_at"] == "2026-07-04T09:00:00"
assert report["uptime"]["uptime_seconds"] == 3600
assert report["uptime"]["uptime_human"] == "1h 0s"

# Falls back to the paper fund's last_update when the scheduler never started.
fund_uptime = healthy_report(
    scheduler=FakeScheduler({**healthy_scheduler(), "started_at": None}),
)
assert fund_uptime["uptime"]["source"] == "paper_fund"
assert fund_uptime["uptime"]["started_at"] == "2026-07-04T09:50:00"
assert fund_uptime["uptime"]["uptime_seconds"] == 600

# NOT_STARTED when neither has a start time.
no_uptime = healthy_report(
    scheduler=FakeScheduler({**healthy_scheduler(), "started_at": None}),
    fund=FakeFund({**healthy_fund(), "last_update": None}),
)
assert no_uptime["uptime"]["status"] == "NOT_STARTED"
assert no_uptime["uptime"]["uptime_seconds"] is None


# ----------------------------------------------------------------------
# Database counts: read from the injected counter only.
# ----------------------------------------------------------------------
counted_tables = []


def recording_counter(table):
    counted_tables.append(table)
    return {"atlas_runs": 7, "recommendations": 20, "paper_fund_orders": 4}.get(table, 0)


db_report = healthy_report(
    row_counter=recording_counter,
    tables=["atlas_runs", "recommendations", "paper_fund_orders"],
)
database_section = db_report["database"]
assert database_section["exists"] is True
assert database_section["table_count"] == 3
assert database_section["row_counts"] == {
    "atlas_runs": 7,
    "recommendations": 20,
    "paper_fund_orders": 4,
}
assert database_section["total_rows"] == 31
assert set(counted_tables) == {"atlas_runs", "recommendations", "paper_fund_orders"}

# Missing database path -> exists False, still no raise.
missing_db = healthy_report(db_path=FakePath(False))
assert missing_db["database"]["exists"] is False


# ----------------------------------------------------------------------
# Graceful degradation: an unavailable subsystem never raises.
# ----------------------------------------------------------------------
partial = OperationsEngine().report(
    scheduler=RaisingScheduler(),
    market_manager=FakeMarketManager(healthy_market_health(), healthy_snapshot()),
    fund=RaisingFund(),
    settings=FakeSettings(auto_fund=True, scheduler=True, data_provider="yahoo"),
    now=NOW,
    row_counter=healthy_counts,
    db_path=FakePath(True),
    tables=["atlas_runs"],
)
assert partial["scheduler"]["status"] == "Unavailable"
assert partial["paper_fund"]["status"] == "Unavailable"
assert partial["learning"]["status"] == "Unavailable"
assert partial["market_data"]["status"] == "EVALUATED"
assert partial["overall_health"]["status"] == "Degraded"
partial_error_sources = {error["source"] for error in partial["recent_errors"]}
assert {"scheduler", "paper_fund"}.issubset(partial_error_sources)

# All monitored subsystems unavailable -> Offline (still no raise).
offline = OperationsEngine().report(
    scheduler=RaisingScheduler(),
    market_manager=RaisingMarketManager(),
    fund=RaisingFund(),
    settings=FakeSettings(),
    now=NOW,
    row_counter=lambda table: (_ for _ in ()).throw(RuntimeError("db boom")),
    db_path=FakePath(True),
    tables=["atlas_runs"],
)
assert offline["overall_health"]["status"] == "Offline"


# ----------------------------------------------------------------------
# No DB writes: the real read-only path leaves every table untouched.
# ----------------------------------------------------------------------
original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()

    tables = list(OperationsEngine.DEFAULT_TABLES)
    before = {table: count_rows(table) for table in tables}

    live = OperationsEngine().report(now=NOW)

    after = {table: count_rows(table) for table in tables}
    assert before == after, "OperationsEngine.report must not write to the database."
    # The real path still produces a complete, well-formed report.
    for section in REQUIRED_SECTIONS:
        assert section in live, section
    assert live["policy"]["writes"] is False
    assert live["database"]["status"] == "EVALUATED"
finally:
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(database_path)
    for candidate in (database_path, f"{database_path}-wal", f"{database_path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


print("OperationsEngine test passed.")
