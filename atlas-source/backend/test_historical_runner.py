import os
import tempfile
import builtins

import pandas as pd
import database.connection as connection
from database.repository import get_historical_validation_runs
from database.setup import setup_database
from engines.historical_runner import HistoricalRunner
from market.mock_historical_data_adapter import MockHistoricalDataAdapter
from market.yahoo_historical_data_adapter import YahooHistoricalDataAdapter


historical_data = [
    {
        "date": "2024-01-02",
        "validation_date": "2024-02-01",
        "ticker": "AAPL",
        "price": 100,
        "future_price": 110,
        "week_return": 2,
        "month_return": 5,
        "moving_average_20": 95,
        "moving_average_50": 92,
        "price_vs_20ma": 5,
        "price_vs_50ma": 8,
        "rsi": 55,
        "macd": 1.2,
        "macd_signal": 1,
        "macd_trend": "Bullish",
        "volatility": 1,
        "trend": "Bullish",
        "score": 5,
    },
    {
        "date": "2024-01-03",
        "validation_date": "2024-02-02",
        "ticker": "MSFT",
        "price": 100,
        "future_price": 90,
        "week_return": -2,
        "month_return": -6,
        "moving_average_20": 105,
        "moving_average_50": 110,
        "price_vs_20ma": -5,
        "price_vs_50ma": -10,
        "rsi": 72,
        "macd": -1,
        "macd_signal": 0,
        "macd_trend": "Bearish",
        "volatility": 3,
        "trend": "Bearish",
        "score": 1,
    },
    {
        "date": "2024-01-04",
        "validation_date": "2024-02-03",
        "ticker": "NVDA",
        "price": 100,
        "future_price": 100.5,
        "week_return": 0,
        "month_return": 0,
        "moving_average_20": 100,
        "moving_average_50": 100,
        "price_vs_20ma": 0,
        "price_vs_50ma": 0,
        "rsi": 50,
        "macd": 0,
        "macd_signal": 0,
        "macd_trend": "Neutral",
        "volatility": 1,
        "trend": "Neutral",
        "score": 2,
    },
    {
        "date": "2024-01-05",
        "validation_date": "2024-02-04",
        "ticker": "TSLA",
        "price": 100,
        "future_price": 95,
        "week_return": 2,
        "month_return": 5,
        "moving_average_20": 95,
        "moving_average_50": 92,
        "price_vs_20ma": 5,
        "price_vs_50ma": 8,
        "rsi": 55,
        "macd": 1.2,
        "macd_signal": 1,
        "macd_trend": "Bullish",
        "volatility": 1,
        "trend": "Bullish",
        "score": 5,
    },
]
config = {
    "tickers": ["AAPL", "MSFT", "NVDA", "TSLA"],
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "forecast_provider": "mock",
    "news_provider": "fake",
    "fundamental_provider": "mock",
    "committee_enabled": True,
    "executive_review_enabled": True,
    "validation_window": 30,
    "portfolio_configuration": {"cash": 100000},
}


runner = HistoricalRunner()
experiment = runner.create_experiment(config)
same_experiment = runner.create_experiment(dict(config))

assert experiment["experiment_id"] == same_experiment["experiment_id"]
assert experiment["experiment_id"].startswith("hist-")

report = runner.run(
    config=config,
    historical_data=historical_data,
    run_date="2026-06-29T12:00:00",
)
metrics = report["metrics"]
statistics = report["statistics"]

assert len(report["recommendations"]) == 4
assert len(report["validations"]) == 4
assert metrics["win_rate"] == 75
assert metrics["loss_rate"] == 25
assert metrics["average_return"] == -1.125
assert metrics["median_return"] == -2.25
assert metrics["average_holding_period"] == 30
assert metrics["sharpe_ratio"] != 0
assert metrics["sortino_ratio"] != 0
assert metrics["maximum_drawdown"] < 0
assert metrics["volatility"] > 0
assert metrics["information_ratio"] is None
assert metrics["profit_factor"] > 0
assert metrics["expectancy"] == metrics["average_return"]
assert metrics["risk_reward_ratio"] > 0
assert metrics["recommendation_accuracy"] == 75
assert "committee_accuracy" in metrics
assert "executive_accuracy" in metrics
assert "hypothesis_accuracy" in metrics
assert "discovery_accuracy" in metrics

