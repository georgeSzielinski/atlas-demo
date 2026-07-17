"""Deterministic Learning Intelligence tests; all database writes use temp DBs."""

import os
import tempfile
from contextlib import contextmanager
from datetime import datetime

import database.connection as connection
from database.connection import get_connection
from database.migrator import run_migrations
from database.repository import get_learning_intelligence_records
from engines.committee_intelligence_engine import CommitteeIntelligenceEngine
from engines.engine_intelligence_engine import EngineIntelligenceEngine
from engines.learning_center_engine import LearningCenterEngine


NOW = datetime(2026, 7, 15, 12, 0, 0)


@contextmanager
def temp_database():
    original = connection.DATABASE_PATH
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as handle:
        path = handle.name
    connection.DATABASE_PATH = path
    connection._wal_initialized_paths.discard(path)
    try:
        run_migrations()
        yield
    finally:
        connection.DATABASE_PATH = original
        connection._wal_initialized_paths.discard(path)
        for candidate in (path, f"{path}-wal", f"{path}-shm"):
            if os.path.exists(candidate):
                os.remove(candidate)


RECORDS = [
    {
        "recommendation_id": 1,
        "run_id": 10,
        "ticker": "AAA",
        "action": "BUY",
        "confidence": 0.8,
        "recommendation_at": "2026-01-01T12:00:00",
        "committee_members": [{"name": "Technical"}],
        "committee_agreement": 75,
        "evidence_breakdown": [
            {"category": "Technical", "confidence": 0.8, "weight": 0.6},
            {"category": "Risk", "confidence": 70, "weight": 0.4},
        ],
        "sector": "Technology",
        "market_regime": "Bull",
        "forecast_direction": "Up",
        "news_sentiment": "Positive",
        "signal_label": "Strong",
        "outcome_id": 11,
        "horizon_days": 7,
        "evaluation_source": "paper",
        "status": "Succeeded",
        "percentage_return": 5,
        "evaluation_at": "2026-01-08T12:00:00",
        "starting_price": 100,
        "ending_price": 105,
    },
    {
        "recommendation_id": 1,
        "run_id": 10,
        "ticker": "AAA",
        "action": "BUY",
        "confidence": 80,
        "recommendation_at": "2026-01-01T12:00:00",
        "committee_members": [{"name": "Technical"}],
        "committee_agreement": 75,
        "evidence_breakdown": [
            {"category": "Technical", "confidence": 80, "weight": 0.6},
            {"category": "Risk", "confidence": 70, "weight": 0.4},
        ],
        "sector": "Technology",
        "market_regime": "Bull",
        "forecast_direction": "Up",
        "outcome_id": 12,
        "horizon_days": 30,
        "evaluation_source": "paper",
        "status": "Failed",
        "percentage_return": -2,
        "evaluation_at": "2026-01-31T12:00:00",
        "starting_price": 100,
        "ending_price": 98,
    },
    {
        "recommendation_id": 1,
        "ticker": "AAA",
        "action": "BUY",
        "confidence": 80,
        "committee_members": [{"name": "Technical"}],
        "committee_agreement": 75,
        "evidence_breakdown": [{"category": "Technical", "confidence": 80, "weight": 0.6}],
        "outcome_id": 13,
        "horizon_days": 90,
        "status": "Pending",
        "evaluation_source": "paper",
    },
    # Exact duplicate outcome id must not double-weight analytics.
    {
        "recommendation_id": 1,
        "ticker": "AAA",
        "outcome_id": 13,
        "horizon_days": 90,
        "status": "Pending",
    },
    {
        "recommendation_id": 2,
        "ticker": "BBB",
        "action": "AVOID",
        "confidence": 60,
        "recommendation_at": "2026-01-02T12:00:00",
        "committee_members": [{"name": "Fundamental"}],
        "committee_agreement": 60,
        "evidence_breakdown": [{"category": "Fundamental", "confidence": 60, "weight": 1}],
        "sector": "Financials",
        "market_regime": "Bear",
        "outcome_id": 21,
        "horizon_days": 7,
        "evaluation_source": "paper",
        "status": "Deferred",
    },
    {
        "recommendation_id": 2,
        "ticker": "BBB",
        "action": "AVOID",
        "confidence": 60,
        "recommendation_at": "2026-01-02T12:00:00",
        "committee_members": [{"name": "Fundamental"}],
        "committee_agreement": 60,
        "evidence_breakdown": [{"category": "Fundamental", "confidence": 60, "weight": 1}],
        "sector": "Financials",
        "market_regime": "Bear",
        "outcome_id": 22,
        "horizon_days": 30,
        "evaluation_source": "paper",
        "status": "Expired",
        "evaluation_at": "2026-02-01T12:00:00",
    },
    {
        "recommendation_id": 3,
        "ticker": "CCC",
        "action": "HOLD",
        "confidence": True,
        "recommendation_at": "2026-01-03T12:00:00",
        "outcome_id": None,
    },
    None,
    {"recommendation_id": None, "outcome_id": 99, "status": "Succeeded", "horizon_days": 7},
    {"recommendation_id": 1, "outcome_id": 98, "status": "nonsense", "horizon_days": "bad"},
]


