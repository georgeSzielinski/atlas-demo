import json
from datetime import datetime, timedelta
from types import SimpleNamespace

from engines.dashboard_v2_engine import DashboardV2Engine
from engines.research_cycle_engine import _RESEARCH_LOCK, ResearchCycleEngine


engine = ResearchCycleEngine()
NOW = datetime(2026, 7, 6, 9, 0, 0)

ENABLED = SimpleNamespace(
    AUTO_RESEARCH_ENABLED=True, AUTO_RESEARCH_INTERVAL_MINUTES=1440
)
DISABLED = SimpleNamespace(
    AUTO_RESEARCH_ENABLED=False, AUTO_RESEARCH_INTERVAL_MINUTES=1440
)


class _Clock:
    """Scripted deterministic clock: returns NOW + i seconds per call."""

    def __init__(self, start=NOW):
        self.start = start
        self.calls = 0

    def __call__(self):
        value = self.start + timedelta(seconds=self.calls)
        self.calls += 1
        return value


class _FakeResearch:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    def generate(self, now=None):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


class _FakeCommittee:
    def evaluate(self, record):
        return {
            "status": "EVALUATED",
            "committee_recommendation": {
                "action": "HOLD",
                "strength": "MODERATE",
                "agreement_pct": 66.67,
                "confidence": 70.0,
            },
        }


class _FakeFund:
    def __init__(self, result=None, error=None):
        self.result = result if result is not None else {
            "status": "SKIPPED",
            "reason": "automatic paper fund operation is disabled",
        }
        self.error = error
        self.calls = []

    def run_due_cycle(self, manager=None, now=None):
        self.calls.append((manager, now))
        if self.error:
            raise self.error
        return self.result


def run(**overrides):
    activity = []
    kwargs = {
        "manager": "manager-sentinel",
        "now": NOW,
        "research_engine": _FakeResearch(),
        "committee_engine": _FakeCommittee(),
        "fund_engine": _FakeFund(),
        "last_run_loader": lambda: None,
        "record_loader": lambda ticker: None,
        "activity_writer": activity.append,
        "attempt_state": {"last_attempt_at": None},
        "clock": _Clock(),
        "settings_module": ENABLED,
    }
    kwargs.update(overrides)
    result = engine.run_due_cycle(**kwargs)
    return result, activity, kwargs


def stage_of(result, name):
    return next(stage for stage in result["stages"] if stage["stage"] == name)


COMPLETED_GENERATION = {
    "status": "COMPLETED",
    "run_id": 7,
    "recommendation_count": 2,
    "tickers_analyzed": ["AAA", "BBB"],
    "skipped": [],
    "provider": "yahoo",
    "ticker_source": "paper_fund_watchlist",
}


# ---------------------------------------------------------------------------
# Disabled: reduces exactly to the prior paper-fund-only tick. No writes.
# ---------------------------------------------------------------------------
result, activity, kwargs = run(settings_module=DISABLED)
assert stage_of(result, "research_generation")["status"] == "SKIPPED"
assert "disabled" in stage_of(result, "research_generation")["reason"]
assert stage_of(result, "committee_evaluation")["status"] == "SKIPPED"
assert "disabled" in stage_of(result, "committee_evaluation")["reason"]
assert stage_of(result, "paper_fund")["status"] == "SKIPPED"
assert result["status"] == "SKIPPED"
# Scheduler summary contract: reason must explain the skip ("disabled").
assert "disabled" in result["reason"]
assert activity == []
assert kwargs["fund_engine"].calls == [("manager-sentinel", NOW)]
assert kwargs["research_engine"].calls == 0


# ---------------------------------------------------------------------------
# Fresh recommendations: generation AND committee both SKIPPED per decision.
# Identical records are never re-evaluated; nothing is written.
# ---------------------------------------------------------------------------
poison = _FakeResearch(error=AssertionError("generate must not be called"))
result, activity, kwargs = run(
    research_engine=poison,
    last_run_loader=lambda: (NOW - timedelta(hours=2)).isoformat(),
)
generation = stage_of(result, "research_generation")
assert generation["status"] == "SKIPPED"
assert "fresh" in generation["reason"]
assert generation["details"]["fresh"] is True
committee = stage_of(result, "committee_evaluation")
assert committee["status"] == "SKIPPED"
assert committee["reason"] == (
    "Recommendations are already fresh; committee evaluation unchanged."
)
assert activity == []
assert poison.calls == 0
assert len(kwargs["fund_engine"].calls) == 1  # fund still ticked


