from engines.discovery_engine import DiscoveryEngine
from engines.historical_runner import HistoricalRunner
from engines.market_regime_engine import MarketRegimeEngine
from engines.performance_observatory import PerformanceObservatory


engine = MarketRegimeEngine()

regime_rows = {
    "Strong Bull": {
        "trend": "Bullish",
        "volatility": 2,
        "month_return": 12,
        "price_vs_20ma": 6,
        "price_vs_50ma": 8,
    },
    "Bull": {
        "trend": "Bullish",
        "volatility": 2,
        "month_return": 4,
        "price_vs_20ma": 2,
        "price_vs_50ma": 1,
    },
    "Sideways": {
        "trend": "Neutral",
        "volatility": 1,
        "month_return": 0.5,
        "price_vs_20ma": 0,
        "price_vs_50ma": 0,
    },
    "Volatile": {
        "trend": "Bullish",
        "volatility": 7,
        "month_return": 1,
        "price_vs_20ma": 1,
        "price_vs_50ma": 1,
    },
    "Bear": {
        "trend": "Bearish",
        "volatility": 3,
        "month_return": -4,
        "price_vs_20ma": -3,
        "price_vs_50ma": -4,
    },
    "Strong Bear": {
        "trend": "Bearish",
        "volatility": 4,
        "month_return": -12,
        "price_vs_20ma": -8,
        "price_vs_50ma": -13,
    },
}

for expected_regime, row in regime_rows.items():
    assert engine.classify_row(row)["regime"] == expected_regime

period = engine.classify_period([
    {"date": "2024-01-01", "ticker": "AAPL", "close": 100, "volatility": 1},
    {"date": "2024-01-02", "ticker": "AAPL", "close": 112, "volatility": 2},
])

assert period["regime"] == "Strong Bull"

historical_data = [
    {
        "date": "2024-01-01",
        "validation_date": "2024-02-01",
        "ticker": "AAPL",
        "price": 100,
        "future_price": 110,
        "month_return": 4,
        "week_return": 2,
        "moving_average_20": 98,
        "moving_average_50": 97,
        "price_vs_20ma": 2,
        "price_vs_50ma": 3,
        "rsi": 55,
        "macd": 1,
        "macd_signal": 0.5,
        "macd_trend": "Bullish",
        "volatility": 2,
        "trend": "Bullish",
        "score": 5,
    },
    {
        "date": "2024-01-02",
        "validation_date": "2024-02-02",
        "ticker": "MSFT",
        "price": 100,
        "future_price": 99,
        "month_return": 0,
        "week_return": 0,
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
]
runner_report = HistoricalRunner().run(
    config={
        "tickers": ["AAPL", "MSFT"],
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "validation_window": 30,
    },
    historical_data=historical_data,
    run_date="2026-06-30T10:00:00",
)
runner_regimes = {
    item["ticker"]: item["market_regime"]
    for item in runner_report["recommendations"]
}

assert runner_regimes == {"AAPL": "Bull", "MSFT": "Sideways"}
assert "performance_by_regime" in runner_report["observatory"]

recommendations = [
    {
        "ticker": "BULL1",
        "action": "BUY",
        "market_regime": "Bull",
        "committee_agreement": 70,
        "knowledge_score": 65,
        "stability_score": 72,
        "evidence_breakdown": [
            {"category": "Forecast", "score": 92, "confidence": 92},
            {"category": "News", "score": 55, "confidence": 55},
        ],
        "validation_result": {
            "success": True,
            "hit": True,
            "percentage_return": 8,
        },
    },
    {
        "ticker": "BULL2",
        "action": "BUY",
        "market_regime": "Bull",
        "committee_agreement": 74,
        "knowledge_score": 68,
        "stability_score": 70,
        "evidence_breakdown": [
            {"category": "Forecast", "score": 88, "confidence": 88},
        ],
        "validation_result": {
            "success": True,
            "hit": True,
            "percentage_return": 6,
        },
    },
    {
        "ticker": "VOL1",
        "action": "HOLD",
        "market_regime": "Volatile",
        "committee_agreement": 62,
        "knowledge_score": 55,
        "stability_score": 45,
        "evidence_breakdown": [
            {"category": "News", "score": 94, "confidence": 94},
            {"category": "Forecast", "score": 55, "confidence": 55},
        ],
        "validation_result": {
            "success": True,
            "hit": True,
            "percentage_return": 10,
        },
    },
    {
        "ticker": "SIDE1",
        "action": "HOLD",
        "market_regime": "Sideways",
        "committee_agreement": 96,
        "knowledge_score": 75,
        "stability_score": 84,
        "evidence_breakdown": [
            {"category": "News", "score": 61, "confidence": 61},
            {"category": "Forecast", "score": 61, "confidence": 61},
        ],
        "validation_result": {
            "success": False,
            "hit": False,
            "percentage_return": -1,
        },
    },
]

observatory = PerformanceObservatory()
regime_report = observatory.performance_by_regime(recommendations)
by_regime = {item["regime"]: item for item in regime_report}

assert by_regime["Bull"]["sample_size"] == 2
assert by_regime["Bull"]["win_rate"] == 100
assert by_regime["Bull"]["average_return"] == 7
assert by_regime["Bull"]["recommendation_distribution"] == {"BUY": 2}
assert by_regime["Bull"]["average_committee_agreement"] == 72
assert by_regime["Bull"]["average_knowledge_score"] == 66.5
assert by_regime["Bull"]["average_stability_score"] == 71
assert by_regime["Volatile"]["evidence_rankings"][0]["category"] == "News"

observatory_report = observatory.generate(
    source_data={
        "recommendations": recommendations,
        "benchmark_results": [],
        "provider_results": [],
        "research_experiments": [],
    },
    discovery_data={
        "recent_discoveries": [],
        "top_discoveries": [],
        "discovery_history": [],
    },
)

assert "performance_by_regime" in observatory_report
assert len(observatory_report["performance_by_regime"]) == 6

discoveries = DiscoveryEngine().analyze(
    source_data={
        "recommendations": recommendations,
        "benchmark_results": [],
        "provider_results": [],
        "research_experiments": [],
    },
    discovery_date="2026-06-30T10:05:00",
)
descriptions = [item["description"] for item in discoveries]

assert "Forecast performs best during Bull markets." in descriptions
assert "News contributes most during Volatile regimes." in descriptions
assert "Committee agreement is strongest during Sideways markets." in descriptions

print("MarketRegimeEngine test passed.")
