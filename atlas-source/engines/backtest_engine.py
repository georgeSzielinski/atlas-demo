class BacktestEngine:

    def evaluate_recommendation(
        self,
        recommendation,
        entry_price,
        exit_price,
        holding_period,
        recommendation_timestamp
    ):
        percentage_return = self._percentage_return(entry_price, exit_price)
        predicted_direction = self._predicted_direction(recommendation)
        actual_direction = self._actual_direction(percentage_return)

        return {
            "recommendation_id": self._get(recommendation, "id", None),
            "ticker": self._get(recommendation, "ticker", ""),
            "recommendation": self._get(recommendation, "action", "HOLD"),
            "predicted_direction": predicted_direction,
            "actual_direction": actual_direction,
            "percentage_return": percentage_return,
            "hit": predicted_direction == actual_direction,
            "success": predicted_direction == actual_direction,
            "holding_period": holding_period,
            "recommendation_timestamp": recommendation_timestamp,
        }

    def evaluate_batch(self, evaluations):
        if not evaluations:
            return {
                "count": 0,
                "hit_rate": 0,
                "overall_hit_rate": 0,
                "average_return": 0,
                "average_gain": 0,
                "average_loss": 0,
                "largest_gain": 0,
                "largest_loss": 0,
                "win_loss_ratio": None,
                "buy_hit_rate": 0,
                "hold_hit_rate": 0,
                "avoid_hit_rate": 0,
                "max_drawdown": None,
                "sharpe_ratio": None,
            }

        returns = [
            evaluation["percentage_return"]
            for evaluation in evaluations
        ]
        gains = [
            percentage_return for percentage_return in returns
            if percentage_return > 0
        ]
        losses = [
            percentage_return for percentage_return in returns
            if percentage_return < 0
        ]
        hits = [
            evaluation for evaluation in evaluations
            if evaluation.get("hit") or evaluation.get("success")
        ]

        return {
            "count": len(evaluations),
            "hit_rate": round(len(hits) / len(evaluations) * 100, 2),
            "overall_hit_rate": round(len(hits) / len(evaluations) * 100, 2),
            "buy_hit_rate": self._hit_rate_for_action(evaluations, "BUY"),
            "hold_hit_rate": self._hit_rate_for_action(evaluations, "HOLD"),
            "avoid_hit_rate": self._hit_rate_for_action(evaluations, "AVOID"),
            "average_return": self._average(returns),
            "average_gain": self._average(gains),
            "average_loss": self._average(losses),
            "largest_gain": max(gains) if gains else 0,
            "largest_loss": min(losses) if losses else 0,
            "win_loss_ratio": self._win_loss_ratio(gains, losses),
            "max_drawdown": None,
            "sharpe_ratio": None,
        }

    def generate_report(self, results):
        summary = (
            results
            if isinstance(results, dict)
            else self.evaluate_batch(results)
        )

        win_loss_ratio = self._format_placeholder(summary["win_loss_ratio"])
        max_drawdown = self._format_placeholder(summary["max_drawdown"])
        sharpe_ratio = self._format_placeholder(summary["sharpe_ratio"])

        return "\n".join([
            "Atlas Backtest Report",
            "=====================",
            f"Total Recommendations: {summary['count']}",
            f"Hit Rate: {self._format_number(summary['hit_rate'])}%",
            f"Average Return: {self._format_number(summary['average_return'])}%",
            f"Average Gain: {self._format_number(summary['average_gain'])}%",
            f"Average Loss: {self._format_number(summary['average_loss'])}%",
            f"Largest Gain: {self._format_number(summary['largest_gain'])}%",
            f"Largest Loss: {self._format_number(summary['largest_loss'])}%",
            f"Win/Loss Ratio: {win_loss_ratio}",
            f"Max Drawdown: {max_drawdown}",
            f"Sharpe Ratio: {sharpe_ratio}",
        ])

    def _predicted_direction(self, recommendation):
        action = self._get(recommendation, "action", "HOLD")

        if action == "BUY":
            return "UP"

        if action == "AVOID":
            return "DOWN"

        return "FLAT"

    def _actual_direction(self, percentage_return):
        if percentage_return > 1:
            return "UP"

        if percentage_return < -1:
            return "DOWN"

        return "FLAT"

    def _percentage_return(self, entry_price, exit_price):
        if entry_price == 0:
            raise ValueError("Entry price cannot be zero.")

        return round((exit_price - entry_price) / entry_price * 100, 2)

    def _average(self, values):
        if not values:
            return 0

        return round(sum(values) / len(values), 2)

    def _hit_rate_for_action(self, evaluations, action):
        matching = [
            evaluation for evaluation in evaluations
            if self._get(evaluation, "recommendation", "") == action
        ]

        if not matching:
            return 0

        hits = [
            evaluation for evaluation in matching
            if evaluation.get("hit") or evaluation.get("success")
        ]

        return round(len(hits) / len(matching) * 100, 2)

    def _win_loss_ratio(self, gains, losses):
        if not losses:
            return None

        return round(len(gains) / len(losses), 2)

    def _format_placeholder(self, value):
        if value is None:
            return "Not calculated yet"

        if isinstance(value, float):
            return self._format_number(value)

        return value

    def _format_number(self, value):
        if isinstance(value, float) and value.is_integer():
            return str(int(value))

        return str(value)

    def _get(self, item, key, fallback):
        if isinstance(item, dict):
            return item.get(key, fallback)

        return getattr(item, key, fallback)