# ---------------------------------------------------------------------------
# Due + generation COMPLETED: committee evaluates the fresh records; both
# stages record activity with timestamps, durations, and cycle_id=None.
# ---------------------------------------------------------------------------
records = {
    "AAA": {"ticker": "AAA", "confidence": 80, "overall_conviction": 80,
            "knowledge_score": 80, "stability_score": 80},
}
result, activity, kwargs = run(
    research_engine=_FakeResearch(result=dict(COMPLETED_GENERATION)),
    record_loader=lambda ticker: records.get(ticker),
    last_run_loader=lambda: (NOW - timedelta(days=2)).isoformat(),
)
generation = stage_of(result, "research_generation")
assert generation["status"] == "COMPLETED"
assert generation["details"]["run_id"] == 7
assert generation["details"]["recommendation_count"] == 2
assert generation["started_at"] is not None
assert generation["duration_seconds"] == 1.0  # scripted clock: 1s per call

committee = stage_of(result, "committee_evaluation")
assert committee["status"] == "COMPLETED"
evaluations = {item["ticker"]: item for item in committee["details"]["evaluations"]}
assert evaluations["AAA"]["action"] == "HOLD"
assert evaluations["AAA"]["strength"] == "MODERATE"
assert evaluations["BBB"]["status"] == "NOT_EVALUATED"
assert "no stored recommendation record" in evaluations["BBB"]["reason"]

assert result["status"] == "COMPLETED"
assert [entry["activity_type"] for entry in activity] == [
    "RECOMMENDATIONS_GENERATED",
    "COMMITTEE_EVALUATED",
]
for entry in activity:
    assert entry["cycle_id"] is None  # never pollutes fund cycle derivations
    assert entry["at"] == NOW.isoformat()
    assert entry["details"]["duration_seconds"] is not None


# ---------------------------------------------------------------------------
# Due + generation REFUSED (e.g. mock provider): honest NOT_EVALUATED chain,
# nothing written, and the retry cooldown prevents per-tick retries.
# ---------------------------------------------------------------------------
attempt_state = {"last_attempt_at": None}
refused = {
    "status": "REFUSED",
    "reason": "Market data provider 'mock' is not a real provider",
    "recommendation_count": 0,
}
result, activity, _ = run(
    research_engine=_FakeResearch(result=refused),
    attempt_state=attempt_state,
)
generation = stage_of(result, "research_generation")
assert generation["status"] == "NOT_EVALUATED"
assert "not a real provider" in generation["reason"]
committee = stage_of(result, "committee_evaluation")
assert committee["status"] == "NOT_EVALUATED"
assert "No fresh recommendation records" in committee["reason"]
assert activity == []
assert attempt_state["last_attempt_at"] == NOW

# Second tick shortly after: cooldown skips the retry (and the committee).
poison = _FakeResearch(error=AssertionError("must not retry within cooldown"))
retry, activity, _ = run(
    research_engine=poison,
    attempt_state=attempt_state,
    now=NOW + timedelta(minutes=5),
)
generation = stage_of(retry, "research_generation")
assert generation["status"] == "SKIPPED"
assert "attempted recently" in generation["reason"]
assert stage_of(retry, "committee_evaluation")["status"] == "SKIPPED"
assert poison.calls == 0
assert activity == []

# Generation completed with zero records -> committee has nothing to do.
empty = {"status": "COMPLETED", "recommendation_count": 0, "run_id": 9}
result, activity, _ = run(research_engine=_FakeResearch(result=dict(empty)))
assert stage_of(result, "research_generation")["status"] == "NOT_EVALUATED"
assert "no recommendation records" in stage_of(result, "research_generation")["reason"]
assert stage_of(result, "committee_evaluation")["status"] == "NOT_EVALUATED"
assert activity == []