def source(records=RECORDS, truncated=False):
    return {
        "records": list(records),
        "total": 25 if truncated else len(records),
        "limit": len(records),
        "truncated": truncated,
        "filters": {"evaluation_source": "paper"},
    }


loader_calls = []


def loader(**filters):
    loader_calls.append(filters)
    return source()


report = LearningCenterEngine().report(source_loader=loader, now=NOW, rolling_window=2)
assert len(loader_calls) == 1, "one shared bounded projection must feed all analytics"
assert report["summary"]["recommendation_volume"] == 3
assert report["summary"]["overall_recommendation_accuracy"] == 50.0
assert report["summary"]["completed_evaluations"] == 3
assert report["summary"]["pending_evaluations"] == 1
assert report["summary"]["deferred_evaluations"] == 1
assert report["summary"]["expired_evaluations"] == 1
assert report["summary"]["outcome_completion_rate"] == 60.0
assert report["summary"]["recommendation_coverage"] == 66.67
assert report["summary"]["average_return"] == 1.5
assert report["summary"]["data_maturity"] == "LIMITED"
assert report["data"]["accuracy_sample_explanation"].endswith("evaluation samples.")
assert report["confidence_calibration"]["status"] == "INSUFFICIENT_SAMPLE"
assert report["confidence_calibration"]["statistical_confidence"] == "NOT_EVALUATED"
assert len(report["rolling_accuracy"]) == 2
assert report["best_recommendations"][0]["recommendation_id"] == 1
assert report["worst_recommendations"][0]["percentage_return"] == -2.0
assert {row["status"]: row["count"] for row in report["outcome_distribution"]} == {
    "Succeeded": 1, "Failed": 1, "Pending": 1, "Deferred": 1, "Expired": 1,
}
assert [row["horizon_days"] for row in report["evaluation_maturity_by_horizon"]] == [
    7, 30, 90, 180, 365,
]
assert report["evaluation_maturity_by_horizon"][3]["status"] == "NOT_EVALUATED"
assert report["sector_intelligence"]["status"] == "EVALUATED"
assert report["regime_intelligence"]["status"] == "EVALUATED"
assert any(row["signal"] == "RSI" for row in report["signal_intelligence"]["unavailable"])
assert report["policy"]["read_only"] is True
assert report["policy"]["changes_recommendation_behavior"] is False

committee = report["committee_intelligence"]
assert committee["status"] == "EVALUATED"
assert committee["committees"][0]["committee"] == "Investment Committee"
assert committee["committees"][0]["recommendation_count"] == 2
assert committee["committees"][0]["accuracy"] == 50.0

engines = report["engine_intelligence"]
assert {row["engine"] for row in engines["engines"]} == {"Technical", "Risk", "Fundamental"}
assert engines["data"]["relationship_scope"] == "stored_recommendation_evidence_association"
assert engines["policy"]["causal_attribution"] is False

context = {row["recommendation_id"]: row for row in report["recommendation_metrics"]}
assert context[1]["primary_engine"] == "Technical"
assert context[1]["engine_historical_accuracy"] == 50.0
assert context[1]["evaluation_maturity"] == 40.0
assert context[3]["recommendation_maturity"] == "NOT_EVALUATED"

empty = LearningCenterEngine().report(source_loader=lambda **_: source([]), now=NOW)
assert empty["status"] == "NOT_EVALUATED"
assert empty["summary"]["overall_recommendation_accuracy"] is None
assert empty["summary"]["outcome_completion_rate"] is None
assert empty["summary"]["recommendation_coverage"] is None
assert empty["summary"]["average_return"] is None