assert statistics["sample_size"] == 4
assert statistics["mean_return"] == -1.125
assert statistics["variance"] > 0
assert statistics["standard_deviation"] > 0
assert statistics["standard_error"] > 0
assert statistics["confidence_interval_95"][0] < statistics["confidence_interval_95"][1]
assert statistics["win_rate"] == 75
assert statistics["win_rate_confidence_interval_95"][0] < statistics["win_rate_confidence_interval_95"][1]
assert statistics["comparison_delta"] == 0
assert statistics["practical_significance_label"] == "Insufficient Sample"
assert statistics["insufficient_sample_size"] is True

assert len(report["comparisons"]) == 6
assert report["comparisons"][0]["variant"] == "Full Atlas"
assert all("win_rate" in row for row in report["comparisons"])
assert all("comparison_delta" in row for row in report["comparisons"])
assert all("win_rate_delta" in row for row in report["comparisons"])
assert all("practical_significance_label" in row for row in report["comparisons"])
assert all(row["statistics"]["sample_size"] == 4 for row in report["comparisons"])
assert report["comparisons"][1]["variant"] == "No Forecast"
assert report["comparisons"][1]["disabled_subsystems"] == ["forecast"]
assert report["comparisons"][1]["practical_significance_label"] == "Insufficient Sample"
assert report["comparisons"][2]["variant"] == "No News"
assert report["comparisons"][2]["disabled_subsystems"] == ["news"]
assert report["comparisons"][3]["variant"] == "No Fundamentals"
assert report["comparisons"][3]["disabled_subsystems"] == ["fundamentals"]
assert report["comparisons"][4]["variant"] == "No Committee"
assert report["comparisons"][4]["disabled_subsystems"] == ["committee"]
assert report["comparisons"][5]["variant"] == "No Executive Review"
assert report["comparisons"][5]["disabled_subsystems"] == ["executive_review"]
assert len(report["attribution"]) == 10
assert "## Executive Summary" in report["markdown_report"]
assert "## Performance" in report["markdown_report"]
assert "## Risk" in report["markdown_report"]
assert "## Future Improvements" in report["markdown_report"]
assert report["benchmark_rows"]
assert report["observatory"]["platform_metrics"]["lifetime_recommendations"] == 4
assert report["discoveries"]

large_validations = [
    {
        "percentage_return": 2,
        "success": True,
        "status": "Succeeded",
    }
    for _ in range(40)
]
large_stats = runner.statistical_analysis(large_validations)
small_delta_stats = runner.statistical_analysis(
    large_validations,
    comparison_delta=0.5,
)
possible_stats = runner.statistical_analysis(
    large_validations,
    comparison_delta=1.5,
)
meaningful_stats = runner.statistical_analysis(
    large_validations,
    comparison_delta=3.5,
)

assert large_stats["sample_size"] == 40
assert large_stats["standard_deviation"] == 0
assert large_stats["standard_error"] == 0
assert large_stats["confidence_interval_95"] == [2.0, 2.0]
assert large_stats["win_rate_confidence_interval_95"] == [100, 100]
assert small_delta_stats["practical_significance_label"] == "Not Meaningful"
assert possible_stats["practical_significance_label"] == "Possibly Meaningful"
assert meaningful_stats["practical_significance_label"] == "Meaningful"

adapter = MockHistoricalDataAdapter()
adapter_rows = adapter.get_ohlcv(
    ["AAPL"],
    "2024-01-01",
    "2024-02-15",
)
repeat_adapter_rows = adapter.get_ohlcv(
    ["AAPL"],
    "2024-01-01",
    "2024-02-15",
)

assert adapter_rows == repeat_adapter_rows
assert adapter_rows[0]["date"] == "2024-01-01"
assert {"open", "high", "low", "close", "volume"} <= set(adapter_rows[0])

adapter_report = HistoricalRunner(
    historical_data_adapter=adapter,
).run(
    config={
        "tickers": ["AAPL"],
        "start_date": "2024-01-01",
        "end_date": "2024-02-15",
        "historical_data_provider": "mock",
        "validation_window": 5,
    },
    run_date="2026-06-29T12:00:00",
)

assert len(adapter_report["recommendations"]) == len(adapter_rows) - 5
assert adapter_report["validations"][0]["starting_price"] == adapter_rows[0]["close"]
assert adapter_report["validations"][0]["ending_price"] == adapter_rows[5]["close"]


class RunnerYahooTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    def history(self, start, end, auto_adjust=False):
        return pd.DataFrame(
            {
                "Open": [100 + index for index in range(12)],
                "High": [101 + index for index in range(12)],
                "Low": [99 + index for index in range(12)],
                "Close": [100.5 + index for index in range(12)],
                "Volume": [1000000 + index for index in range(12)],
            },
            index=pd.date_range("2024-01-01", periods=12, freq="D"),
        )


