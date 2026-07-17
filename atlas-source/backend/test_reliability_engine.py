import os
import tempfile
from datetime import datetime

import database.connection as connection
from database.migrator import run_migrations
from backend.status import count_rows
from engines.reliability_engine import ReliabilityEngine


NOW = datetime(2026, 7, 4, 10, 0, 0)

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
# Injectable OperationsEngine-shaped fixtures.
# ----------------------------------------------------------------------
def healthy_ops(**overrides):
    report = {
        "overall_health": {"status": "Healthy"},
        "scheduler": {
            "status": "EVALUATED",
            "enabled": True,
            "error_count": 0,
            "last_error_at": None,
            "started_at": "2026-07-04T09:00:00",
        },
        "market_data": {
            "status": "EVALUATED",
            "active_provider": "yahoo",
            "requested_provider": "yahoo",
            "healthy": True,
            "fallback_used": False,
            "validated": True,
            "last_error": None,
            "data_freshness": {"is_stale": False},
            "offline_capable": False,
        },
        "paper_fund": {
            "status": "EVALUATED",
            "fund_status": "RUNNING",
            "last_error": None,
            "last_update": "2026-07-04T09:50:00",
        },
        "learning": {"status": "EVALUATED", "learning_active": True},
        "database": {"status": "EVALUATED", "exists": True, "total_rows": 10},
        "uptime": {
            "status": "EVALUATED",
            "source": "scheduler",
            "uptime_seconds": 3600,
            "uptime_human": "1h 0s",
        },
        "warnings": [],
        "recent_errors": [],
        "operational_recommendations": [],
        "operational_mode": {"mode": "LIVE_PAPER"},
        "policy": {"read_only": True},
    }
    for key, value in overrides.items():
        report[key] = value
    return report


def up_state(day):
    return {
        "current_state": "RUNNING",
        "health": {"status": "Healthy"},
        "market_date": f"2026-07-{day:02d}",
    }


def down_state(day):
    return {
        "current_state": "ERROR",
        "health": {"status": "Degraded"},
        "market_date": f"2026-07-{day:02d}",
    }


HEALTHY_RUNTIME = [up_state(day) for day in range(6, 0, -1)]  # newest-first
HEALTHY_MARKET = [{"validated": True, "fallback_used": False} for _ in range(5)]
HEALTHY_ACTIVITY = [{"activity_type": "CYCLE_COMPLETED", "at": "2026-07-04T09:50:00"}]


def healthy_report(**overrides):
    kwargs = {
        "operations": healthy_ops(),
        "runtime_history": HEALTHY_RUNTIME,
        "market_history": HEALTHY_MARKET,
        "fund_activity": HEALTHY_ACTIVITY,
        "now": NOW,
    }
    kwargs.update(overrides)
    return ReliabilityEngine().report(**kwargs)


engine = ReliabilityEngine()


# ----------------------------------------------------------------------
# Healthy system.
# ----------------------------------------------------------------------
report = healthy_report()

for key in REQUIRED_KEYS:
    assert key in report, key

assert report["version"] == "reliability-framework-v1"
assert report["overall_reliability"] == {
    "score": 100,
    "grade": "A+",
    "status": "Reliable",
    "evaluated_subsystems": 7,
    "total_subsystems": 7,
}
assert all(report["subsystem_scores"][name] == 100 for name in ReliabilityEngine.SUBSYSTEMS)
assert report["confidence"]["level"] == "HIGH"
assert report["warning_count"] == 0
assert report["error_count"] == 0
assert report["critical_count"] == 0
assert report["recent_incidents"] == []
assert report["consecutive_failures"] == {"status": "EVALUATED", "count": 0}
assert report["availability"]["status"] == "EVALUATED"
assert report["availability"]["availability_percent"] == 100.0
assert report["reliability_trend"]["status"] == "EVALUATED"
assert report["reliability_trend"]["direction"] == "STABLE"
assert report["reliability_recommendations"] == ["No reliability action required."]
assert report["operational_policy"]["read_only"] is True
assert report["operational_policy"]["writes"] is False
assert report["operational_policy"]["broker_integration"] is False
assert report["operational_policy"]["real_money"] is False
# Contributors sum to the overall score.
impacts = [c["impact"] for c in report["contributors"] if c["impact"] is not None]
assert round(100 + sum(impacts)) == report["overall_reliability"]["score"]


