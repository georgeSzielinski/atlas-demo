import tempfile

import database.connection as connection
from database.repository import (
    get_latest_benchmark_results,
    get_latest_evidence_benchmarks,
)
from database.setup import setup_database
from engines.benchmark_engine import BenchmarkEngine


engine = BenchmarkEngine()
benchmark_date = "2026-01-15T09:30:00"
validation_results = [
    {
        "recommendation": "BUY",
        "percentage_return": 12,
        "success": True,
        "hit": True,
        "status": "Succeeded",
        "confidence": 85,
        "signal_quality_score": 9,
    },
    {
        "recommendation": "BUY",
        "percentage_return": -4,
        "success": False,
        "hit": False,
        "status": "Failed",
        "confidence": 40,
        "signal_quality_score": 5,
    },
    {
        "recommendation": "HOLD",
        "percentage_return": 0.5,
        "success": True,
        "hit": True,
        "status": "Succeeded",
        "confidence": 72,
        "signal_quality_score": 7,
    },
    {
        "recommendation": "AVOID",
        "percentage_return": 6,
        "success": False,
        "hit": False,
        "status": "Failed",
        "confidence": 55,
        "signal_quality_score": 4,
    },
    {
        "recommendation": "AVOID",
        "percentage_return": None,
        "success": None,
        "hit": None,
        "status": "Pending",
        "confidence": 90,
        "signal_quality_score": 8,
    },
]

recommendation_rows = engine.benchmark_recommendations(
    validation_results,
    benchmark_date=benchmark_date,
    notes="Deterministic ABS test.",
)
recommendation_metrics = {
    row["metric"]: row["value"] for row in recommendation_rows
}
benchmark_thresholds = (
    engine.HIGH_CONFIDENCE_THRESHOLD,
    engine.HIGH_SIGNAL_QUALITY_THRESHOLD,
)

assert recommendation_metrics["buy_accuracy"] == 50
assert recommendation_metrics["per_engine_accuracy"] == 50
assert recommendation_metrics["rolling_accuracy"] == 33.33
assert recommendation_metrics["hold_accuracy"] == 100
assert recommendation_metrics["avoid_accuracy"] == 0
assert recommendation_metrics["overall_hit_rate"] == 50
assert recommendation_metrics["recommendation_accuracy"] == 50
assert recommendation_metrics["validation_success"] == 50
assert recommendation_metrics["average_return"] == 3.62
assert recommendation_metrics["average_gain"] == 6.17
assert recommendation_metrics["average_loss"] == -4
assert recommendation_metrics["average_recommendation_lifetime"] == 0
assert recommendation_metrics["rolling_performance"] == 0.83
assert recommendation_metrics["high_confidence_accuracy"] == 100
assert recommendation_metrics["low_confidence_accuracy"] == 0
assert recommendation_metrics["confidence_calibration"] == 100

for row in recommendation_rows:
    assert row["requires_human_approval"] is True
    assert "suggested_adjustment" in row
    assert "adjustment_reason" in row
    assert "benchmark_snapshot" in row

avoid_accuracy = next(
    row for row in recommendation_rows
    if row["metric"] == "avoid_accuracy"
)

assert avoid_accuracy["suggested_adjustment"] == (
    "review_signal_weight_or_threshold"
)
assert engine.HIGH_CONFIDENCE_THRESHOLD == benchmark_thresholds[0]
assert engine.HIGH_SIGNAL_QUALITY_THRESHOLD == benchmark_thresholds[1]

signal_rows = engine.benchmark_signal_quality(
    validation_results,
    benchmark_date=benchmark_date,
)
signal_metrics = {row["metric"]: row["value"] for row in signal_rows}

assert signal_metrics["high_signal_quality_accuracy"] == 100
assert signal_metrics["low_signal_quality_accuracy"] == 0
assert signal_metrics["sample_count"] == 4

forecast_rows = engine.benchmark_forecasts(
    [
        {"predicted_direction": "UP", "actual_direction": "UP"},
        {"predicted_direction": "DOWN", "actual_direction": "UP"},
        {"predicted_direction": "FLAT", "actual_direction": "FLAT"},
    ],
    benchmark_date=benchmark_date,
)
forecast_metrics = {row["metric"]: row["value"] for row in forecast_rows}

assert forecast_metrics["direction_accuracy"] == 66.67
assert forecast_metrics["mae"] is None
assert forecast_metrics["rmse"] is None
assert forecast_metrics["runtime"] is None
assert all(row["requires_human_approval"] is True for row in forecast_rows)

evidence_rows = engine.benchmark_evidence_sources(
    [
        {
            "source_name": "forecast",
            "effectiveness_score": 72.5,
            "sample_count": 20,
        },
        {
            "source_name": "news",
            "effectiveness_score": 61,
            "sample_count": 15,
        },
    ],
    benchmark_date=benchmark_date,
)

assert evidence_rows[0]["source_name"] == "forecast"
assert evidence_rows[0]["effectiveness_score"] == 72.5
assert evidence_rows[0]["sample_count"] == 20

with tempfile.NamedTemporaryFile(suffix=".db") as database_file:
    connection.DATABASE_PATH = database_file.name
    setup_database()
    engine.save_benchmark_results(recommendation_rows + forecast_rows)
    engine.save_evidence_benchmarks(evidence_rows)

    saved_benchmarks = get_latest_benchmark_results(limit=20)
    saved_evidence = get_latest_evidence_benchmarks(limit=20)

    assert len(saved_benchmarks) == len(recommendation_rows + forecast_rows)
    assert any(
        row["metric"] == "overall_hit_rate" and row["value"] == 50
        for row in saved_benchmarks
    )
    assert any(
        row["source_name"] == "forecast"
        and row["effectiveness_score"] == 72.5
        and row["sample_count"] == 20
        for row in saved_evidence
    )

print("BenchmarkEngine test passed.")
