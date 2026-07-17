"""Focused Sprint 1B.2 outcome evaluation tests on temporary databases."""

import os
import tempfile
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace

import database.connection as connection
from database.connection import get_connection
from database.migrator import run_migrations
from database.repository import get_outcomes, get_outcomes_for_recommendation
from engines.outcome_evaluation_engine import OutcomeEvaluationEngine
from engines.validation_engine import ValidationEngine


NOW = datetime(2026, 7, 14, 12, 0, 0)


@contextmanager
def temp_database():
    original = connection.DATABASE_PATH
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as handle:
        path = handle.name
    connection.DATABASE_PATH = path
    connection._wal_initialized_paths.discard(path)
    try:
        run_migrations()
        yield path
    finally:
        connection.DATABASE_PATH = original
        connection._wal_initialized_paths.discard(path)
        for candidate in (path, f"{path}-wal", f"{path}-shm"):
            if os.path.exists(candidate):
                os.remove(candidate)


def seed(rec_id, ticker, action, entry_price=100.0, entry_at="2025-01-01T12:00:00"):
    db = get_connection()
    try:
        db.execute(
            "INSERT INTO recommendations "
            "(id, run_id, ticker, action, confidence, validation_status, entry_at, "
            "entry_price, entry_price_source, entry_validated, entry_status, outcome_state) "
            "VALUES (?, 1, ?, ?, 77, 'Pending', ?, ?, 'yahoo', 1, 'OBSERVED', 'PENDING')",
            (rec_id, ticker, action, entry_at, entry_price),
        )
        db.commit()
    finally:
        db.close()


class PriceManager:
    provider_name = "yahoo"

    def __init__(self, prices, *, fallback=False, validated=True, provider="yahoo", cache_age=0):
        self.prices = prices
        self.fallback = fallback
        self.validated = validated
        self.provider = provider
        self.cache_age = cache_age
        self.calls = 0
        self.requested = []

    def latest_prices(self, tickers, use_cache=True):
        self.calls += 1
        self.requested.append(list(tickers))
        return {
            "requested_provider": self.provider_name,
            "prices": {ticker: self.prices.get(ticker) for ticker in tickers},
            "results": {
                ticker: {
                    "ticker": ticker,
                    "price": self.prices.get(ticker),
                    "provider": self.provider,
                    "fallback_used": self.fallback,
                    "validated": self.validated,
                    "cache_age": self.cache_age,
                }
                for ticker in tickers
            },
            "fallback_used": self.fallback,
            "validated": self.validated,
            "as_of": NOW.isoformat(),
        }


ENABLED = SimpleNamespace(AUTO_OUTCOME_ENABLED=True)
DISABLED = SimpleNamespace(AUTO_OUTCOME_ENABLED=False)


# Disabled and empty states do not fetch prices or write evidence.
engine = OutcomeEvaluationEngine()
disabled = engine.run_due_cycle(settings_module=DISABLED, now=NOW)
assert disabled["status"] == "SKIPPED" and "disabled" in disabled["reason"]
poison = PriceManager({})
empty = engine.evaluate(
    manager=poison,
    now=NOW,
    candidate_loader=lambda *_: [],
    activity_writer=lambda entry: None,
)
assert empty["status"] == "SKIPPED" and poison.calls == 0


# ValidationEngine semantics: BUY needs UP (>1%), AVOID needs DOWN (<-1%),
# HOLD needs FLAT (within +/-1%). Multiple actions continue independently.
with temp_database():
    seed(1, "BUYOK", "BUY")
    seed(2, "BUYBAD", "BUY")
    seed(3, "HOLDOK", "HOLD")
    seed(4, "AVOIDOK", "AVOID")
    manager = PriceManager({"BUYOK": 110, "BUYBAD": 90, "HOLDOK": 100.5, "AVOIDOK": 90})
    summary = engine.evaluate(manager=manager, now=NOW)
    assert summary["evaluated"] == 20  # five ValidationEngine horizons per recommendation
    assert summary["succeeded"] == 15 and summary["failed"] == 5
    assert manager.calls == 1
    rows = get_outcomes(limit=100)
    by_ticker = {}
    for row in rows:
        by_ticker.setdefault(row["ticker"], set()).add(row["status"])
    assert by_ticker == {
        "BUYOK": {"Succeeded"}, "BUYBAD": {"Failed"},
        "HOLDOK": {"Succeeded"}, "AVOIDOK": {"Succeeded"},
    }