class RunnerYahooModule:
    Ticker = RunnerYahooTicker


runner_original_import = builtins.__import__


def runner_yfinance(name, *args, **kwargs):
    if name == "yfinance":
        return RunnerYahooModule()

    return runner_original_import(name, *args, **kwargs)


builtins.__import__ = runner_yfinance
yahoo_adapter = YahooHistoricalDataAdapter()

try:
    yahoo_adapter_report = HistoricalRunner(
        historical_data_adapter=yahoo_adapter,
    ).run(
        config={
            "tickers": ["AAPL"],
            "start_date": "2024-01-01",
            "end_date": "2024-01-12",
            "historical_data_provider": "yahoo",
            "validation_window": 5,
        },
        run_date="2026-06-29T12:00:00",
    )
finally:
    builtins.__import__ = runner_original_import

assert yahoo_adapter.fallback_used is False
assert yahoo_adapter.last_error == ""
assert len(yahoo_adapter_report["recommendations"]) == 7
assert yahoo_adapter_report["validations"][0]["starting_price"] == 100.5
assert yahoo_adapter_report["validations"][0]["ending_price"] == 105.5

toggle_report = runner.run(
    config={
        "tickers": ["AAPL", "MSFT", "NVDA", "TSLA"],
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "validation_window": 30,
        "use_forecast": False,
        "use_news": False,
        "use_committee": False,
        "use_executive_review": False,
    },
    historical_data=historical_data,
    run_date="2026-06-29T12:00:00",
)
toggle_recommendation = toggle_report["recommendations"][0]
disabled_evidence = [
    item for item in toggle_recommendation["evidence_breakdown"]
    if item.get("disabled")
]

assert toggle_report["experiment"]["configuration"]["use_forecast"] is False
assert toggle_report["experiment"]["configuration"]["use_news"] is False
assert "forecast" in toggle_recommendation["disabled_subsystems"]
assert "news" in toggle_recommendation["disabled_subsystems"]
assert "committee" in toggle_recommendation["disabled_subsystems"]
assert "executive_review" in toggle_recommendation["disabled_subsystems"]
assert {item["category"] for item in disabled_evidence} >= {
    "Forecast",
    "News",
    "Committee",
    "Executive",
}
assert all(item["score"] == 0 for item in disabled_evidence)

try:
    HistoricalRunner(historical_data_adapter=adapter).run(
        config={
            "tickers": ["AAPL"],
            "start_date": "2024-02-01",
            "end_date": "2024-01-01",
            "validation_window": 5,
        },
        run_date="2026-06-29T12:00:00",
    )
    raise AssertionError("Invalid historical range should fail.")
except ValueError as error:
    assert "Start date" in str(error) or "start_date" in str(error)

try:
    HistoricalRunner(historical_data_adapter=adapter).run(
        config={
            "tickers": ["INVALID"],
            "start_date": "2024-01-01",
            "end_date": "2024-02-01",
            "validation_window": 5,
        },
        run_date="2026-06-29T12:00:00",
    )
    raise AssertionError("Missing historical ticker should fail.")
except ValueError as error:
    assert "ticker" in str(error).lower()

try:
    HistoricalRunner(historical_data_adapter=adapter).run(
        config={
            "tickers": ["AAPL"],
            "start_date": "2024-01-01",
            "end_date": "2024-01-03",
            "validation_window": 5,
        },
        run_date="2026-06-29T12:00:00",
    )
    raise AssertionError("Insufficient historical rows should fail.")
except ValueError as error:
    assert "Insufficient historical rows" in str(error)

try:
    HistoricalRunner().run(
        config=config,
        historical_data=[historical_data[1], historical_data[0]],
        run_date="2026-06-29T12:00:00",
    )
    raise AssertionError("Unsorted historical rows should fail.")
except ValueError as error:
    assert "sorted" in str(error)

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    setup_database()
    runner.run(
        config=config,
        historical_data=historical_data,
        persist=True,
        run_date="2026-06-29T12:00:00",
    )
    saved = get_historical_validation_runs(limit=1)

    assert len(saved) == 1
    assert saved[0]["experiment_id"] == experiment["experiment_id"]
    assert saved[0]["metrics"]["win_rate"] == 75
    assert saved[0]["comparison"][0]["variant"] == "Full Atlas"
    assert saved[0]["statistics"]["sample_size"] == 4
    assert "Atlas Historical Validation Report" in saved[0]["report"]
finally:
    connection.DATABASE_PATH = original_database_path
    if os.path.exists(database_path):
        os.remove(database_path)

print("HistoricalRunner test passed.")
