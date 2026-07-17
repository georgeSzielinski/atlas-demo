from engines.validation_engine import ValidationEngine


engine = ValidationEngine()
timestamp = "2026-01-01T09:30:00"
evaluation_timestamp = "2026-01-08T09:30:00"

buy_result = engine.evaluate_completed_recommendation(
    recommendation={"id": 1, "ticker": "AAPL", "action": "BUY"},
    starting_price=100,
    ending_price=112,
    holding_period=7,
    recommendation_timestamp=timestamp,
    evaluation_timestamp=evaluation_timestamp,
    notes="Reached validation horizon.",
)
avoid_result = engine.evaluate_completed_recommendation(
    recommendation={"id": 2, "ticker": "MSFT", "action": "AVOID"},
    starting_price=100,
    ending_price=106,
    holding_period=7,
    recommendation_timestamp=timestamp,
    evaluation_timestamp=evaluation_timestamp,
)
pending_result = engine.pending_result(
    recommendation={"id": 3, "ticker": "NVDA", "action": "HOLD"},
    recommendation_timestamp=timestamp,
)
expired_result = engine.expired_result(
    recommendation={"id": 4, "ticker": "TSLA", "action": "BUY"},
    recommendation_timestamp=timestamp,
    evaluation_timestamp=evaluation_timestamp,
)

assert buy_result["recommendation_id"] == 1
assert buy_result["ticker"] == "AAPL"
assert buy_result["recommendation"] == "BUY"
assert buy_result["recommendation_timestamp"] == timestamp
assert buy_result["evaluation_timestamp"] == evaluation_timestamp
assert buy_result["entry_timestamp"] == timestamp
assert buy_result["exit_timestamp"] == evaluation_timestamp
assert buy_result["holding_period"] == 7
assert buy_result["expected_holding_period"] == 7
assert buy_result["starting_price"] == 100
assert buy_result["ending_price"] == 112
assert buy_result["percentage_return"] == 12
assert buy_result["predicted_direction"] == "UP"
assert buy_result["actual_direction"] == "UP"
assert buy_result["success"] is True
assert buy_result["status"] == "Succeeded"
assert buy_result["notes"] == "Reached validation horizon."
assert buy_result["validation_notes"] == "Reached validation horizon."
assert buy_result["validation_window"] == 7

assert avoid_result["recommendation_id"] == 2
assert avoid_result["predicted_direction"] == "DOWN"
assert avoid_result["actual_direction"] == "UP"
assert avoid_result["success"] is False
assert avoid_result["status"] == "Failed"

assert pending_result["status"] == "Pending"
assert pending_result["percentage_return"] is None
assert pending_result["notes"] == "Awaiting validation."

assert expired_result["status"] == "Expired"
assert expired_result["evaluation_timestamp"] == evaluation_timestamp
assert expired_result["notes"] == "Recommendation expired before validation."

windows = engine.multiple_window_results(
    recommendation={"id": 5, "ticker": "AAPL", "action": "BUY"},
    recommendation_timestamp=timestamp,
)

assert [item["validation_window"] for item in windows] == [7, 30, 90, 180, 365]
assert all(item["status"] == "Pending" for item in windows)

metrics = engine.performance_metrics([
    buy_result,
    avoid_result,
    pending_result,
    expired_result,
])

assert metrics["count"] == 2
assert metrics["overall_hit_rate"] == 50
assert metrics["buy_hit_rate"] == 100
assert metrics["hold_hit_rate"] == 0
assert metrics["avoid_hit_rate"] == 0
assert metrics["average_return"] == 9
assert metrics["average_gain"] == 9
assert metrics["average_loss"] == 0
assert metrics["largest_gain"] == 12
assert metrics["largest_loss"] == 0
assert metrics["win_loss_ratio"] is None
assert metrics["max_drawdown"] is None
assert metrics["sharpe_ratio"] is None

print("ValidationEngine test passed.")