# One ticker with multiple due horizons is fetched once; a completed retry is
# excluded and immutable.
with temp_database():
    seed(10, "MULTI", "BUY")
    manager = PriceManager({"MULTI": 110})
    first = engine.evaluate(manager=manager, now=NOW)
    assert first["evaluated"] == len(ValidationEngine.VALIDATION_WINDOWS)
    assert manager.calls == 1 and manager.requested == [["MULTI"]]
    before = get_outcomes_for_recommendation(10)
    second = engine.evaluate(manager=manager, now=NOW)
    assert second["status"] == "SKIPPED" and manager.calls == 1
    assert get_outcomes_for_recommendation(10) == before


# Deferred evidence updates in place on a trustworthy retry; fallback, mock,
# invalid, stale, and non-finite prices never complete an outcome.
for unsafe in (
    PriceManager({"SAFE": 110}, fallback=True),
    PriceManager({"SAFE": 110}, provider="mock"),
    PriceManager({"SAFE": 110}, validated=False),
    PriceManager({"SAFE": 110}, cache_age=301),
    PriceManager({"SAFE": float("nan")}),
):
    with temp_database():
        seed(20, "SAFE", "BUY", entry_at="2026-07-01T12:00:00")
        deferred = engine.evaluate(manager=unsafe, now=NOW)
        assert deferred["deferred"] >= 1 and deferred["evaluated"] == 0
        assert all(row["status"] == "Deferred" for row in get_outcomes_for_recommendation(20))

with temp_database():
    seed(30, "RETRY", "BUY", entry_at="2026-07-01T12:00:00")
    deferred = engine.evaluate(manager=PriceManager({"RETRY": None}), now=NOW)
    rows_before = get_outcomes_for_recommendation(30)
    assert deferred["deferred"] == 1 and len(rows_before) == 1
    completed = engine.evaluate(manager=PriceManager({"RETRY": 110}), now=NOW)
    rows_after = get_outcomes_for_recommendation(30)
    assert completed["succeeded"] == 1
    assert len(rows_after) == 1 and rows_after[0]["id"] == rows_before[0]["id"]
    assert rows_after[0]["status"] == "Succeeded"


# A per-candidate validation failure is isolated; remaining candidates finish.
class OneFailureValidation(ValidationEngine):
    VALIDATION_WINDOWS = [7]

    def evaluate_completed_recommendation(self, recommendation, *args, **kwargs):
        if recommendation["ticker"] == "BAD":
            raise RuntimeError("candidate exploded")
        return super().evaluate_completed_recommendation(recommendation, *args, **kwargs)


with temp_database():
    seed(40, "BAD", "BUY", entry_at="2026-07-01T12:00:00")
    seed(41, "GOOD", "BUY", entry_at="2026-07-01T12:00:00")
    partial = engine.evaluate(
        manager=PriceManager({"BAD": 110, "GOOD": 110}),
        validation_engine=OneFailureValidation(),
        now=NOW,
    )
    assert partial["status"] == "PARTIAL" and len(partial["errors"]) == 1
    assert partial["succeeded"] == 1


# Outcome writes preserve recommendations and paper orders exactly.
with temp_database():
    seed(50, "UNCH", "BUY", entry_at="2026-07-01T12:00:00")
    db = get_connection()
    try:
        db.execute(
            "INSERT INTO paper_fund_orders (order_id, ticker, side, quantity, status) "
            "VALUES ('existing', 'UNCH', 'BUY', 3, 'FILLED_SIMULATED')"
        )
        db.commit()
        rec_before = db.execute("SELECT * FROM recommendations WHERE id = 50").fetchone()
        order_before = db.execute("SELECT * FROM paper_fund_orders WHERE order_id = 'existing'").fetchone()
    finally:
        db.close()
    engine.evaluate(manager=PriceManager({"UNCH": 110}), now=NOW)
    db = get_connection()
    try:
        assert db.execute("SELECT * FROM recommendations WHERE id = 50").fetchone() == rec_before
        assert db.execute("SELECT * FROM paper_fund_orders WHERE order_id = 'existing'").fetchone() == order_before
    finally:
        db.close()


# API reads, manual idempotency, read-only status, and scheduler composition.
from fastapi.testclient import TestClient
import api.main as api_main

