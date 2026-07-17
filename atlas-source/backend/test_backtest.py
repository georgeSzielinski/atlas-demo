from engines.backtest_engine import BacktestEngine


engine = BacktestEngine()

buy_result = engine.evaluate_recommendation(
    recommendation={"ticker": "AAPL", "action": "BUY"},
    entry_price=100,
    exit_price=110,
    holding_period=5,
    recommendation_timestamp="2026-01-01T09:30:00",
)
avoid_result = engine.evaluate_recommendation(
    recommendation={"ticker": "MSFT", "action": "AVOID"},
    entry_price=100,
    exit_price=95,
    holding_period=5,
    recommendation_timestamp="2026-01-01T09:30:00",
)
hold_result = engine.evaluate_recommendation(
    recommendation={"ticker": "NVDA", "action": "HOLD"},
    entry_price=100,
    exit_price=100.5,
    holding_period=5,
    recommendation_timestamp="2026-01-01T09:30:00",
)

assert buy_result["predicted_direction"] == "UP"
assert buy_result["actual_direction"] == "UP"
assert buy_result["percentage_return"] == 10
assert buy_result["hit"] is True
assert buy_result["success"] is True
assert buy_result["recommendation"] == "BUY"
assert buy_result["holding_period"] == 5
assert buy_result["recommendation_timestamp"] == "2026-01-01T09:30:00"

assert avoid_result["predicted_direction"] == "DOWN"
assert avoid_result["actual_direction"] == "DOWN"
assert avoid_result["hit"] is True

assert hold_result["predicted_direction"] == "FLAT"
assert hold_result["actual_direction"] == "FLAT"

summary = engine.evaluate_batch([buy_result, avoid_result, hold_result])

assert summary["count"] == 3
assert summary["hit_rate"] == 100
assert summary["overall_hit_rate"] == 100
assert summary["buy_hit_rate"] == 100
assert summary["hold_hit_rate"] == 100
assert summary["avoid_hit_rate"] == 100
assert summary["average_return"] == 1.83
assert summary["average_gain"] == 5.25
assert summary["average_loss"] == -5
assert summary["largest_gain"] == 10
assert summary["largest_loss"] == -5
assert summary["win_loss_ratio"] == 2
assert summary["max_drawdown"] is None
assert summary["sharpe_ratio"] is None

report = engine.generate_report([buy_result, avoid_result, hold_result])

assert "Atlas Backtest Report" in report
assert "Total Recommendations: 3" in report
assert "Hit Rate: 100%" in report
assert "Average Return: 1.83%" in report
assert "Average Gain: 5.25%" in report
assert "Average Loss: -5%" in report
assert "Largest Gain: 10%" in report
assert "Largest Loss: -5%" in report
assert "Win/Loss Ratio: 2" in report
assert "Max Drawdown: Not calculated yet" in report
assert "Sharpe Ratio: Not calculated yet" in report

print(report)
print("BacktestEngine test passed.")