truncated = LearningCenterEngine().report(
    source_loader=lambda **_: source(RECORDS[:1], truncated=True), now=NOW
)
assert truncated["data"]["truncated"] is True
assert truncated["data"]["analyzed_row_count"] == 1
assert truncated["data"]["source_total_row_count"] == 25
assert "may be incomplete" in truncated["data"]["warning"]

unknown_committee = CommitteeIntelligenceEngine().report(
    committee="Unknown", source_loader=lambda **_: source(), now=NOW
)
unknown_engine = EngineIntelligenceEngine().report(
    engine="Unknown", source_loader=lambda **_: source(), now=NOW
)
assert unknown_committee["status"] == "NOT_EVALUATED"
assert unknown_engine["status"] == "NOT_EVALUATED"

for status, expected in (
    ("Pending", {"completed": 0, "pending": 1, "deferred": 0, "expired": 0, "coverage": 0.0}),
    ("Deferred", {"completed": 0, "pending": 0, "deferred": 1, "expired": 0, "coverage": 0.0}),
    ("Expired", {"completed": 1, "pending": 0, "deferred": 0, "expired": 1, "coverage": 100.0}),
):
    status_record = [{
        "recommendation_id": 1,
        "ticker": "AAA",
        "action": "BUY",
        "confidence": 80,
        "outcome_id": 1,
        "horizon_days": 7,
        "status": status,
    }]
    status_report = LearningCenterEngine().report(
        source_loader=lambda rows=status_record, **_: source(rows), now=NOW
    )
    assert status_report["summary"]["overall_recommendation_accuracy"] is None
    assert status_report["summary"]["completed_evaluations"] == expected["completed"]
    assert status_report["summary"]["pending_evaluations"] == expected["pending"]
    assert status_report["summary"]["deferred_evaluations"] == expected["deferred"]
    assert status_report["summary"]["expired_evaluations"] == expected["expired"]
    assert status_report["summary"]["recommendation_coverage"] == expected["coverage"]

unknown_dimension = LearningCenterEngine().report(
    sector="Unknown",
    regime="Unknown",
    source_loader=lambda **_: source([]),
    now=NOW,
)
assert unknown_dimension["sector_intelligence"]["status"] == "NOT_EVALUATED"
assert unknown_dimension["regime_intelligence"]["status"] == "NOT_EVALUATED"

# Performance sanity: a linear 5,000-row projection completes and preserves count.
bulk = [
    {
        "recommendation_id": index,
        "ticker": f"T{index}",
        "action": "BUY",
        "confidence": 75,
        "outcome_id": index,
        "horizon_days": 7,
        "status": "Succeeded",
        "percentage_return": 1,
    }
    for index in range(5000)
]
bulk_report = LearningCenterEngine().report(source_loader=lambda **_: source(bulk), now=NOW)
assert bulk_report["summary"]["recommendation_volume"] == 5000
assert bulk_report["summary"]["accuracy_evaluations"] == 5000


with temp_database():
    db = get_connection()
    try:
        db.execute(
            "INSERT INTO recommendations "
            "(id, run_id, ticker, action, confidence, created_at, committee_members, "
            "committee_agreement, evidence_breakdown, sector, market_regime) "
            "VALUES (1, 1, 'AAA', 'BUY', 85, '2026-01-01T12:00:00', ?, 80, ?, "
            "'Technology', 'Bull')",
            ('[{"name":"Technical"}]', '[{"category":"Technical","confidence":85,"weight":1}]'),
        )
        db.execute(
            "INSERT INTO recommendation_validations "
            "(id, recommendation_id, ticker, recommendation, status, success, "
            "percentage_return, horizon_days, evaluation_source) "
            "VALUES (1, 1, 'AAA', 'BUY', 'Succeeded', 1, 4, 7, 'paper')"
        )
        db.commit()
        before = db.total_changes
    finally:
        db.close()

    selected = get_learning_intelligence_records(limit=100000)
    assert selected["limit"] == 100000
    assert selected["records"][0]["committee_members"][0]["name"] == "Technical"
    assert selected["records"][0]["evidence_breakdown"][0]["category"] == "Technical"
    db = get_connection()
    try:
        assert db.total_changes == 0
        assert db.execute("SELECT COUNT(*) FROM recommendations").fetchone()[0] == 1
    finally:
        db.close()