# ---------------------------------------------------------------------------
# Failures are isolated: a crashing research stage never blocks the fund.
# ---------------------------------------------------------------------------
result, activity, kwargs = run(
    research_engine=_FakeResearch(error=RuntimeError("provider exploded")),
)
assert stage_of(result, "research_generation")["status"] == "ERROR"
assert "provider exploded" in stage_of(result, "research_generation")["reason"]
assert stage_of(result, "committee_evaluation")["status"] == "NOT_EVALUATED"
assert len(kwargs["fund_engine"].calls) == 1
assert activity == []

# Fund result mapping: completed / failed / raised.
completed_fund = {"cycle_status": "COMPLETED", "cycle_id": "fund-1"}
result, _, _ = run(fund_engine=_FakeFund(result=completed_fund))
assert stage_of(result, "paper_fund")["status"] == "COMPLETED"
assert stage_of(result, "paper_fund")["details"]["cycle_id"] == "fund-1"
assert result["fund"] == completed_fund

failed_fund = {"cycle_status": "FAILED", "error": "no validated prices"}
result, _, _ = run(fund_engine=_FakeFund(result=failed_fund))
assert stage_of(result, "paper_fund")["status"] == "ERROR"
assert "no validated prices" in stage_of(result, "paper_fund")["reason"]

result, _, _ = run(fund_engine=_FakeFund(error=RuntimeError("db locked")))
assert stage_of(result, "paper_fund")["status"] == "ERROR"
assert "db locked" in stage_of(result, "paper_fund")["reason"]

# A failed cycle that already re-armed itself (cycle_status RECOVERING) is a
# recognized outcome: the real failure reason is preserved — never reported
# as an unknown shape — and it is exactly what scheduler persistence records.
recovering_fund = {
    "cycle_status": "RECOVERING",
    "cycle_id": "fund-2",
    "error": "validated real market prices unavailable",
    "fund_status": "RUNNING",
    "next_update": "2026-07-06T09:30:00",
}
result, _, _ = run(fund_engine=_FakeFund(result=recovering_fund))
recovering_stage = stage_of(result, "paper_fund")
assert recovering_stage["status"] == "ERROR"
assert "validated real market prices unavailable" in recovering_stage["reason"]
assert "2026-07-06T09:30:00" in recovering_stage["reason"]
assert "unknown shape" not in recovering_stage["reason"]
assert recovering_stage["details"]["cycle_id"] == "fund-2"
assert result["reason"] == recovering_stage["reason"]


# ---------------------------------------------------------------------------
# Single-flight: a held lock skips the whole cycle without writes.
# ---------------------------------------------------------------------------
assert _RESEARCH_LOCK.acquire(blocking=False)
try:
    result, activity, kwargs = run()
    assert result["status"] == "SKIPPED"
    assert result["reason"] == "another research cycle is already running"
    assert result["stages"] == []
    assert activity == []
    assert kwargs["fund_engine"].calls == []
finally:
    _RESEARCH_LOCK.release()


# ---------------------------------------------------------------------------
# Determinism: identical inputs and scripted clock -> identical output.
# ---------------------------------------------------------------------------
def deterministic_run():
    result, _, _ = run(
        research_engine=_FakeResearch(result=dict(COMPLETED_GENERATION)),
        record_loader=lambda ticker: records.get(ticker),
        attempt_state={"last_attempt_at": None},
        clock=_Clock(),
    )
    return result


assert json.dumps(deterministic_run(), sort_keys=True) == json.dumps(
    deterministic_run(), sort_keys=True
)


# ---------------------------------------------------------------------------
# Read-only status report.
# ---------------------------------------------------------------------------
status = engine.status(
    settings_module=ENABLED,
    last_run_loader=lambda: (NOW - timedelta(days=3)).isoformat(),
    now=NOW,
)
assert status["enabled"] is True
assert status["interval_minutes"] == 1440
assert status["research_due"] is True
assert status["policy"]["paper_only"] is True

