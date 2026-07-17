import os
import tempfile
from datetime import datetime

import database.connection as connection
from database.migrator import run_migrations
from backend.status import count_rows
from engines.dashboard_v2_engine import DashboardV2Engine


NOW = datetime(2026, 7, 4, 10, 0, 0)

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
# Deterministic injectable collaborators.
# ----------------------------------------------------------------------
class FakeOps:
    def report(self):
        return {
            "overall_health": {"status": "Healthy"},
            "market_data": {"status": "EVALUATED", "active_provider": "yahoo"},
            "scheduler": {"status": "EVALUATED", "tick_count": 3},
        }


class FakeReliability:
    def report(self):
        return {"overall_reliability": {"score": 100, "grade": "A+"}}


class FakeFund:
    def status(self):
        return {"fund_status": "RUNNING", "watchlist": ["AAPL"]}


class SpyEngine:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class RaisingOps:
    def report(self):
        raise RuntimeError("ops boom")


class RaisingFund:
    def status(self):
        raise RuntimeError("fund boom")


class RaisingEngine:
    def generate(self, **kwargs):
        raise RuntimeError("engine boom")


# Shared dataset objects; identity is asserted to prove single-load injection.
STATE = {"fund_status": "RUNNING", "watchlist": ["AAPL"], "positions": {}}
SNAPSHOTS = [{"as_of": "2026-07-04T09:50:00", "portfolio_value": 100}]
ORDERS = [{"created_at": "2026-07-04T09:50:00", "ticker": "AAPL"}]
RISK = [{"created_at": "2026-07-04T09:50:00", "verdict": "APPROVED"}]
LEARNING = [{"at": "2026-07-04T09:50:00", "lesson": "x"}]
ACTIVITY = [{"at": "2026-07-04T09:50:00", "activity_type": "CYCLE_COMPLETED"}]


def counting_loaders():
    calls = {k: 0 for k in ("state", "snapshots", "orders", "risk_decisions", "learning", "activity")}

    def state_loader():
        calls["state"] += 1
        return STATE

    def snapshots_loader(limit=None):
        calls["snapshots"] += 1
        return SNAPSHOTS

    def orders_loader(limit=None):
        calls["orders"] += 1
        return ORDERS

    def risk_loader(limit=None):
        calls["risk_decisions"] += 1
        return RISK

    def learning_loader(limit=None):
        calls["learning"] += 1
        return LEARNING

    def activity_loader(limit=None):
        calls["activity"] += 1
        return ACTIVITY

    loaders = {
        "state": state_loader,
        "snapshots": snapshots_loader,
        "orders": orders_loader,
        "risk_decisions": risk_loader,
        "learning": learning_loader,
        "activity": activity_loader,
    }
    return loaders, calls


def spy_report(**overrides):
    spies = {
        "portfolio_engine": SpyEngine({"portfolio": "ok"}),
        "performance_engine": SpyEngine({"performance": "ok"}),
        "scenarios_engine": SpyEngine({"scenarios": "ok"}),
        "correlation_engine": SpyEngine({"status": "NOT_EVALUATED", "reason": "mock provider"}),
        "learning_engine": SpyEngine({"learning": "ok"}),
    }
    loaders, calls = counting_loaders()
    kwargs = {
        "operations": FakeOps(),
        "reliability": FakeReliability(),
        "fund": FakeFund(),
        "loaders": loaders,
        "now": NOW,
        **spies,
    }
    kwargs.update(overrides)
    report = DashboardV2Engine().report(**kwargs)
    return report, spies, calls


# ----------------------------------------------------------------------
# All sections exist.
# ----------------------------------------------------------------------
report, spies, calls = spy_report()
for section in SECTIONS:
    assert section in report, section

assert report["version"] == "dashboard-v2"
assert report["notifications"] == []
assert report["policy"]["read_only"] is True
assert report["policy"]["writes"] is False
assert report["policy"]["composition_only"] is True
assert report["operations"] == FakeOps().report()
assert report["reliability"] == FakeReliability().report()
assert report["paper_fund"] == FakeFund().status()


# ----------------------------------------------------------------------
# Shared dataset loaded EXACTLY ONCE; no duplicated repository reads.
# ----------------------------------------------------------------------
assert calls == {
    "state": 1,
    "snapshots": 1,
    "orders": 1,
    "risk_decisions": 1,
    "learning": 1,
    "activity": 1,
}, calls


# ----------------------------------------------------------------------
# The single shared objects are injected (by identity) into every engine,
# proving no engine re-reads the tables.
# ----------------------------------------------------------------------
assert len(spies["portfolio_engine"].calls) == 1
assert len(spies["performance_engine"].calls) == 1
assert len(spies["scenarios_engine"].calls) == 1
assert len(spies["correlation_engine"].calls) == 1
assert len(spies["learning_engine"].calls) == 1

pf_call = spies["portfolio_engine"].calls[0]
assert pf_call["snapshots"] is SNAPSHOTS
assert pf_call["risk_decisions"] is RISK
assert pf_call["learning"] is LEARNING
assert pf_call["activity"] is ACTIVITY

perf_call = spies["performance_engine"].calls[0]
assert perf_call["orders"] is ORDERS
assert perf_call["snapshots"] is SNAPSHOTS

corr_call = spies["correlation_engine"].calls[0]
assert corr_call["snapshots"] is SNAPSHOTS
assert "orders" not in corr_call  # correlation only needs state + snapshots

learn_call = spies["learning_engine"].calls[0]
assert learn_call["learning"] is LEARNING
assert learn_call["orders"] is ORDERS