# API validation and read-only GET route coverage use an injected source.
original_learning_source = LearningCenterEngine._source
original_committee_source = CommitteeIntelligenceEngine._source
original_engine_source = EngineIntelligenceEngine._source
LearningCenterEngine._source = lambda self, **_: source()
CommitteeIntelligenceEngine._source = lambda self, **_: source()
EngineIntelligenceEngine._source = lambda self, **_: source()
try:
    os.environ["MARKET_DATA_PROVIDER"] = "mock"
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)
    openapi_schema = app.openapi()
    learning_response_schema = (
        openapi_schema["paths"]["/learning-center"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]
    )
    assert learning_response_schema == {
        "$ref": "#/components/schemas/LearningCenterResponse"
    }
    status_response_schema = (
        openapi_schema["paths"]["/learning-center/status"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]
    )
    assert status_response_schema == {
        "$ref": "#/components/schemas/LearningCenterStatusResponse"
    }

    learning_response = client.get("/learning-center")
    assert learning_response.status_code == 200
    assert set(learning_response.json()) == {"learning_center"}
    learning_payload = learning_response.json()["learning_center"]
    assert set(learning_payload) == set(report)
    for section in (
        "summary",
        "confidence_calibration",
        "committee_intelligence",
        "engine_intelligence",
        "data",
        "policy",
    ):
        assert set(learning_payload[section]) == set(report[section])
    assert learning_payload["outcome_distribution"] == report["outcome_distribution"]
    assert learning_payload["confidence_calibration"]["status"] == "INSUFFICIENT_SAMPLE"

    LearningCenterEngine._source = lambda self, **_: source(bulk[:20])
    sufficient_sample_response = client.get("/learning-center")
    assert sufficient_sample_response.status_code == 200
    assert (
        sufficient_sample_response.json()["learning_center"]
        ["confidence_calibration"]["minimum_sample_warning"]
        is None
    )

    LearningCenterEngine._source = lambda self, **_: source([])
    empty_response = client.get("/learning-center")
    assert empty_response.status_code == 200
    assert set(empty_response.json()) == {"learning_center"}
    empty_payload = empty_response.json()["learning_center"]
    assert empty_payload["status"] == "NOT_EVALUATED"
    assert empty_payload["summary"]["overall_recommendation_accuracy"] is None
    assert empty_payload["summary"]["outcome_completion_rate"] is None
    assert empty_payload["summary"]["recommendation_coverage"] is None
    assert empty_payload["summary"]["average_return"] is None

    LearningCenterEngine._source = lambda self, **_: source()
    status_response = client.get("/learning-center/status")
    assert status_response.status_code == 200
    assert set(status_response.json()) == {"learning_center_status"}

    def unavailable_source(self, **_):
        raise RuntimeError("fixture unavailable")

    LearningCenterEngine._source = unavailable_source
    unavailable_response = client.get("/learning-center/status")
    assert unavailable_response.status_code == 200
    unavailable_payload = unavailable_response.json()["learning_center_status"]
    assert unavailable_payload["status"] == "Unavailable"
    assert set(unavailable_payload) == {
        "status",
        "reason",
        "summary",
        "committee_analytics_health",
        "engine_analytics_health",
        "truncated",
        "warning",
        "policy",
    }

    LearningCenterEngine._source = lambda self, **_: source()
    assert client.get("/committee-intelligence").status_code == 200
    assert client.get("/committee-intelligence/leaderboard").status_code == 200
    assert client.get("/committee-intelligence/status").status_code == 200
    assert client.get("/engine-intelligence").status_code == 200
    assert client.get("/engine-intelligence/leaderboard").status_code == 200
    assert client.get("/engine-intelligence/status").status_code == 200
    assert client.get("/learning-center?horizon=0").status_code == 422
    assert client.get("/learning-center?rolling_window=0").status_code == 422
    assert client.get("/learning-center?limit=100001").status_code == 422
finally:
    LearningCenterEngine._source = original_learning_source
    CommitteeIntelligenceEngine._source = original_committee_source
    EngineIntelligenceEngine._source = original_engine_source


print("Learning Intelligence tests passed.")
