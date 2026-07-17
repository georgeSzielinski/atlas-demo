import os
import tempfile

import database.connection as connection
from database.repository import get_research_dashboard_data
from database.setup import setup_database
from engines.recommendation_engine import RecommendationEngine
from engines.research_engine import ResearchEngine
from models.investment_recommendation import InvestmentRecommendation
from models.stock_analysis import StockAnalysis


def run_tests():
    original_database_path = connection.DATABASE_PATH

    with tempfile.NamedTemporaryFile(delete=False) as database_file:
        test_database_path = database_file.name

    try:
        connection.DATABASE_PATH = test_database_path
        setup_database()

        engine = ResearchEngine()
        experiment_date = "2026-06-29T09:30:00"
        experiment = engine.create_experiment(
            title="Deterministic ARL Test",
            description="Compare research strategies and providers.",
            dataset="unit-test-history",
            ticker_list=["MSFT", "AAPL"],
            provider_configuration={"data": "mock"},
            forecast_provider="mock",
            news_provider="fake",
            fundamental_provider="mock",
            validation_window=30,
            benchmark_snapshot={"overall_hit_rate": 62.5},
            status="Completed",
            notes="Unit test fixture.",
            experiment_date=experiment_date,
            toggles={
                "use_forecast": False,
                "use_news": False,
            },
        )

        expected_id = engine.generate_experiment_id(
            "Deterministic ARL Test",
            experiment_date,
            "unit-test-history",
            ["MSFT", "AAPL"],
        )
        assert experiment["experiment_id"] == expected_id
        assert experiment["ticker_list"] == ["MSFT", "AAPL"]
        assert experiment["toggles"]["use_forecast"] is False
        assert experiment["toggles"]["use_news"] is False
        assert experiment["toggles"]["use_technical"] is True
        assert experiment["disabled_subsystems"] == ["forecast", "news"]

        strategies = [
            {
                "strategy_name": "Technical only",
                "components": ["Technical"],
                "validation_results": [
                    {"success": True, "percentage_return": 5.0, "confidence": 70},
                    {"success": False, "percentage_return": -2.0, "confidence": 60},
                ],
                "runtime": 1.2,
                "missing_data": [],
            },
            {
                "strategy_name": "Everything",
                "components": ["Technical", "Forecast", "Fundamental", "News"],
                "validation_results": [
                    {"hit": True, "percentage_return": 8.0, "confidence": 80},
                ],
                "runtime": 2.5,
                "missing_data": ["risk"],
            },
        ]

        strategy_results = engine.compare_strategies(strategies)
        technical_result = strategy_results[0]
        assert technical_result["recommendation_count"] == 2
        assert technical_result["hit_rate"] == 50.0
        assert technical_result["average_return"] == 1.5
        assert technical_result["average_gain"] == 5.0
        assert technical_result["average_loss"] == -2.0
        assert technical_result["confidence"] == 65.0

        provider_results = engine.compare_providers({
            "forecast": [
                {"provider_name": "Mock", "score": 70, "notes": "Baseline"},
                {"provider_name": "Kronos", "score": 82, "notes": "Candidate"},
            ],
            "news": [
                {"provider_name": "Fake", "score": 60},
                {"provider_name": "RSS", "score": 55, "status": "Unavailable"},
            ],
        })
        assert provider_results[0]["provider_name"] == "Kronos"
        assert provider_results[0]["rank"] == 1
        assert provider_results[2]["provider_type"] == "news"

        recommendation = InvestmentRecommendation(
            ticker="AAPL",
            action="BUY",
            confidence=76,
            evidence_breakdown=[
                {
                    "category": "Technical",
                    "score": 90,
                    "weight": 0.3,
                    "confidence": 85,
                },
                {
                    "category": "News",
                    "score": 35,
                    "weight": 0.2,
                    "confidence": 40,
                },
            ],
        )

        attribution = engine.attribute_recommendation(recommendation)
        assert attribution["strongest_engine"] == "Technical"
        assert attribution["confidence_drag_engine"] == "News"
        assert attribution["changed_evidence"] == ["Technical", "News"]

        stock = StockAnalysis(
            ticker="AAPL",
            asset_type="Stock",
            price=280,
            week_return=2,
            month_return=5,
            moving_average_20=275,
            moving_average_50=270,
            price_vs_20ma=2,
            price_vs_50ma=4,
            rsi=55,
            macd=1.2,
            macd_signal=1.0,
            macd_trend="Bullish",
            volatility=1.3,
            trend="Bullish",
            score=5,
        )
        default_recommendation = RecommendationEngine().build_recommendations([
            stock
        ])[0]
        toggled_recommendation = RecommendationEngine().build_recommendations(
            [stock],
            experiment_toggles={"use_forecast": False},
        )[0]

        assert not hasattr(default_recommendation, "disabled_subsystems")
        assert toggled_recommendation.action == default_recommendation.action
        assert toggled_recommendation.disabled_subsystems == ["Forecast"]
        assert any(
            item.get("disabled") and item["category"] == "Forecast"
            for item in toggled_recommendation.evidence_breakdown
        )

        report = engine.run_experiment(
            experiment=experiment,
            strategies=strategies,
            providers={
                "forecast": [
                    {"provider_name": "Mock", "score": 70},
                    {"provider_name": "Kronos", "score": 82},
                ],
            },
            recommendations=[recommendation],
        )
        markdown = engine.generate_markdown_report(report)
        assert "## Executive Summary" in markdown
        assert "## Experiment Configuration" in markdown
        assert "## Provider Comparison" in markdown
        assert "- Disabled Subsystems: forecast, news" in markdown
        assert "## Next Experiments" in markdown

        engine.persist_report(report)
        dashboard = get_research_dashboard_data()
        assert dashboard["research_experiments"][0]["experiment_id"] == expected_id
        assert dashboard["provider_rankings"][0]["provider_name"] == "Kronos"
        assert dashboard["engine_rankings"][0]["strategy_name"] == "Everything"

        print("ResearchEngine tests passed.")
    finally:
        connection.DATABASE_PATH = original_database_path
        if os.path.exists(test_database_path):
            os.remove(test_database_path)


if __name__ == "__main__":
    run_tests()