# ----------------------------------------------------------------------
# Deterministic output.
# ----------------------------------------------------------------------
assert healthy_report() == healthy_report(), "ReliabilityEngine must be deterministic."


# ----------------------------------------------------------------------
# Weighted scoring + contributor calculation.
# market_data: not validated + stale -> two warnings -> score 80.
# ----------------------------------------------------------------------
weighted = healthy_report(
    operations=healthy_ops(
        market_data={
            "status": "EVALUATED",
            "active_provider": "yahoo",
            "healthy": True,
            "fallback_used": False,
            "validated": False,
            "last_error": None,
            "data_freshness": {"is_stale": True},
        }
    )
)
assert weighted["subsystem_scores"]["market_data"] == 80
assert weighted["subsystem_scores"]["provider"] == 100  # no fallback
market_contributor = next(
    c for c in weighted["contributors"] if c["subsystem"] == "market_data"
)
assert market_contributor["score"] == 80
assert market_contributor["weight"] == 0.2
assert market_contributor["base_weight"] == 0.2
assert market_contributor["impact"] == -4.0
assert market_contributor["excluded"] is False
# 0.80*100 + 0.20*80 = 96
assert weighted["overall_reliability"]["score"] == 96
assert weighted["overall_reliability"]["grade"] == "A"
assert weighted["overall_reliability"]["status"] == "Reliable"


# ----------------------------------------------------------------------
# Grade calculation (deterministic scale; 97 -> A, 100 -> A+).
# ----------------------------------------------------------------------
assert engine._grade(100) == "A+"
assert engine._grade(98) == "A+"
assert engine._grade(97) == "A"
assert engine._grade(93) == "A"
assert engine._grade(92) == "A-"
assert engine._grade(90) == "A-"
assert engine._grade(89) == "B+"
assert engine._grade(60) == "D-"
assert engine._grade(59) == "F"
assert engine._grade(None) == "NOT_EVALUATED"
assert engine._status(90) == "Reliable"
assert engine._status(89) == "Watch"
assert engine._status(74) == "Degraded"
assert engine._status(49) == "Critical"
assert engine._status(None) == "NOT_EVALUATED"


# ----------------------------------------------------------------------
# Confidence calculation. Low telemetry must never produce HIGH.
# ----------------------------------------------------------------------
# Full coverage + history -> HIGH.
assert healthy_report()["confidence"]["level"] == "HIGH"
# Full coverage but no runtime history -> MEDIUM (not HIGH).
assert healthy_report(runtime_history=[])["confidence"]["level"] == "MEDIUM"
# Minority of subsystems reporting -> LOW.
sparse_ops = {
    "overall_health": {"status": "Degraded"},
    "scheduler": {"status": "EVALUATED", "error_count": 0},
    "database": {"status": "EVALUATED", "exists": True},
    "market_data": {"status": "Unavailable", "reason": "down"},
    "paper_fund": {"status": "Unavailable", "reason": "down"},
    "learning": {"status": "Unavailable", "reason": "down"},
    "uptime": {"status": "NOT_STARTED"},
}
sparse = healthy_report(operations=sparse_ops, runtime_history=[])
assert sparse["confidence"]["level"] == "LOW"
assert sparse["confidence"]["coverage"] == "3/7"  # scheduler, database, api


# ----------------------------------------------------------------------
# NOT_EVALUATED exclusion: missing subsystems are excluded, never scored 0.
# ----------------------------------------------------------------------
excluded_ops = healthy_ops(
    market_data={"status": "Unavailable", "reason": "market telemetry down"}
)
excluded = healthy_report(operations=excluded_ops)
assert excluded["subsystem_scores"]["market_data"] is None
assert excluded["subsystem_scores"]["provider"] is None
market_c = next(
    c for c in excluded["contributors"] if c["subsystem"] == "market_data"
)
provider_c = next(
    c for c in excluded["contributors"] if c["subsystem"] == "provider"
)
assert market_c["excluded"] is True and market_c["weight"] == 0.0
assert provider_c["excluded"] is True and provider_c["impact"] is None
# Renormalized over the remaining subsystems: api drops to 90 (one section
# unavailable), everyone else 100 -> 98, NOT dragged toward zero.
assert excluded["subsystem_scores"]["api"] == 90
assert excluded["overall_reliability"]["score"] == 98
assert excluded["overall_reliability"]["evaluated_subsystems"] == 5
assert excluded["market_data_reliability"]["status"] == "NOT_EVALUATED"
assert "telemetry" in excluded["market_data_reliability"]["reason"].lower()