# Risk section reuses the already-loaded risk decisions (same object, no re-read).
assert report["risk"]["decisions"] is RISK
assert report["risk"]["count"] == 1
assert report["risk"]["read_only"] is True
assert "limits" in report["risk"]


# ----------------------------------------------------------------------
# Composition only: child results pass through verbatim.
# ----------------------------------------------------------------------
assert report["portfolio"] == {"portfolio": "ok"}
assert report["performance"] == {"performance": "ok"}
assert report["scenarios"] == {"scenarios": "ok"}
assert report["learning"] == {"learning": "ok"}
# Market and scheduler are projected from the operations report (not re-fetched).
assert report["market"] == {"status": "EVALUATED", "active_provider": "yahoo"}
assert report["scheduler"] == {"status": "EVALUATED", "tick_count": 3}


# ----------------------------------------------------------------------
# NOT_EVALUATED values from child engines are preserved verbatim.
# ----------------------------------------------------------------------
assert report["correlation"] == {"status": "NOT_EVALUATED", "reason": "mock provider"}


# ----------------------------------------------------------------------
# Deterministic output.
# ----------------------------------------------------------------------
def deterministic_report():
    return DashboardV2Engine().report(
        operations=FakeOps(),
        reliability=FakeReliability(),
        fund=FakeFund(),
        portfolio_engine=SpyEngine({"portfolio": "ok"}),
        performance_engine=SpyEngine({"performance": "ok"}),
        scenarios_engine=SpyEngine({"scenarios": "ok"}),
        correlation_engine=SpyEngine({"correlation": "ok"}),
        learning_engine=SpyEngine({"learning": "ok"}),
        paper_fund_data={
            "state": STATE,
            "snapshots": SNAPSHOTS,
            "orders": ORDERS,
            "risk_decisions": RISK,
            "learning": LEARNING,
            "activity": ACTIVITY,
        },
        now=NOW,
    )


assert deterministic_report() == deterministic_report(), "Output must be deterministic."


# ----------------------------------------------------------------------
# Injected paper_fund_data -> loaders are never called at all.
# ----------------------------------------------------------------------
loaders, injected_calls = counting_loaders()
injected = DashboardV2Engine().report(
    operations=FakeOps(),
    reliability=FakeReliability(),
    fund=FakeFund(),
    portfolio_engine=SpyEngine({}),
    performance_engine=SpyEngine({}),
    scenarios_engine=SpyEngine({}),
    correlation_engine=SpyEngine({}),
    learning_engine=SpyEngine({}),
    paper_fund_data={
        "state": STATE,
        "snapshots": SNAPSHOTS,
        "orders": ORDERS,
        "risk_decisions": RISK,
        "learning": LEARNING,
        "activity": ACTIVITY,
    },
    loaders=loaders,
    now=NOW,
)
assert all(count == 0 for count in injected_calls.values())
assert injected["risk"]["decisions"] is RISK


# ----------------------------------------------------------------------
# Graceful degradation: raising collaborators never crash the report.
# ----------------------------------------------------------------------
graceful, _, _ = spy_report(
    operations=RaisingOps(),
    fund=RaisingFund(),
    portfolio_engine=RaisingEngine(),
)
assert graceful["operations"]["status"] == "Unavailable"
assert graceful["paper_fund"]["status"] == "Unavailable"
assert graceful["portfolio"]["status"] == "Unavailable"
# Market/scheduler degrade to NOT_EVALUATED when operations cannot be composed.
assert graceful["market"]["status"] == "NOT_EVALUATED"
assert graceful["scheduler"]["status"] == "NOT_EVALUATED"
# The remaining sections still resolve.
assert graceful["reliability"] == FakeReliability().report()
for section in SECTIONS:
    assert section in graceful, section


# ----------------------------------------------------------------------
# Raising loaders degrade to an empty shared dataset (never raises).
# ----------------------------------------------------------------------
def boom_loaders():
    def state_loader():
        raise RuntimeError("db boom")

    return {"state": state_loader}


boom = DashboardV2Engine().report(
    operations=FakeOps(),
    reliability=FakeReliability(),
    fund=FakeFund(),
    portfolio_engine=SpyEngine({"portfolio": "ok"}),
    performance_engine=SpyEngine({"performance": "ok"}),
    scenarios_engine=SpyEngine({"scenarios": "ok"}),
    correlation_engine=SpyEngine({"correlation": "ok"}),
    learning_engine=SpyEngine({"learning": "ok"}),
    loaders=boom_loaders(),
    now=NOW,
)
assert boom["risk"]["decisions"] == []  # empty shared fallback, not fabricated
assert boom["portfolio"] == {"portfolio": "ok"}


# ----------------------------------------------------------------------
# No DB writes + empty database handling: the real path against a fresh,
# empty temp database produces a complete report and writes nothing.
# ----------------------------------------------------------------------
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
        "paper_fund_learning",
        "risk_decisions",
        "runtime_states",
        "market_data_snapshots",
    ]
    before = {table: count_rows(table) for table in tables}

    live = DashboardV2Engine().report(now=NOW)

    after = {table: count_rows(table) for table in tables}
    assert before == after, "DashboardV2Engine.report must not write to the database."
    for section in SECTIONS:
        assert section in live, section
    assert live["policy"]["writes"] is False
    assert live["notifications"] == []
    # Empty database: paper fund is OFF and sections resolve without crashing.
    assert isinstance(live["risk"]["decisions"], list)
    assert live["risk"]["count"] == 0
finally:
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(database_path)
    for candidate in (database_path, f"{database_path}-wal", f"{database_path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


print("DashboardV2Engine test passed.")
