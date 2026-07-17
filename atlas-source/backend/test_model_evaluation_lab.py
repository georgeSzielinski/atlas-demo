import os
import tempfile

import database.connection as connection
from api.main import model_evaluations_dashboard
from database.repository import (
    get_discovery_source_data,
    get_model_evaluations,
    get_research_dashboard_data,
    save_model_evaluations,
)
from database.setup import setup_database
from engines.discovery_engine import DiscoveryEngine
from engines.model_evaluation_lab import ModelEvaluationLab
from engines.performance_observatory import PerformanceObservatory
from engines.research_engine import ResearchEngine


candidates = [
    {
        "model_name": "Mock Forecast",
        "model_type": "forecast",
        "provider": "mock",
        "status": "available",
        "integration_difficulty": "Low",
        "sample_size": 20,
        "accuracy": 70,
        "win_rate": 68,
        "average_return": 2.2,
        "sharpe_ratio": 1.1,
        "max_drawdown": -4,
        "runtime_placeholder": 5,
        "memory_placeholder": 10,
        "cost_placeholder": 0,
    },
    {
        "model_name": "Kronos",
        "model_type": "forecast",
        "provider": "kronos",
        "status": "candidate",
        "integration_difficulty": "Medium",
        "sample_size": 20,
        "accuracy": 82,
        "win_rate": 78,
        "average_return": 4.5,
        "sharpe_ratio": 1.8,
        "max_drawdown": -3,
        "runtime_placeholder": 18,
        "memory_placeholder": 40,
        "cost_placeholder": 15,
    },
    {
        "model_name": "Chronos",
        "model_type": "forecast",
        "provider": "future",
        "status": "future_placeholder",
        "integration_difficulty": "High",
        "sample_size": 0,
        "accuracy": 0,
        "win_rate": 0,
        "average_return": 0,
        "sharpe_ratio": 0,
        "max_drawdown": 0,
        "runtime_placeholder": 0,
        "memory_placeholder": 0,
        "cost_placeholder": 0,
    },
    {
        "model_name": "TimesFM",
        "model_type": "forecast",
        "provider": "future",
        "status": "future_placeholder",
        "integration_difficulty": "High",
        "sample_size": 0,
        "accuracy": 0,
        "win_rate": 0,
        "average_return": 0,
        "sharpe_ratio": 0,
        "max_drawdown": 0,
        "runtime_placeholder": 0,
        "memory_placeholder": 0,
        "cost_placeholder": 0,
    },
    {
        "model_name": "FinBERT",
        "model_type": "sentiment",
        "provider": "future",
        "status": "future_placeholder",
        "integration_difficulty": "Medium",
        "sample_size": 0,
        "accuracy": 0,
        "win_rate": 0,
        "average_return": 0,
        "sharpe_ratio": 0,
        "max_drawdown": 0,
        "runtime_placeholder": 0,
        "memory_placeholder": 0,
        "cost_placeholder": 0,
    },
    {
        "model_name": "Financial RoBERTa",
        "model_type": "sentiment",
        "provider": "future",
        "status": "future_placeholder",
        "integration_difficulty": "Medium",
        "sample_size": 0,
        "accuracy": 0,
        "win_rate": 0,
        "average_return": 0,
        "sharpe_ratio": 0,
        "max_drawdown": 0,
        "runtime_placeholder": 0,
        "memory_placeholder": 0,
        "cost_placeholder": 0,
    },
]


lab = ModelEvaluationLab()
result = lab.evaluate(
    dataset="deterministic-model-fixture",
    date_range={"start": "2024-01-01", "end": "2024-03-31"},
    validation_window=30,
    candidates=candidates,
    evaluation_date="2026-06-30T11:00:00",
)

assert len(result["evaluations"]) == 6
assert result["rankings"]["best_overall"] == "Kronos"
assert result["rankings"]["best_accuracy"] == "Kronos"
assert result["rankings"]["best_risk_adjusted"] == "Kronos"
assert result["rankings"]["best_low_cost"] == "Mock Forecast"
assert result["rankings"]["best_speed"] == "Mock Forecast"
assert set(result["rankings"]["not_recommended"]) == {
    "Chronos",
    "FinBERT",
    "Financial RoBERTa",
    "TimesFM",
}
assert result["controlled_learning"]["can_suggest_model_adoption"] is True
assert result["controlled_learning"]["can_auto_adopt_models"] is False
assert result["controlled_learning"]["requires_human_approval"] is True

kronos = next(
    item for item in result["evaluations"]
    if item["model_name"] == "Kronos"
)
assert kronos["recommendation"] == "Candidate for human review"

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    setup_database()
    save_model_evaluations(result["evaluations"])

    saved = get_model_evaluations(limit=10)
    assert len(saved) == 6
    assert saved[0]["model_name"] == "Kronos"
    assert saved[0]["date_range"] == {
        "start": "2024-01-01",
        "end": "2024-03-31",
    }
    assert saved[0]["validation_window"] == 30
    assert saved[0]["sample_size"] == 20

    research_dashboard = get_research_dashboard_data()
    assert research_dashboard["model_evaluations"][0]["model_name"] == "Kronos"
    research_report = ResearchEngine().research_dashboard_data()
    assert (
        research_report["model_evaluation_report"]["rankings"]["best_overall"]
        == "Kronos"
    )
    assert (
        research_report["model_evaluation_report"]["controlled_learning"][
            "can_auto_adopt_models"
        ]
        is False
    )

    source_data = get_discovery_source_data()
    assert source_data["model_evaluations"][0]["model_name"] == "Kronos"

    observatory = PerformanceObservatory().generate(
        source_data=source_data,
        discovery_data={
            "recent_discoveries": [],
            "top_discoveries": [],
            "discovery_history": [],
        },
    )
    assert observatory["model_evaluation_summary"]["evaluation_count"] == 6
    assert (
        observatory["model_evaluation_summary"]["rankings"]["best_overall"]
        == "Kronos"
    )

    discoveries = DiscoveryEngine().analyze(
        source_data=source_data,
        discovery_date="2026-06-30T11:05:00",
    )
    descriptions = [item["description"] for item in discoveries]
    assert (
        "Kronos is the best overall model evaluation candidate."
        in descriptions
    )

    api_result = model_evaluations_dashboard()
    assert api_result["model_evaluations"][0]["model_name"] == "Kronos"
    assert (
        api_result["model_evaluation_report"]["controlled_learning"][
            "requires_human_approval"
        ]
        is True
    )
finally:
    connection.DATABASE_PATH = original_database_path
    if os.path.exists(database_path):
        os.remove(database_path)

print("ModelEvaluationLab test passed.")
