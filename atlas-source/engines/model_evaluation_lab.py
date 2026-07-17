from datetime import datetime


class ModelEvaluationLab:
    DEFAULT_CANDIDATES = [
        {
            "model_name": "Mock Forecast",
            "model_type": "forecast",
            "provider": "mock",
            "status": "available",
            "integration_difficulty": "Low",
        },
        {
            "model_name": "Kronos",
            "model_type": "forecast",
            "provider": "kronos",
            "status": "candidate",
            "integration_difficulty": "Medium",
        },
        {
            "model_name": "Chronos",
            "model_type": "forecast",
            "provider": "future",
            "status": "future_placeholder",
            "integration_difficulty": "High",
        },
        {
            "model_name": "TimesFM",
            "model_type": "forecast",
            "provider": "future",
            "status": "future_placeholder",
            "integration_difficulty": "High",
        },
        {
            "model_name": "FinBERT",
            "model_type": "sentiment",
            "provider": "future",
            "status": "future_placeholder",
            "integration_difficulty": "Medium",
        },
        {
            "model_name": "Financial RoBERTa",
            "model_type": "sentiment",
            "provider": "future",
            "status": "future_placeholder",
            "integration_difficulty": "Medium",
        },
    ]

    DIFFICULTY_SCORES = {
        "Low": 100,
        "Medium": 70,
        "High": 40,
    }

    def evaluate(
        self,
        dataset,
        date_range,
        validation_window,
        candidates=None,
        evaluation_date=None,
    ):
        rows = []
        for candidate in candidates or self.DEFAULT_CANDIDATES:
            row = self._evaluation_row(
                candidate,
                dataset,
                date_range,
                validation_window,
                evaluation_date or datetime.now().isoformat(),
            )
            rows.append(row)

        rankings = self.rank_models(rows)

        return {
            "evaluations": rows,
            "rankings": rankings,
            "controlled_learning": self.controlled_learning(),
        }

    def rank_models(self, evaluations):
        ranked = sorted(
            evaluations,
            key=lambda item: (
                item["overall_score"],
                item["accuracy"],
                item["sharpe_ratio"],
                -item["cost_placeholder"],
                item["model_name"],
            ),
            reverse=True,
        )
        not_recommended = [
            item for item in evaluations
            if item["recommendation"] == "Not recommended"
        ]
        recommended = [
            item for item in evaluations
            if item["recommendation"] != "Not recommended"
        ]

        return {
            "best_overall": self._name(ranked),
            "best_accuracy": self._name(sorted(
                recommended,
                key=lambda item: (item["accuracy"], item["model_name"]),
                reverse=True,
            )),
            "best_risk_adjusted": self._name(sorted(
                recommended,
                key=lambda item: (item["sharpe_ratio"], item["model_name"]),
                reverse=True,
            )),
            "best_low_cost": self._name(sorted(
                recommended,
                key=lambda item: (
                    -item["cost_placeholder"],
                    item["overall_score"],
                    item["model_name"],
                ),
                reverse=True,
            )),
            "best_speed": self._name(sorted(
                recommended,
                key=lambda item: (
                    -item["runtime_placeholder"],
                    item["overall_score"],
                    item["model_name"],
                ),
                reverse=True,
            )),
            "not_recommended": [
                item["model_name"] for item in sorted(
                    not_recommended,
                    key=lambda item: item["model_name"],
                )
            ],
            "ordered": ranked,
        }

    def controlled_learning(self):
        return {
            "can_suggest_model_adoption": True,
            "can_auto_adopt_models": False,
            "requires_human_approval": True,
            "policy": (
                "Model evaluations are advisory. Atlas can suggest adoption "
                "candidates, but cannot install, activate, or auto-adopt models."
            ),
        }

    def _evaluation_row(
        self,
        candidate,
        dataset,
        date_range,
        validation_window,
        evaluation_date,
    ):
        sample_size = candidate.get("sample_size", 0)
        accuracy = candidate.get("accuracy", 0)
        win_rate = candidate.get("win_rate", accuracy)
        average_return = candidate.get("average_return", 0)
        sharpe_ratio = candidate.get("sharpe_ratio", 0)
        max_drawdown = candidate.get("max_drawdown", 0)
        runtime = candidate.get("runtime_placeholder", 0)
        memory = candidate.get("memory_placeholder", 0)
        cost = candidate.get("cost_placeholder", 0)
        difficulty = candidate.get("integration_difficulty", "High")
        overall_score = self._overall_score(
            accuracy,
            win_rate,
            average_return,
            sharpe_ratio,
            max_drawdown,
            runtime,
            cost,
            difficulty,
        )

        return {
            "model_name": candidate.get("model_name", ""),
            "model_type": candidate.get("model_type", ""),
            "provider": candidate.get("provider", ""),
            "dataset": dataset,
            "date_range": date_range,
            "validation_window": validation_window,
            "sample_size": sample_size,
            "accuracy": accuracy,
            "win_rate": win_rate,
            "average_return": average_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "runtime_placeholder": runtime,
            "memory_placeholder": memory,
            "cost_placeholder": cost,
            "integration_difficulty": difficulty,
            "recommendation": self._recommendation(
                overall_score,
                sample_size,
                candidate.get("status", ""),
            ),
            "overall_score": overall_score,
            "evaluation_date": evaluation_date,
            "status": candidate.get("status", "candidate"),
        }

    def _overall_score(
        self,
        accuracy,
        win_rate,
        average_return,
        sharpe_ratio,
        max_drawdown,
        runtime,
        cost,
        difficulty,
    ):
        return_score = max(0, min(100, 50 + average_return * 5))
        sharpe_score = max(0, min(100, 50 + sharpe_ratio * 20))
        drawdown_score = max(0, min(100, 100 + max_drawdown * 3))
        speed_score = max(0, min(100, 100 - runtime))
        cost_score = max(0, min(100, 100 - cost))
        difficulty_score = self.DIFFICULTY_SCORES.get(difficulty, 40)
        score = (
            accuracy * 0.25
            + win_rate * 0.15
            + return_score * 0.15
            + sharpe_score * 0.15
            + drawdown_score * 0.10
            + speed_score * 0.08
            + cost_score * 0.07
            + difficulty_score * 0.05
        )

        return round(max(0, min(100, score)), 2)

    def _recommendation(self, overall_score, sample_size, status):
        if status == "future_placeholder":
            return "Not recommended"

        if sample_size < 5:
            return "Needs more validation"

        if overall_score >= 75:
            return "Candidate for human review"

        if overall_score >= 60:
            return "Continue benchmarking"

        return "Not recommended"

    def _name(self, rows):
        if not rows:
            return None

        return rows[0]["model_name"]
