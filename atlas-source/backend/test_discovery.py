import os
import tempfile

import database.connection as connection
from database.repository import (
    get_discovery_dashboard_data,
    get_research_dashboard_data,
    save_discoveries,
)
from database.setup import setup_database
from engines.discovery_engine import DiscoveryEngine
from engines.research_engine import ResearchEngine


def fixture_source_data():
    return {
        "recommendations": [
            {
                "ticker": "AAPL",
                "confidence": 82,
                "committee_agreement": 80,
                "main_disagreement": "",
                "evidence_breakdown": [
                    {"category": "Technical", "score": 85},
                    {"category": "Forecast", "score": 78},
                ],
                "validation_result": {"success": True, "hit": True},
            },
            {
                "ticker": "MSFT",
                "confidence": 78,
                "committee_agreement": 76,
                "main_disagreement": "",
                "evidence_breakdown": [
                    {"category": "Technical", "score": 82},
                    {"category": "Forecast", "score": 74},
                ],
                "validation_result": {"success": True, "hit": True},
            },
            {
                "ticker": "TSLA",
                "confidence": 55,
                "committee_agreement": 42,
                "main_disagreement": "Forecast disagrees with Risk.",
                "evidence_breakdown": [
                    {"category": "News", "score": 72},
                    {"category": "Risk", "score": 38},
                ],
                "validation_result": {"success": False, "hit": False},
            },
            {
                "ticker": "NVDA",
                "confidence": 52,
                "committee_agreement": 45,
                "main_disagreement": "News disagrees with Risk.",
                "evidence_breakdown": [
                    {"category": "News", "score": 75},
                    {"category": "Risk", "score": 42},
                ],
                "validation_result": {"success": False, "hit": False},
            },
        ],
        "benchmark_results": [
            {
                "engine_name": "ForecastEngine",
                "metric": "forecast_direction_accuracy",
                "value": 45,
            },
            {
                "engine_name": "BenchmarkEngine",
                "metric": "overall_hit_rate",
                "value": 62,
            },
        ],
        "provider_results": [
            {
                "provider_type": "forecast",
                "provider_name": "Mock",
                "score": 55,
                "rank": 2,
                "status": "Available",
            },
            {
                "provider_type": "news",
                "provider_name": "RSS",
                "score": 68,
                "rank": 1,
                "status": "Available",
            },
        ],
        "research_experiments": [],
    }


def run_tests():
    original_database_path = connection.DATABASE_PATH

    with tempfile.NamedTemporaryFile(delete=False) as database_file:
        test_database_path = database_file.name

    try:
        connection.DATABASE_PATH = test_database_path
        setup_database()

        engine = DiscoveryEngine()
        discoveries = engine.analyze(
            source_data=fixture_source_data(),
            discovery_date="2026-06-29T10:00:00",
        )

        titles = [discovery["title"] for discovery in discoveries]
        assert "Highest-performing evidence combination" in titles
        assert "Weakest evidence combination" in titles
        assert "Best committee agreement range" in titles
        assert "Worst committee disagreements" in titles
        assert "Provider performance leader" in titles
        assert "Forecast model performance" in titles
        assert "Confidence calibration" in titles
        assert "Validation success" in titles
        assert "Benchmark trend" in titles
        assert "Sector trend coverage" in titles

        validation_discovery = next(
            item for item in discoveries
            if item["title"] == "Validation success"
        )
        assert validation_discovery["sample_size"] == 4
        assert validation_discovery["support_level"] == "Tiny sample"
        assert validation_discovery["confidence"] > 0
        assert validation_discovery["automatic_behavior_change"] is False
        assert validation_discovery["warnings"]
        assert "do not auto-change" in validation_discovery["suggestions"][0]

        forecast_discovery = next(
            item for item in discoveries
            if item["title"] == "Forecast model performance"
        )
        assert forecast_discovery["suggestions"] == [
            "Forecast contributes little under current configuration."
        ]

        save_discoveries(discoveries)
        dashboard = get_discovery_dashboard_data()
        assert dashboard["recent_discoveries"]
        assert dashboard["top_discoveries"]
        assert dashboard["highest_confidence_discoveries"]
        assert dashboard["discovery_history"]

        research_engine = ResearchEngine()
        experiment = research_engine.create_experiment(
            title="Discovery Referenced Experiment",
            description="Experiment references a discovery.",
            dataset="discovery-fixture",
            ticker_list=["AAPL"],
            related_discoveries=[validation_discovery["id"]],
            experiment_date="2026-06-29T10:05:00",
        )
        research_engine.persist_report({
            "experiment": experiment,
            "strategy_results": [],
            "provider_results": [],
            "attributions": [],
        })
        research_dashboard = get_research_dashboard_data()
        assert research_dashboard["discoveries"]

        print("DiscoveryEngine tests passed.")
    finally:
        connection.DATABASE_PATH = original_database_path
        if os.path.exists(test_database_path):
            os.remove(test_database_path)


if __name__ == "__main__":
    run_tests()
