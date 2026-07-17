"""Sprint 2.0 Recommendation Intelligence tests using a temporary database."""

import os
import tempfile
from contextlib import contextmanager
from datetime import datetime

import database.connection as connection
from database.connection import get_connection
from database.migrator import run_migrations
from database.repository import get_recommendation_intelligence_records
from engines.recommendation_intelligence_engine import RecommendationIntelligenceEngine


NOW = datetime(2026, 2, 1, 12, 0, 0)


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


def seed_recommendation(rec_id, ticker, action, confidence, created_at):
    db = get_connection()
    try:
        db.execute(
            "INSERT INTO recommendations "
            "(id, run_id, ticker, action, confidence, created_at, entry_at, "
            "entry_price, outcome_state) VALUES (?, 1, ?, ?, ?, ?, ?, 100, 'PENDING')",
            (rec_id, ticker, action, confidence, created_at, created_at),
        )
        db.commit()
    finally:
        db.close()


def seed_outcome(outcome_id, rec_id, ticker, action, status, success, value, horizon, evaluated_at):
    db = get_connection()
    try:
        db.execute(
            "INSERT INTO recommendation_validations "
            "(id, recommendation_id, ticker, recommendation, status, success, "
            "percentage_return, horizon_days, evaluation_source, evaluation_timestamp, "
            "starting_price, ending_price) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'paper', ?, 100, ?)",
            (
                outcome_id, rec_id, ticker, action, status, success, value,
                horizon, evaluated_at, None if value is None else 100 * (1 + value / 100),
            ),
        )
        db.commit()
    finally:
        db.close()


def counts():
    db = get_connection()
    try:
        return {
            "recommendations": db.execute("SELECT COUNT(*) FROM recommendations").fetchone()[0],
            "outcomes": db.execute("SELECT COUNT(*) FROM recommendation_validations").fetchone()[0],
            "orders": db.execute("SELECT COUNT(*) FROM paper_fund_orders").fetchone()[0],
            "activity": db.execute("SELECT COUNT(*) FROM paper_fund_activity").fetchone()[0],
        }
    finally:
        db.close()


engine = RecommendationIntelligenceEngine()
empty = engine.report(source_loader=lambda **_: {
    "records": [], "total": 0, "limit": 10000, "truncated": False, "filters": {}
}, now=NOW)
assert empty["status"] == "NOT_EVALUATED"
assert empty["summary"]["overall_accuracy"] is None
assert empty["summary"]["outcome_completion_rate"] is None
assert all(
    bucket["accuracy"] is None and bucket["sample_size"] == 0
    for bucket in empty["accuracy_by_confidence"]
)
assert all(
    bucket["calibration"] == "NO_DATA" and bucket["sample_size"] == 0
    for bucket in empty["confidence_calibration"]
)


def confidence_report(confidence):
    row = {
        "recommendation_id": 1,
        "outcome_id": 1,
        "ticker": "TEST",
        "action": "BUY",
        "confidence": confidence,
        "recommendation_at": "2026-01-01T12:00:00",
        "evaluation_at": "2026-01-08T12:00:00",
        "horizon_days": 7,
        "status": "Succeeded",
        "success": True,
        "percentage_return": 1.0,
    }
    return engine.report(source_loader=lambda **_: {
        "records": [row], "total": 1, "limit": 10000,
        "truncated": False, "filters": {},
    }, now=NOW)


for fractional, percentage, expected_bucket, expected_confidence in (
    (0.85, 85, "80-89", 85.0),
    (1.0, 100, "90-100", 100.0),
):
    fractional_report = confidence_report(fractional)
    percentage_report = confidence_report(percentage)
    buckets = {
        bucket["bucket"]: bucket
        for bucket in fractional_report["accuracy_by_confidence"]
    }
    calibration = {
        bucket["bucket"]: bucket
        for bucket in fractional_report["confidence_calibration"]
    }
    assert buckets[expected_bucket]["sample_size"] == 1
    assert calibration[expected_bucket]["average_confidence"] == expected_confidence
    assert (
        fractional_report["accuracy_by_confidence"]
        == percentage_report["accuracy_by_confidence"]
    )
    assert (
        fractional_report["confidence_calibration"]
        == percentage_report["confidence_calibration"]
    )


