import os

# Deterministic offline provider so importing the app never touches the network.
os.environ["MARKET_DATA_PROVIDER"] = "mock"

from fastapi.testclient import TestClient

import api.main as main
from api.scheduler_runtime import scheduler_runtime
from engines.live_paper_fund_engine import LivePaperFundEngine
from engines.research_cycle_engine import ResearchCycleEngine


# ----------------------------------------------------------------------
# Route registration: GET /recommendations/history exists exactly once.
# ----------------------------------------------------------------------
routes = [r for r in main.app.routes if getattr(r, "path", "") == "/recommendations/history"]
assert len(routes) == 1, routes
assert "GET" in routes[0].methods
assert routes[0].methods == {"GET"}, "endpoint must be read-only GET, no mutating verbs"


# ----------------------------------------------------------------------
# Isolate repository access: replace the DB read with a spy that records
# every limit the endpoint passes down and returns a deterministic payload.
# The test therefore never depends on production database contents.
# ----------------------------------------------------------------------
SENTINEL_CYCLES = [{"cycle_id": "c-1", "run_id": 7, "evaluations": [], "duration_seconds": 1.0}]
recorded_limits = []


def spy_get_committee_cycle_evaluations(limit=50):
    recorded_limits.append(limit)
    return list(SENTINEL_CYCLES)


# Guard: prove the read path never ticks the scheduler or paper fund. Any call
# to a cycle-running entry point flips these flags.
tick_invocations = []


def _forbidden_tick(*args, **kwargs):
    tick_invocations.append(True)
    raise AssertionError("GET /recommendations/history must not run a cycle tick.")


original_repo = main.get_committee_cycle_evaluations
original_paper_tick = LivePaperFundEngine.run_due_cycle
original_research_tick = ResearchCycleEngine.run_due_cycle

main.get_committee_cycle_evaluations = spy_get_committee_cycle_evaluations
LivePaperFundEngine.run_due_cycle = _forbidden_tick
ResearchCycleEngine.run_due_cycle = _forbidden_tick

try:
    tasks_before = scheduler_runtime.active_task_count()
    client = TestClient(main.app)

    # --- Default limit -------------------------------------------------
    recorded_limits.clear()
    response = client.get("/recommendations/history")
    assert response.status_code == 200, response.text
    assert response.json() == {"cycles": SENTINEL_CYCLES}
    assert recorded_limits == [500], recorded_limits

    # --- Normal custom limit ------------------------------------------
    recorded_limits.clear()
    response = client.get("/recommendations/history", params={"limit": 42})
    assert response.status_code == 200, response.text
    assert recorded_limits == [42], recorded_limits

    # --- Limits above 2000 are capped at 2000 --------------------------
    recorded_limits.clear()
    response = client.get("/recommendations/history", params={"limit": 9999})
    assert response.status_code == 200, response.text
    assert recorded_limits == [2000], recorded_limits

    # Exactly 2000 passes through unchanged; 2001 is the first capped value.
    recorded_limits.clear()
    assert client.get("/recommendations/history", params={"limit": 2000}).status_code == 200
    assert client.get("/recommendations/history", params={"limit": 2001}).status_code == 200
    assert recorded_limits == [2000, 2000], recorded_limits

    # --- Limits below 1 are clamped to 1 (FastAPI accepts these ints) --
    recorded_limits.clear()
    response = client.get("/recommendations/history", params={"limit": 0})
    assert response.status_code == 200, response.text
    assert recorded_limits == [1], recorded_limits

    recorded_limits.clear()
    response = client.get("/recommendations/history", params={"limit": -5})
    assert response.status_code == 200, response.text
    assert recorded_limits == [1], recorded_limits

    # --- Malformed non-integer input -> FastAPI validation error -------
    recorded_limits.clear()
    response = client.get("/recommendations/history", params={"limit": "not-a-number"})
    assert response.status_code == 422, response.text
    body = response.json()
    assert "detail" in body, body
    assert body["detail"][0]["type"] == "int_parsing", body
    # Validation fails before the handler runs, so the repository is untouched.
    assert recorded_limits == [], recorded_limits

    # --- No writes / no scheduler tick / no paper fund -----------------
    # The repository read is fully mocked (no DB touched), no cycle-running
    # entry point fired, and the request created no scheduler loop tasks.
    assert tick_invocations == [], "no cycle tick should have run"
    assert scheduler_runtime.active_task_count() == tasks_before == 0
finally:
    main.get_committee_cycle_evaluations = original_repo
    LivePaperFundEngine.run_due_cycle = original_paper_tick
    ResearchCycleEngine.run_due_cycle = original_research_tick


print("Recommendation history API test passed.")
