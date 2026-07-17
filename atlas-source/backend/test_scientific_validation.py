import os
import tempfile

import database.connection as connection
from api.main import scientific_validation_dashboard
from database.repository import (
    get_discovery_source_data,
    get_research_dashboard_data,
    get_scientific_validation_reports,
    save_scientific_validation_report,
)
from database.setup import setup_database
from engines.discovery_engine import DiscoveryEngine
from engines.knowledge_graph_engine import KnowledgeGraphEngine
from engines.performance_observatory import PerformanceObservatory
from engines.research_engine import ResearchEngine
from engines.scientific_validation_engine import ScientificValidationEngine


baseline = {
    "win_rate": 55,
    "average_return": 1.2,
    "sharpe_ratio": 0.8,
    "max_drawdown": -8,
    "probability_calibration": 70,
    "recommendation_accuracy": 62,
    "average_holding_period": 30,
    "trade_frequency": 5,
}
candidate = {
    "win_rate": 63,
    "average_return": 2.4,
    "sharpe_ratio": 1.2,
    "max_drawdown": -5,
    "probability_calibration": 78,
    "recommendation_accuracy": 69,
    "average_holding_period": 34,
    "trade_frequency": 6,
}
regimes = {
    regime: {"status": "Improved", "sample_size": 20}
    for regime in ScientificValidationEngine.REGIMES
}
generalization = {
    test: {"status": "Improved", "sample_size": 20}
    for test in ScientificValidationEngine.GENERALIZATION_TESTS
}

engine = ScientificValidationEngine()
report = engine.evaluate(
    experiment_id="sv-001",
    experiment_date="2026-06-30T12:00:00",
    feature_tested="Candidate Forecast Evidence Source",
    baseline=baseline,
    candidate=candidate,
    sample_size=60,
    regimes=regimes,
    generalization=generalization,
)

assert report["scientific_result"] == "Improved"
assert report["adoption_decision"] == "ADOPT"
assert report["policy"]["changes_recommendation_behavior"] is False
assert len(report["metric_comparison"]) == 8
assert len(report["cross_regime_validation"]) == 7
assert len(report["generalization_tests"]) == 4

small_sample = engine.evaluate(
    experiment_id="sv-002",
    experiment_date="2026-06-30T12:05:00",
    feature_tested="Tiny Sample Provider",
    baseline=baseline,
    candidate=candidate,
    sample_size=8,
    regimes=regimes,
    generalization=generalization,
)
assert small_sample["scientific_result"] == "Not Enough Evidence"
assert small_sample["adoption_decision"] == "RETEST"

regression = engine.evaluate(
    experiment_id="sv-003",
    experiment_date="2026-06-30T12:10:00",
    feature_tested="Regressing Model",
    baseline=candidate,
    candidate=baseline,
    sample_size=60,
    regimes=regimes,
    generalization=generalization,
)
assert regression["scientific_result"] == "Regression"
assert regression["adoption_decision"] == "REJECT"

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    setup_database()
    save_scientific_validation_report(report)

    saved = get_scientific_validation_reports(limit=10)
    assert len(saved) == 1
    assert saved[0]["experiment_id"] == "sv-001"
    assert saved[0]["feature_tested"] == "Candidate Forecast Evidence Source"
    assert saved[0]["sample_size"] == 60
    assert saved[0]["adoption_decision"] == "ADOPT"

    research_dashboard = get_research_dashboard_data()
    assert research_dashboard["scientific_validations"][0]["experiment_id"] == "sv-001"

    research_report = ResearchEngine().research_dashboard_data()
    assert (
        research_report["scientific_validation_report"]["decision_distribution"]["ADOPT"]
        == 1
    )

    source_data = get_discovery_source_data()
    assert source_data["scientific_validations"][0]["adoption_decision"] == "ADOPT"

    observatory = PerformanceObservatory().generate(
        source_data=source_data,
        discovery_data={
            "recent_discoveries": [],
            "top_discoveries": [],
            "discovery_history": [],
        },
    )
    assert observatory["scientific_validation_summary"]["validation_count"] == 1
    assert observatory["scientific_validation_summary"]["adoptable_feature_count"] == 1

    discoveries = DiscoveryEngine().analyze(
        source_data=source_data,
        discovery_date="2026-06-30T12:15:00",
    )
    assert any(
        item["title"] == "Scientifically validated adoption candidates"
        for item in discoveries
    )

    graph = KnowledgeGraphEngine().build(
        source_data=source_data,
        discovery_data={
            "recent_discoveries": [],
            "top_discoveries": [],
            "discovery_history": [],
        },
        historical_runs=[],
    )
    assert any(node["type"] == "Scientific Validation" for node in graph["nodes"])

    api_result = scientific_validation_dashboard()
    assert api_result["scientific_validations"][0]["experiment_id"] == "sv-001"
    assert api_result["policy"]["changes_recommendation_behavior"] is False
finally:
    connection.DATABASE_PATH = original_database_path
    if os.path.exists(database_path):
        os.remove(database_path)

print("ScientificValidationEngine test passed.")