invalid_confidences = (-1, 101, True, "85", float("nan"), float("inf"), float("-inf"))
for invalid_confidence in invalid_confidences:
    invalid_report = confidence_report(invalid_confidence)
    assert sum(
        bucket["sample_size"]
        for bucket in invalid_report["accuracy_by_confidence"]
    ) == 0
    assert all(
        bucket["accuracy"] is None
        for bucket in invalid_report["accuracy_by_confidence"]
    )
    assert all(
        bucket["calibration"] == "NO_DATA"
        for bucket in invalid_report["confidence_calibration"]
    )


truncated = engine.report(source_loader=lambda **_: {
    "records": confidence_report(85)["best_performing_recommendations"],
    "total": 25,
    "limit": 1,
    "truncated": True,
    "filters": {},
}, now=NOW)
assert truncated["data"]["truncated"] is True
assert truncated["data"]["analyzed_row_count"] == 1
assert truncated["data"]["source_total_row_count"] == 25
assert "may be incomplete" in truncated["data"]["warning"]


with temp_database():
    seed_recommendation(1, "AAA", "BUY", 90, "2026-01-01T12:00:00")
    seed_recommendation(2, "BBB", "BUY", 80, "2026-01-02T12:00:00")
    seed_recommendation(3, "CCC", "HOLD", 60, "2026-01-03T12:00:00")
    seed_recommendation(4, "DDD", "AVOID", 40, "2026-01-04T12:00:00")
    seed_recommendation(5, "EEE", "BUY", 95, "2026-01-05T12:00:00")

    seed_outcome(1, 1, "AAA", "BUY", "Succeeded", 1, 10, 7, "2026-01-08T12:00:00")
    seed_outcome(2, 2, "BBB", "BUY", "Failed", 0, -3, 7, "2026-01-09T12:00:00")
    seed_outcome(3, 3, "CCC", "HOLD", "Succeeded", 1, 0.5, 7, "2026-01-10T12:00:00")
    seed_outcome(4, 4, "DDD", "AVOID", "Succeeded", 1, -8, 7, "2026-01-11T12:00:00")
    seed_outcome(5, 1, "AAA", "BUY", "Failed", 0, -5, 30, "2026-01-31T12:00:00")
    seed_outcome(6, 2, "BBB", "BUY", "Deferred", None, None, 30, "2026-01-31T12:00:00")
    seed_outcome(7, 3, "CCC", "HOLD", "Expired", None, None, 30, "2026-01-31T12:00:00")

    before = counts()
    report = engine.report(now=NOW)
    assert report["status"] == "EVALUATED"
    assert report["generated_at"] == NOW.isoformat()
    assert report["summary"] == {
        "overall_accuracy": 60.0,
        "accuracy_scope": "recommendation_horizon_evaluations",
        "multiple_horizons_weight_separately": True,
        "unique_recommendation_accuracy": "NOT_EVALUATED",
        "recommendation_volume": 5,
        "completed_evaluations": 6,
        "accuracy_evaluations": 5,
        "pending_evaluations": 1,
        "outcome_completion_rate": 85.71,
        "recommendations_without_outcomes": 1,
        "recommendation_outcome_coverage": 80.0,
    }
    assert report["data"]["accuracy_sample_explanation"] == (
        "Each Succeeded or Failed completed horizon is a separate accuracy sample; "
        "an older recommendation with five such completed horizons contributes five "
        "evaluation samples."
    )

    assert report["accuracy_by_action"]["BUY"] == {
        "accuracy": 33.33, "successful": 1, "failed": 2, "sample_size": 3,
    }
    assert report["accuracy_by_action"]["HOLD"]["accuracy"] == 100.0
    assert report["accuracy_by_action"]["AVOID"]["accuracy"] == 100.0

    buckets = {row["bucket"]: row for row in report["accuracy_by_confidence"]}
    assert buckets["90-100"]["accuracy"] == 50.0
    assert buckets["80-89"]["accuracy"] == 0.0
    assert buckets["60-69"]["accuracy"] == 100.0
    assert buckets["0-49"]["accuracy"] == 100.0
    calibration = {row["bucket"]: row for row in report["confidence_calibration"]}
    assert calibration["90-100"]["calibration"] == "OVERCONFIDENT"
    assert calibration["90-100"]["calibration_gap"] == 40.0
    assert calibration["0-49"]["calibration"] == "UNDERCONFIDENT"
    assert calibration["0-49"]["calibration_gap"] == -60.0

    assert report["average_returns_by_action"] == {
        "BUY": {"average_return": 0.67, "sample_size": 3},
        "HOLD": {"average_return": 0.5, "sample_size": 1},
        "AVOID": {"average_return": -8.0, "sample_size": 1},
    }
    assert report["best_performing_recommendations"][0]["percentage_return"] == 10.0
    assert report["worst_performing_recommendations"][0]["percentage_return"] == -8.0
    assert report["worst_performing_recommendations"][0]["success"] is True

    rolling = report["rolling_accuracy"]
    assert [point["outcome_id"] for point in rolling] == [1, 2, 3, 4, 5]
    assert rolling[-1]["accuracy"] == 60.0
    assert rolling[-1]["sample_size"] == 5
    assert report["recommendation_volume"]["by_action"] == {
        "BUY": 3, "HOLD": 1, "AVOID": 1, "UNKNOWN": 0,
    }
    assert report["outcome_status"] == {
        "total_evaluations": 7,
        "completed": 6,
        "pending": 1,
        "deferred": 1,
        "expired": 1,
        "succeeded": 3,
        "failed": 2,
        "completion_rate": 85.71,
    }
    assert report["policy"]["read_only"] is True
    assert report["policy"]["uses_ai"] is False
    assert counts() == before

    # Repository selectors preserve exact recommendation identity and horizons.
    selected = get_recommendation_intelligence_records(
        ticker="aaa", action="buy", horizon=30, evaluation_source="paper", limit=50
    )
    assert selected["total"] == 1
    assert selected["records"][0]["recommendation_id"] == 1
    assert selected["records"][0]["outcome_id"] == 5
    assert selected["filters"] == {
        "ticker": "AAA", "action": "BUY", "horizon": 30,
        "evaluation_source": "paper",
    }

    # Read-only APIs expose analytics and selector-ready records with validation.
    original_provider = os.environ.get("MARKET_DATA_PROVIDER")
    os.environ["MARKET_DATA_PROVIDER"] = "mock"
    try:
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        records_response_schema = (
            app.openapi()["paths"]["/recommendation-intelligence/records"]["get"]
            ["responses"]["200"]["content"]["application/json"]["schema"]
        )
        assert records_response_schema == {
            "$ref": "#/components/schemas/RecommendationIntelligenceRecordsResponse"
        }
        response = client.get("/recommendation-intelligence?rolling_window=3&top_limit=2")
        assert response.status_code == 200
        payload = response.json()["recommendation_intelligence"]
        assert payload["summary"]["overall_accuracy"] == 60.0
        assert payload["summary"]["accuracy_scope"] == "recommendation_horizon_evaluations"
        assert payload["summary"]["multiple_horizons_weight_separately"] is True
        assert payload["summary"]["unique_recommendation_accuracy"] == "NOT_EVALUATED"
        assert payload["rolling_accuracy"][-1]["sample_size"] == 3
        assert len(payload["best_performing_recommendations"]) == 2

        records = client.get(
            "/recommendation-intelligence/records?ticker=aaa&action=BUY&horizon=7&limit=999999"
        )
        assert records.status_code == 200
        body = records.json()
        assert set(body) == {"recommendation_intelligence_records", "meta"}
        assert set(body["meta"]) == {
            "total", "limit", "truncated", "filters", "read_only",
        }
        assert body["meta"]["filters"] == {
            "ticker": "AAA",
            "action": "BUY",
            "horizon": 7,
            "evaluation_source": "paper",
        }
        assert body["meta"]["limit"] == 10000
        assert body["meta"]["read_only"] is True
        expected_records = get_recommendation_intelligence_records(
            ticker="aaa",
            action="BUY",
            horizon=7,
            evaluation_source="paper",
            limit=999999,
        )
        assert body["recommendation_intelligence_records"] == expected_records["records"]
        assert body["recommendation_intelligence_records"][0]["recommendation_id"] == 1
        assert client.get("/recommendation-intelligence?action=SELL").status_code == 422
        assert client.get("/recommendation-intelligence?horizon=0").status_code == 422
        assert client.get("/recommendation-intelligence?rolling_window=0").status_code == 422

        operations = client.get("/operations")
        assert operations.status_code == 200
        visibility = operations.json()["recommendation_intelligence"]
        assert visibility["overall_accuracy"] == 60.0
        assert visibility["policy"]["changes_trading_behavior"] is False
        assert counts() == before
    finally:
        if original_provider is None:
            os.environ.pop("MARKET_DATA_PROVIDER", None)
        else:
            os.environ["MARKET_DATA_PROVIDER"] = original_provider


print("Recommendation Intelligence Sprint 2.0 tests passed.")