fresh_status = engine.status(
    settings_module=ENABLED,
    last_run_loader=lambda: (NOW - timedelta(hours=1)).isoformat(),
    now=NOW,
)
assert fresh_status["research_due"] is False


# ---------------------------------------------------------------------------
# Policy block on every cycle result.
# ---------------------------------------------------------------------------
result, _, _ = run()
policy = result["policy"]
assert policy["composition_only"] is True
assert policy["paper_only"] is True
assert policy["llm_decisions"] is False
assert policy["broker_integration"] is False
assert policy["real_money"] is False
assert policy["reuses_existing_engines_only"] is True
assert policy["modifies_fund_trading_behavior"] is False


# ---------------------------------------------------------------------------
# Dashboard v2 research_cycle section (composed from recorded activity).
# ---------------------------------------------------------------------------
dashboard = DashboardV2Engine()

empty_section = dashboard._research_cycle({"activity": []})
assert empty_section["status"] == "NOT_EVALUATED"
assert "No autonomous research cycle" in empty_section["reason"]
assert [stage["status"] for stage in empty_section["stages"]] == [
    "NOT_EVALUATED", "NOT_EVALUATED",
]

fixture_activity = [
    {
        "at": "2026-07-06T09:00:00",
        "cycle_id": None,
        "activity_type": "COMMITTEE_EVALUATED",
        "message": "Investment committee evaluated 1 record(s).",
        "details": {"evaluations": [{"ticker": "AAA"}], "duration_seconds": 0.4},
    },
    {
        "at": "2026-07-06T09:00:00",
        "cycle_id": None,
        "activity_type": "RECOMMENDATIONS_GENERATED",
        "message": "Autonomous research generated 2 record(s) (run 7).",
        "details": {"run_id": 7, "recommendation_count": 2, "duration_seconds": 3.2},
    },
]
section = dashboard._research_cycle({"activity": fixture_activity})
assert section["status"] == "EVALUATED"
stages = {stage["stage"]: stage for stage in section["stages"]}
assert stages["research_generation"]["status"] == "COMPLETED"
assert stages["research_generation"]["duration_seconds"] == 3.2
assert stages["research_generation"]["at"] == "2026-07-06T09:00:00"
assert stages["committee_evaluation"]["status"] == "COMPLETED"
assert stages["committee_evaluation"]["details"]["evaluations"] == [{"ticker": "AAA"}]

# The full composed report carries the new section.
full_report = dashboard.report(
    operations={"scheduler": {"status": "EVALUATED"}, "market_data": {"status": "EVALUATED"}},
    reliability={},
    fund={},
    portfolio_engine=SimpleNamespace(generate=lambda **kwargs: {}),
    performance_engine=SimpleNamespace(generate=lambda **kwargs: {}),
    scenarios_engine=SimpleNamespace(generate=lambda **kwargs: {}),
    correlation_engine=SimpleNamespace(generate=lambda **kwargs: {}),
    learning_engine=SimpleNamespace(generate=lambda **kwargs: {}),
    paper_fund_data={"activity": fixture_activity},
    risk_limits={},
    risk_decisions=[],
)
assert full_report["research_cycle"]["status"] == "EVALUATED"


# ---------------------------------------------------------------------------
# API endpoints: default settings -> the tick reduces to a safe skip; the
# status endpoint is read-only.
# ---------------------------------------------------------------------------
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

tick_response = client.post("/research-cycle/tick")
assert tick_response.status_code == 200
tick_body = tick_response.json()
assert tick_body["tick"]["status"] in {"SKIPPED", "COMPLETED"}
tick_stages = {s["stage"]: s for s in tick_body["tick"]["stages"]}
assert tick_stages["research_generation"]["status"] == "SKIPPED"  # disabled by default
assert tick_stages["committee_evaluation"]["status"] == "SKIPPED"

status_response = client.get("/research-cycle/status")
assert status_response.status_code == 200
status_body = status_response.json()
assert status_body["enabled"] is False  # off by default
assert status_body["policy"]["broker_integration"] is False

print("ResearchCycleEngine test passed.")