client = TestClient(api_main.app)
outcomes_response_schema = (
    api_main.app.openapi()["paths"]["/recommendations/{recommendation_id}/outcomes"]
    ["get"]["responses"]["200"]["content"]["application/json"]["schema"]
)
assert outcomes_response_schema == {
    "$ref": "#/components/schemas/RecommendationOutcomesResponse"
}
with temp_database():
    seed(60, "API", "BUY", entry_at="2026-07-01T12:00:00")
    original_manager = api_main.MarketDataManager
    original_datetime = api_main.datetime
    original_research_tick = api_main.research_cycle_tick
    original_settings = __import__("core.settings", fromlist=["settings"])
    original_enabled = original_settings.AUTO_OUTCOME_ENABLED

    class FixedDateTime:
        @classmethod
        def now(cls):
            return NOW

    api_main.MarketDataManager = lambda: PriceManager({"API": 110})
    api_main.datetime = FixedDateTime
    try:
        first = client.post("/outcomes/evaluate")
        second = client.post("/outcomes/evaluate")
        assert first.status_code == second.status_code == 200
        assert first.json()["outcome_evaluation"]["succeeded"] == 1
        assert second.json()["outcome_evaluation"]["status"] == "SKIPPED"

        feed = client.get("/outcomes?limit=999999&ticker=api&horizon=7&evaluation_source=paper")
        assert feed.status_code == 200
        assert feed.json()["meta"]["limit"] == 2000
        assert feed.json()["outcomes"][0]["ticker"] == "API"
        assert client.get("/outcomes?limit=0").status_code == 422
        assert client.get("/outcomes?horizon=0").status_code == 422
        exact_response = client.get("/recommendations/60/outcomes")
        assert exact_response.status_code == 200
        exact = exact_response.json()
        assert set(exact) == {"recommendation_outcomes", "meta"}
        assert exact["meta"] == {
            "recommendation_id": 60,
            "count": len(exact["recommendation_outcomes"]),
            "read_only": True,
        }
        assert exact["recommendation_outcomes"] == get_outcomes_for_recommendation(60)
        missing = client.get("/recommendations/999/outcomes").json()
        assert missing == {
            "recommendation_outcomes": [],
            "meta": {"recommendation_id": 999, "count": 0, "read_only": True},
        }

        db = get_connection()
        try:
            before_counts = (
                db.execute("SELECT COUNT(*) FROM recommendation_validations").fetchone()[0],
                db.execute("SELECT COUNT(*) FROM paper_fund_activity").fetchone()[0],
            )
        finally:
            db.close()
        status = client.get("/outcomes/status")
        assert status.status_code == 200
        assert status.json()["outcome_status"]["policy"]["does_not_place_orders"] is True
        operations = client.get("/operations")
        assert operations.status_code == 200
        outcome_ops = operations.json()["outcome_evaluation"]
        assert outcome_ops["paper_only"] is True
        assert outcome_ops["does_not_place_orders"] is True
        assert outcome_ops["pending"] == outcome_ops["pending_count"]
        db = get_connection()
        try:
            after_counts = (
                db.execute("SELECT COUNT(*) FROM recommendation_validations").fetchone()[0],
                db.execute("SELECT COUNT(*) FROM paper_fund_activity").fetchone()[0],
            )
        finally:
            db.close()
        assert after_counts == before_counts

        # The existing scheduler wrapper adds one isolated outcome stage. Two
        # ticks cannot duplicate the already completed keyed outcome.
        seed(61, "SCHED", "BUY")
        api_main.MarketDataManager = lambda: PriceManager({"API": 110, "SCHED": 110})
        api_main.research_cycle_tick = lambda: {
            "tick": {"status": "SKIPPED", "reason": "fixture", "stages": []},
            "status": "SKIPPED",
        }
        original_settings.AUTO_OUTCOME_ENABLED = True
        scheduled_one = api_main.scheduled_cycle_tick()
        scheduled_two = api_main.scheduled_cycle_tick()
        assert scheduled_one["tick"]["stages"][0]["stage"] == "outcome_evaluation"
        assert scheduled_one["outcome_evaluation"]["succeeded"] == len(ValidationEngine.VALIDATION_WINDOWS)
        assert scheduled_two["outcome_evaluation"]["status"] == "SKIPPED"
        assert len(get_outcomes_for_recommendation(61)) == len(ValidationEngine.VALIDATION_WINDOWS)
    finally:
        original_settings.AUTO_OUTCOME_ENABLED = original_enabled
        api_main.MarketDataManager = original_manager
        api_main.datetime = original_datetime
        api_main.research_cycle_tick = original_research_tick


print("Outcome evaluation Sprint 1B.2 tests passed.")
