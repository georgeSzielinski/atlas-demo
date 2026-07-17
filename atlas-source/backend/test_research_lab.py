import os
import tempfile

import database.connection as connection
from api.main import (
    experiments_active_dashboard,
    experiments_dashboard,
    experiments_history_dashboard,
    research_lab_dashboard,
    validation_latest_dashboard,
)
from database.repository import (
    get_registry_experiments,
    save_registry_experiment,
)
from database.setup import setup_database
from engines.research_lab_engine import ResearchLabEngine


def row(index, ticker, price, future_price, month_return, volatility):
    return {
        "date": f"2024-01-{index:02d}",
        "validation_date": f"2024-02-{index:02d}",
        "ticker": ticker,
        "asset_type": "Stock",
        "price": price,
        "future_price": future_price,
        "week_return": month_return / 4,
        "month_return": month_return,
        "moving_average_20": price * 0.98,
        "moving_average_50": price * 0.95,
        "price_vs_20ma": 2,
        "price_vs_50ma": 5,
        "rsi": 58,
        "macd": 1,
        "macd_signal": 0.5,
        "macd_trend": "Bullish",
        "volatility": volatility,
        "trend": "Bullish" if month_return >= 0 else "Bearish",
        "score": 4,
        "fundamental_score": 68,
        "forecast_score": 72 if future_price >= price else 40,
        "news_confidence": 62,
        "portfolio_score": 66,
        "risk_score": 70,
        "committee_agreement": 74,
        "executive_confidence": 76,
        "stability_score": 79,
        "knowledge_score": 77,
    }


historical_data = []
for day in range(1, 16):
    historical_data.append(row(day, "AAPL", 100 + day, 104 + day, 3.0, 2.0))
    historical_data.append(row(day, "MSFT", 200 + day, 198 + day, -1.5, 3.0))

historical_data = sorted(
    historical_data,
    key=lambda item: (item["date"], item["ticker"]),
)

engine = ResearchLabEngine()

# ------------------------------------------------------------------
# Part 1 - Experiment Registry
# ------------------------------------------------------------------
experiment = engine.create_experiment(
    title="Probability calibration refinement",
    description="Test a recalibrated probability curve.",
    feature_being_tested="Probability calibration",
    baseline_strategy="Current Atlas",
    candidate_strategy="No News",
    priority="High",
    status="READY_FOR_TEST",
    created_date="2026-06-20T09:00:00",
)

assert experiment["experiment_id"].startswith("exp-")
assert experiment["status"] == "READY_FOR_TEST"
assert experiment["priority"] == "High"
assert experiment["validation_state"] == "Not Enough Evidence"
assert experiment["policy"]["changes_recommendation_behavior"] is False
assert experiment["policy"]["automatic_adoption"] is False

# Deterministic experiment id.
duplicate = engine.create_experiment(
    title="Probability calibration refinement",
    description="Different description does not affect the id.",
    feature_being_tested="Probability calibration",
    baseline_strategy="Current Atlas",
    candidate_strategy="No News",
    created_date="2026-06-20T09:00:00",
)
assert duplicate["experiment_id"] == experiment["experiment_id"]

# Invalid state and priority fall back to safe defaults.
guarded = engine.create_experiment(
    title="Guarded",
    description="",
    feature_being_tested="Feature",
    baseline_strategy="Current Atlas",
    candidate_strategy="No News",
    status="NOT_A_STATE",
    priority="Critical",
    created_date="2026-06-20T09:00:00",
)
assert guarded["status"] == "PROPOSED"
assert guarded["priority"] == "Medium"

# ------------------------------------------------------------------
# Part 3 + Part 4 - Simulation Arena + Scientific Validation reuse
# ------------------------------------------------------------------
result = engine.run_experiment(
    experiment,
    dataset="deterministic-lab-fixture",
    tickers=["AAPL", "MSFT"],
    date_range={"start": "2024-01-01", "end": "2024-01-15"},
    validation_window=10,
    historical_data=historical_data,
    run_date="2026-06-30T13:00:00",
)

assert result["arena_id"].startswith("arena-")
assert result["baseline_strategy"] == "Current Atlas"
assert result["candidate_strategy"] == "No News"
assert set(result["baseline_metrics"].keys()) == set(engine.ARENA_METRICS)
assert set(result["candidate_metrics"].keys()) == set(engine.ARENA_METRICS)
assert result["baseline_metrics"]["alpha"] == 0
assert result["validation"]["scientific_result"] in engine.VALIDATION_STATES
assert result["validation"]["adoption_decision"] in {"ADOPT", "RETEST", "REJECT"}
assert result["validation"]["policy"]["changes_recommendation_behavior"] is False
assert result["experiment"]["status"] == "VALIDATING"
assert result["experiment"]["validation_state"] == result["validation"]["scientific_result"]