# ----------------------------------------------------------------------
# All unavailable: overall NOT_EVALUATED, never raises, never fabricates.
# ----------------------------------------------------------------------
class RaisingOps:
    def report(self):
        raise RuntimeError("operations boom")


all_unavailable = ReliabilityEngine().report(
    operations=RaisingOps(),
    runtime_history=[],
    market_history=[],
    fund_activity=[],
    now=NOW,
)
assert all_unavailable["overall_reliability"]["score"] is None
assert all_unavailable["overall_reliability"]["grade"] == "NOT_EVALUATED"
assert all_unavailable["overall_reliability"]["status"] == "NOT_EVALUATED"
assert all(
    all_unavailable["subsystem_scores"][name] is None
    for name in ReliabilityEngine.SUBSYSTEMS
)
assert all_unavailable["confidence"]["level"] == "LOW"
assert all_unavailable["consecutive_failures"]["status"] == "NOT_EVALUATED"
assert all_unavailable["availability"]["status"] == "NOT_EVALUATED"
assert all_unavailable["reliability_trend"]["status"] == "NOT_EVALUATED"


# ----------------------------------------------------------------------
# Incident merging: multiple sources combine, de-duplicate, order stably.
# ----------------------------------------------------------------------
merge_ops = healthy_ops(
    scheduler={
        "status": "EVALUATED",
        "error_count": 2,
        "last_error_at": "2026-07-04T09:30:00",
        "started_at": "2026-07-04T09:00:00",
    },
    market_data={
        "status": "EVALUATED",
        "active_provider": "yahoo",
        "healthy": True,
        "fallback_used": False,
        "validated": True,
        "last_error": "quote feed timeout",
        "data_freshness": {"is_stale": False},
    },
    paper_fund={
        "status": "EVALUATED",
        "fund_status": "ERROR",
        "last_error": "boom",
        "last_update": "2026-07-04T09:40:00",
    },
)
merge_activity = [
    {"activity_type": "CYCLE_FAILED", "message": "boom", "at": "2026-07-04T09:40:00"},
    {"activity_type": "CYCLE_FAILED", "message": "older failure", "at": "2026-07-03T09:40:00"},
    {"activity_type": "CYCLE_COMPLETED", "message": "ok", "at": "2026-07-02T09:40:00"},
]
merged = healthy_report(operations=merge_ops, fund_activity=merge_activity)
incidents = merged["recent_incidents"]
# "boom" appears from both the ERROR-state section (CRITICAL) and CYCLE_FAILED
# activity (ERROR): deduped to a single CRITICAL entry.
boom = [i for i in incidents if i["message"] == "boom"]
assert len(boom) == 1
assert boom[0]["severity"] == "CRITICAL"
assert boom[0]["subsystem"] == "paper_fund"
# Ordered by subsystem (scheduler, market_data, ..., paper_fund).
subsystems_in_order = [i["subsystem"] for i in incidents]
assert subsystems_in_order == sorted(
    subsystems_in_order,
    key=lambda name: ReliabilityEngine.SUBSYSTEMS.index(name),
)
assert merged["critical_count"] == 1
assert merged["error_count"] >= 2  # scheduler + market_data + older failure


# ----------------------------------------------------------------------
# Consecutive failures + degradation escalation.
# ----------------------------------------------------------------------
streak_activity = [
    {"activity_type": "CYCLE_FAILED", "message": "fail 3", "at": "2026-07-04T09:50:00"},
    {"activity_type": "CYCLE_FAILED", "message": "fail 2", "at": "2026-07-04T09:20:00"},
    {"activity_type": "CYCLE_FAILED", "message": "fail 1", "at": "2026-07-04T08:50:00"},
    {"activity_type": "CYCLE_COMPLETED", "message": "ok", "at": "2026-07-04T08:20:00"},
]
streak = healthy_report(
    operations=healthy_ops(
        paper_fund={
            "status": "EVALUATED",
            "fund_status": "ERROR",
            "last_error": "prices unavailable",
            "last_update": "2026-07-04T09:50:00",
        }
    ),
    fund_activity=streak_activity,
)
assert streak["consecutive_failures"] == {"status": "EVALUATED", "count": 3}
assert streak["critical_count"] >= 1
assert any(
    "Halt automatic paper-fund cycles" in rec
    for rec in streak["reliability_recommendations"]
)
assert streak["overall_reliability"]["status"] in {"Degraded", "Critical", "Watch"}

