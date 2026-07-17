from engines.performance_observatory import PerformanceObservatory


source_data = {
    "recommendations": [
        {
            "ticker": "AAPL",
            "action": "BUY",
            "confidence": 80,
            "committee_agreement": 82,
            "main_disagreement": "",
            "evidence_breakdown": [
                {
                    "category": "Technical",
                    "score": 85,
                    "confidence": 88,
                },
                {
                    "category": "Forecast",
                    "score": 74,
                    "confidence": 72,
                },
            ],
            "validation_result": {
                "success": True,
                "hit": True,
                "percentage_return": 10,
            },
        },
        {
            "ticker": "MSFT",
            "action": "HOLD",
            "confidence": 60,
            "committee_agreement": 55,
            "main_disagreement": "Forecast disagrees with Risk.",
            "evidence_breakdown": [
                {
                    "category": "Technical",
                    "score": 48,
                    "confidence": 52,
                },
                {
                    "category": "Risk",
                    "score": 42,
                    "confidence": 45,
                },
            ],
            "validation_result": {
                "success": False,
                "hit": False,
                "percentage_return": -5,
            },
        },
        {
            "ticker": "NVDA",
            "action": "BUY",
            "confidence": 70,
            "committee_agreement": 78,
            "main_disagreement": "",
            "evidence_breakdown": [
                {
                    "category": "Forecast",
                    "score": 80,
                    "confidence": 76,
                },
                {
                    "category": "News",
                    "score": 68,
                    "confidence": 65,
                },
            ],
            "validation_result": {
                "success": True,
                "hit": True,
                "percentage_return": 2,
            },
        },
        {
            "ticker": "TSLA",
            "action": "AVOID",
            "confidence": 45,
            "committee_agreement": 35,
            "main_disagreement": "News disagrees with Risk.",
            "evidence_breakdown": [
                {
                    "category": "Fundamental",
                    "score": 38,
                    "confidence": 40,
                },
                {
                    "category": "Portfolio",
                    "score": 58,
                    "confidence": 54,
                },
            ],
            "validation_result": None,
        },
    ],
    "benchmark_results": [
        {
            "engine_name": "BenchmarkEngine",
            "metric": "overall_hit_rate",
            "value": 66.67,
        },
        {
            "engine_name": "ForecastEngine",
            "metric": "direction_accuracy",
            "value": 75,
        },
    ],
    "provider_results": [
        {
            "provider_type": "forecast",
            "provider_name": "Mock",
            "score": 70,
            "rank": 1,
            "status": "Available",
        },
        {
            "provider_type": "news",
            "provider_name": "RSS",
            "score": 62,
            "rank": 1,
            "status": "Available",
        },
        {
            "provider_type": "fundamental",
            "provider_name": "MockFundamentals",
            "score": 48,
            "rank": 2,
            "status": "Available",
        },
    ],
    "research_experiments": [
        {
            "experiment_id": "arl-fixture",
            "title": "Fixture Experiment",
            "status": "Planned",
        },
    ],
}
discovery_data = {
    "recent_discoveries": [
        {"id": "disc-1", "title": "Validation success"},
    ],
    "top_discoveries": [
        {"id": "disc-2", "title": "Provider performance leader"},
    ],
    "discovery_history": [
        {"id": "disc-1"},
        {"id": "disc-2"},
    ],
}

original_actions = [
    recommendation["action"]
    for recommendation in source_data["recommendations"]
]

observatory = PerformanceObservatory()
report = observatory.generate(
    source_data=source_data,
    discovery_data=discovery_data,
)
metrics = report["platform_metrics"]

assert [
    recommendation["action"]
    for recommendation in source_data["recommendations"]
] == original_actions
assert metrics["lifetime_recommendations"] == 4
assert metrics["validated_recommendations"] == 3
assert metrics["current_win_rate"] == 66.67
assert metrics["rolling_win_rate"] == 66.67
assert metrics["average_return"] == 2.33
assert metrics["median_return"] == 2
assert metrics["largest_gain"] == 10
assert metrics["largest_loss"] == -5
assert metrics["sharpe_placeholder"] == 0
assert metrics["drawdown_placeholder"] == 0
assert metrics["confidence_calibration"] == 63.33
assert metrics["recommendation_distribution"] == {
    "BUY": 2,
    "HOLD": 1,
    "AVOID": 1,
}
assert metrics["committee_agreement_distribution"] == {
    "low": 1,
    "medium": 1,
    "high": 2,
}

technical = next(
    item for item in report["engine_report_cards"]
    if item["engine"] == "Technical"
)
forecast = next(
    item for item in report["engine_report_cards"]
    if item["engine"] == "Forecast"
)
committee = next(
    item for item in report["engine_report_cards"]
    if item["engine"] == "Committee"
)

assert technical["accuracy"] == 50
assert technical["sample_size"] == 2
assert forecast["accuracy"] == 100
assert forecast["confidence"] == 74
assert committee["confidence"] == 62.5

forecast_provider = next(
    item for item in report["provider_report_cards"]
    if item["provider_type"] == "forecast"
)
data_provider = next(
    item for item in report["provider_report_cards"]
    if item["provider_type"] == "data"
)

assert forecast_provider["provider_name"] == "Mock"
assert forecast_provider["rank"] == 1
assert data_provider["status"] == "No history"

assert report["benchmark_history"]["benchmark_count"] == 2
assert report["benchmark_history"]["metric_averages"] == {
    "direction_accuracy": 75,
    "overall_hit_rate": 66.67,
}
assert report["committee_history"]["disagreement_count"] == 2
assert report["discovery_history"]["discovery_count"] == 2
assert report["experiment_summary"]["experiment_count"] == 1
assert report["controlled_learning"]["automatic_behavior_changes"] is False
assert report["controlled_learning"]["requires_human_approval"] is True

print("PerformanceObservatory test passed.")