# Determinism: running twice yields identical metrics.
result_again = engine.run_experiment(
    experiment,
    dataset="deterministic-lab-fixture",
    tickers=["AAPL", "MSFT"],
    date_range={"start": "2024-01-01", "end": "2024-01-15"},
    validation_window=10,
    historical_data=historical_data,
    run_date="2026-06-30T13:00:00",
)
assert result_again["candidate_metrics"] == result["candidate_metrics"]
assert result_again["arena_id"] == result["arena_id"]

# ------------------------------------------------------------------
# Part 7 - Experiment Comparison
# ------------------------------------------------------------------
comparison = result["comparison"]
assert len(comparison["rows"]) == len(engine.ARENA_METRICS)
assert all(
    set(comparison_row.keys())
    == {"metric", "baseline", "candidate", "difference", "improved"}
    for comparison_row in comparison["rows"]
)

# ------------------------------------------------------------------
# Parts 2, 5, 6, 8 - Queue, Timeline, Roadmap, History on examples
# ------------------------------------------------------------------
examples = engine.default_experiments()
assert len(examples) == 6
assert {item["status"] for item in examples} >= {
    "PROPOSED",
    "READY_FOR_TEST",
    "RUNNING",
    "VALIDATING",
    "REJECTED",
    "ADOPTED",
}

queue = engine.build_queue(examples)
assert set(queue.keys()) == {
    "highest_priority",
    "waiting",
    "running",
    "recently_completed",
}
assert all(
    item["status"] not in engine.COMPLETED_STATES
    for item in queue["highest_priority"]
)
assert all(item["status"] == "RUNNING" for item in queue["running"])

timeline = engine.build_timeline(examples)
assert set(timeline.keys()) == {"planned", "active", "completed", "rejected"}
assert all(item["status"] == "REJECTED" for item in timeline["rejected"])

roadmap = engine.build_roadmap(examples)
assert set(roadmap.keys()) == {"High", "Medium", "Low"}
assert roadmap["High"]
assert roadmap["Low"]

# Roadmap defaults appear when there are no open experiments.
empty_roadmap = engine.build_roadmap([])
assert empty_roadmap["High"][0]["title"] == "Improve probability calibration."
assert empty_roadmap["Medium"][0]["title"] == "Study macro weighting."
assert empty_roadmap["Low"][0]["title"] == "Alternative technical indicators."

history = engine.build_history(examples)
assert "Probability calibration" in history["features"]
assert "REJECTED" in history["statuses"]

# Search by feature, status, and result.
by_feature = engine.search_history(examples, feature="Macro")
assert all(
    "macro" in item["feature_being_tested"].lower() for item in by_feature
)
by_status = engine.search_history(examples, status="ADOPTED")
assert all(item["status"] == "ADOPTED" for item in by_status)
by_result = engine.search_history(examples, result="Regression")
assert all(item["validation_state"] == "Regression" for item in by_result)

# ------------------------------------------------------------------
# Part 9 - Operations summary
# ------------------------------------------------------------------
operations = engine.operations_summary(examples)
assert operations["active_experiment_count"] >= 1
assert "research_progress" in operations
assert operations["research_progress"]["total_experiments"] == 6
assert operations["research_progress"]["completion_rate"] >= 0
assert operations["policy"]["human_approval_required"] is True

# ------------------------------------------------------------------
# Persistence + dashboard + API
# ------------------------------------------------------------------
original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    setup_database()

    # Empty registry falls back to deterministic examples.
    empty_dashboard = engine.laboratory_dashboard()
    assert empty_dashboard["experiment_count"] == 6
    assert empty_dashboard["policy"]["broker_integration"] is False

    save_registry_experiment(result["experiment"])
    saved = get_registry_experiments(limit=10)
    assert len(saved) == 1
    assert saved[0]["experiment_id"] == experiment["experiment_id"]
    assert saved[0]["status"] == "VALIDATING"
    assert set(saved[0]["arena_metrics"]["candidate"].keys()) == set(
        engine.ARENA_METRICS
    )

    dashboard = engine.laboratory_dashboard()
    assert dashboard["experiment_count"] == 1
    assert dashboard["experiments"][0]["experiment_id"] == experiment["experiment_id"]
    assert "queue" in dashboard
    assert "timeline" in dashboard
    assert "roadmap" in dashboard

    api_lab = research_lab_dashboard()
    assert api_lab["experiment_count"] == 1
    assert api_lab["policy"]["changes_recommendation_behavior"] is False

    api_experiments = experiments_dashboard()
    assert api_experiments["experiment_count"] == 1
    assert experiment["experiment_id"] in {
        item["experiment_id"] for item in api_experiments["experiments"]
    }

    api_history = experiments_history_dashboard(status="VALIDATING")
    assert all(
        item["status"] == "VALIDATING" for item in api_history["results"]
    )

    api_active = experiments_active_dashboard()
    assert experiment["experiment_id"] in {
        item["experiment_id"] for item in api_active["active_experiments"]
    }

    api_validation = validation_latest_dashboard()
    assert api_validation["policy"]["automatic_adoption"] is False
finally:
    connection.DATABASE_PATH = original_database_path
    if os.path.exists(database_path):
        os.remove(database_path)

print("ResearchLabEngine test passed.")