# No terminal cycles -> NOT_EVALUATED.
no_cycles = healthy_report(
    fund_activity=[{"activity_type": "CYCLE_STARTED", "message": "x", "at": "z"}]
)
assert no_cycles["consecutive_failures"]["status"] == "NOT_EVALUATED"

# Latest cycle succeeded -> zero streak.
zero_streak = healthy_report(
    fund_activity=[
        {"activity_type": "CYCLE_COMPLETED", "message": "ok", "at": "b"},
        {"activity_type": "CYCLE_FAILED", "message": "old", "at": "a"},
    ]
)
assert zero_streak["consecutive_failures"]["count"] == 0


# ----------------------------------------------------------------------
# Availability.
# ----------------------------------------------------------------------
availability = healthy_report(
    runtime_history=[up_state(4), up_state(3), up_state(2), down_state(1)]
)["availability"]
assert availability["status"] == "EVALUATED"
assert availability["availability_percent"] == 75.0
assert availability["states_sampled"] == 4
assert availability["up_states"] == 3
assert healthy_report(runtime_history=[])["availability"]["status"] == "NOT_EVALUATED"


# ----------------------------------------------------------------------
# Trend.
# ----------------------------------------------------------------------
# Fewer than the minimum samples -> NOT_EVALUATED.
assert (
    healthy_report(runtime_history=[up_state(2), up_state(1)])["reliability_trend"][
        "status"
    ]
    == "NOT_EVALUATED"
)
# Recent window up, older window down -> IMPROVING (newest-first ordering).
improving = healthy_report(
    runtime_history=[up_state(4), up_state(3), down_state(2), down_state(1)]
)["reliability_trend"]
assert improving["direction"] == "IMPROVING"
degrading = healthy_report(
    runtime_history=[down_state(4), down_state(3), up_state(2), up_state(1)]
)["reliability_trend"]
assert degrading["direction"] == "DEGRADING"
stable = healthy_report(
    runtime_history=[up_state(4), up_state(3), up_state(2), up_state(1)]
)["reliability_trend"]
assert stable["direction"] == "STABLE"


# ----------------------------------------------------------------------
# Recommendations for a degraded system.
# ----------------------------------------------------------------------
degraded_ops = healthy_ops(
    market_data={
        "status": "EVALUATED",
        "active_provider": "mock",
        "healthy": True,
        "fallback_used": True,
        "validated": False,
        "last_error": None,
        "data_freshness": {"is_stale": True},
    },
    scheduler={
        "status": "EVALUATED",
        "error_count": 1,
        "last_error_at": "2026-07-04T09:30:00",
        "started_at": "2026-07-04T09:00:00",
    },
)
degraded = healthy_report(operations=degraded_ops)
recs = degraded["reliability_recommendations"]
assert any("validated real market data provider" in rec for rec in recs)
assert any("Refresh market data" in rec for rec in recs)
assert any("scheduler tick errors" in rec for rec in recs)
assert "No reliability action required." not in recs


# ----------------------------------------------------------------------
# Graceful degradation: raising history collaborators never crash the report.
# ----------------------------------------------------------------------
class RaisingList:
    def __iter__(self):
        raise RuntimeError("history boom")


graceful = ReliabilityEngine().report(
    operations=healthy_ops(),
    runtime_history=RaisingList(),
    market_history=RaisingList(),
    fund_activity=RaisingList(),
    now=NOW,
)
assert graceful["availability"]["status"] == "NOT_EVALUATED"
assert graceful["reliability_trend"]["status"] == "NOT_EVALUATED"
assert graceful["consecutive_failures"]["status"] == "NOT_EVALUATED"
# The live subsystems still evaluate from the operations report.
assert graceful["overall_reliability"]["score"] == 100


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

    tables = [
        "atlas_runs",
        "recommendations",
        "runtime_states",
        "market_data_snapshots",
        "paper_fund_activity",
        "paper_fund_snapshots",
    ]
    before = {table: count_rows(table) for table in tables}

    live = ReliabilityEngine().report(now=NOW)

    after = {table: count_rows(table) for table in tables}
    assert before == after, "ReliabilityEngine.report must not write to the database."
    for key in REQUIRED_KEYS:
        assert key in live, key
    assert live["operational_policy"]["writes"] is False
finally:
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(database_path)
    for candidate in (database_path, f"{database_path}-wal", f"{database_path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


print("ReliabilityEngine test passed.")
