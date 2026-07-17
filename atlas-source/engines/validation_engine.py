from datetime import datetime

from engines.backtest_engine import BacktestEngine


class ValidationEngine:
    PENDING = "Pending"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    EXPIRED = "Expired"
    VALIDATION_WINDOWS = [7, 30, 90, 180, 365]

    def __init__(self):
        self.backtest_engine = BacktestEngine()

    def evaluate_completed_recommendation(
        self,
        recommendation,
        starting_price,
        ending_price,
        holding_period,
        recommendation_timestamp,
        evaluation_timestamp=None,
        notes="",
    ):
        evaluation_time = evaluation_timestamp or datetime.now().isoformat()
        result = self.backtest_engine.evaluate_recommendation(
            recommendation=recommendation,
            entry_price=starting_price,
            exit_price=ending_price,
            holding_period=holding_period,
            recommendation_timestamp=recommendation_timestamp,
        )
        success = result["success"]

        return {
            "recommendation_id": result["recommendation_id"],
            "ticker": result["ticker"],
            "recommendation": result["recommendation"],
            "recommendation_timestamp": recommendation_timestamp,
            "evaluation_timestamp": evaluation_time,
            "entry_timestamp": recommendation_timestamp,
            "exit_timestamp": evaluation_time,
            "holding_period": holding_period,
            "expected_holding_period": holding_period,
            "starting_price": starting_price,
            "ending_price": ending_price,
            "percentage_return": result["percentage_return"],
            "predicted_direction": result["predicted_direction"],
            "actual_direction": result["actual_direction"],
            "success": success,
            "hit": success,
            "status": self.SUCCEEDED if success else self.FAILED,
            "notes": notes,
            "validation_notes": notes,
            "validation_window": holding_period,
        }

    def pending_result(self, recommendation, recommendation_timestamp, notes=""):
        return self._status_result(
            recommendation=recommendation,
            recommendation_timestamp=recommendation_timestamp,
            status=self.PENDING,
            notes=notes or "Awaiting validation.",
        )

    def expired_result(
        self,
        recommendation,
        recommendation_timestamp,
        evaluation_timestamp=None,
        notes="",
    ):
        return self._status_result(
            recommendation=recommendation,
            recommendation_timestamp=recommendation_timestamp,
            evaluation_timestamp=evaluation_timestamp,
            status=self.EXPIRED,
            notes=notes or "Recommendation expired before validation.",
        )

    def performance_metrics(self, validation_results):
        completed_results = [
            result for result in validation_results
            if result.get("status") in {self.SUCCEEDED, self.FAILED}
        ]

        return self.backtest_engine.evaluate_batch(completed_results)

    def multiple_window_results(
        self,
        recommendation,
        recommendation_timestamp,
        windows=None,
    ):
        return [
            self.pending_result(
                recommendation=recommendation,
                recommendation_timestamp=recommendation_timestamp,
                notes=f"Awaiting {window}-day validation.",
            ) | {
                "expected_holding_period": window,
                "validation_window": window,
            }
            for window in (windows or self.VALIDATION_WINDOWS)
        ]

    def _status_result(
        self,
        recommendation,
        recommendation_timestamp,
        status,
        evaluation_timestamp=None,
        notes="",
    ):
        return {
            "recommendation_id": self._get(recommendation, "id", None),
            "ticker": self._get(recommendation, "ticker", ""),
            "recommendation": self._get(recommendation, "action", "HOLD"),
            "recommendation_timestamp": recommendation_timestamp,
            "evaluation_timestamp": evaluation_timestamp,
            "entry_timestamp": recommendation_timestamp,
            "exit_timestamp": evaluation_timestamp,
            "holding_period": None,
            "expected_holding_period": None,
            "starting_price": None,
            "ending_price": None,
            "percentage_return": None,
            "predicted_direction": self.backtest_engine._predicted_direction(
                recommendation
            ),
            "actual_direction": None,
            "success": None,
            "hit": None,
            "status": status,
            "notes": notes,
            "validation_notes": notes,
            "validation_window": None,
        }

    def _get(self, item, key, fallback):
        if isinstance(item, dict):
            return item.get(key, fallback)

        return getattr(item, key, fallback)
