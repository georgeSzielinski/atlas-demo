from datetime import datetime


class ScientificValidationEngine:
    REQUIRED_METRICS = [
        "win_rate",
        "average_return",
        "sharpe_ratio",
        "max_drawdown",
        "probability_calibration",
        "recommendation_accuracy",
        "average_holding_period",
        "trade_frequency",
    ]
    REGIMES = [
        "Bull",
        "Bear",
        "Sideways",
        "High Volatility",
        "Low Volatility",
        "Rising Rates",
        "Falling Rates",
    ]
    GENERALIZATION_TESTS = [
        "training_period",
        "validation_period",
        "out_of_sample_period",
        "walk_forward_placeholder",
    ]
    MIN_SAMPLE_SIZE = 20
    ADOPTABLE_METRICS = {
        "win_rate",
        "average_return",
        "sharpe_ratio",
        "max_drawdown",
        "probability_calibration",
        "recommendation_accuracy",
    }

    def evaluate(
        self,
        experiment_id,
        feature_tested,
        baseline,
        candidate,
        sample_size,
        experiment_date=None,
        regimes=None,
        generalization=None,
    ):
        date = experiment_date or datetime.now().isoformat()
        baseline_metrics = self._metrics(baseline)
        candidate_metrics = self._metrics(candidate)
        metric_comparison = self.compare_metrics(
            baseline_metrics,
            candidate_metrics,
        )
        regime_validation = self.cross_regime_validation(regimes or {})
        generalization_tests = self.generalization_tests(generalization or {})
        status = self.scientific_status(
            sample_size,
            metric_comparison,
            regime_validation,
            generalization_tests,
        )
        adoption = self.adoption_decision(
            status,
            sample_size,
            metric_comparison,
            regime_validation,
            generalization_tests,
        )

        return {
            "experiment_id": experiment_id,
            "date": date,
            "feature_tested": feature_tested,
            "baseline": baseline_metrics,
            "candidate": candidate_metrics,
            "sample_size": sample_size,
            "metric_comparison": metric_comparison,
            "cross_regime_validation": regime_validation,
            "generalization_tests": generalization_tests,
            "scientific_result": status,
            "adoption_decision": adoption["decision"],
            "adoption_explanation": adoption["explanation"],
            "integrations": {
                "research_laboratory": True,
                "performance_observatory": True,
                "discovery_engine": True,
                "knowledge_graph": True,
            },
            "policy": self.policy(),
        }

    def compare_metrics(self, baseline, candidate):
        rows = []

        for metric in self.REQUIRED_METRICS:
            baseline_value = baseline.get(metric)
            candidate_value = candidate.get(metric)
            delta = self._delta(metric, baseline_value, candidate_value)
            status = self._metric_status(metric, delta)
            rows.append({
                "metric": metric,
                "baseline": baseline_value,
                "candidate": candidate_value,
                "delta": delta,
                "status": status,
            })

        return rows

    def cross_regime_validation(self, regimes):
        return [
            {
                "regime": regime,
                "status": self._named_status(regimes.get(regime, {})),
                "metrics": self._metrics(regimes.get(regime, {})),
            }
            for regime in self.REGIMES
        ]

    def generalization_tests(self, generalization):
        return [
            {
                "test": test,
                "status": self._named_status(generalization.get(test, {})),
                "details": generalization.get(test, {}),
            }
            for test in self.GENERALIZATION_TESTS
        ]

    def scientific_status(
        self,
        sample_size,
        metric_comparison,
        regime_validation,
        generalization_tests,
    ):
        if sample_size < self.MIN_SAMPLE_SIZE:
            return "Not Enough Evidence"

        adoptable = [
            item for item in metric_comparison
            if item["metric"] in self.ADOPTABLE_METRICS
        ]
        improved = [
            item for item in adoptable if item["status"] == "Improved"
        ]
        regressions = [
            item for item in adoptable if item["status"] == "Regression"
        ]
        regime_failures = [
            item for item in regime_validation
            if item["status"] == "Regression"
        ]
        regime_gaps = [
            item for item in regime_validation
            if item["status"] == "Not Enough Evidence"
        ]
        generalization_failures = [
            item for item in generalization_tests
            if item["status"] == "Regression"
        ]
        generalization_gaps = [
            item for item in generalization_tests
            if item["status"] == "Not Enough Evidence"
        ]

        if regime_gaps or generalization_gaps:
            return "Not Enough Evidence"

        if regressions or regime_failures or generalization_failures:
            return "Regression"

        if len(improved) >= 4:
            return "Improved"

        return "Neutral"

    def adoption_decision(
        self,
        status,
        sample_size,
        metric_comparison,
        regime_validation,
        generalization_tests,
    ):
        improved_metrics = [
            item["metric"] for item in metric_comparison
            if item["status"] == "Improved"
        ]
        regressed_metrics = [
            item["metric"] for item in metric_comparison
            if item["status"] == "Regression"
        ]
        regime_regressions = [
            item["regime"] for item in regime_validation
            if item["status"] == "Regression"
        ]
        generalization_regressions = [
            item["test"] for item in generalization_tests
            if item["status"] == "Regression"
        ]

        if status == "Improved":
            return {
                "decision": "ADOPT",
                "explanation": (
                    "ADOPT: sample size is sufficient and candidate improved "
                    f"{len(improved_metrics)} required metrics without regime "
                    "or generalization regression."
                ),
            }

        if status == "Regression":
            reasons = regressed_metrics + regime_regressions + generalization_regressions
            return {
                "decision": "REJECT",
                "explanation": (
                    "REJECT: candidate produced deterministic regression in "
                    f"{', '.join(reasons) or 'validation evidence'}."
                ),
            }

        if status == "Not Enough Evidence":
            return {
                "decision": "RETEST",
                "explanation": (
                    "RETEST: sample size "
                    f"{sample_size} is below the required "
                    f"{self.MIN_SAMPLE_SIZE} observations."
                ),
            }

        return {
            "decision": "RETEST",
            "explanation": (
                "RETEST: candidate is neutral; it did not demonstrate enough "
                "measured improvement for adoption."
            ),
        }

    def policy(self):
        return {
            "read_only": True,
            "deterministic": True,
            "changes_recommendation_behavior": False,
            "automatic_adoption": False,
            "broker_integration": False,
        }

    def _metrics(self, values):
        source = values or {}

        return {
            metric: source.get(metric, 0)
            for metric in self.REQUIRED_METRICS
        }

    def _delta(self, metric, baseline, candidate):
        if metric == "max_drawdown":
            return round(abs(baseline or 0) - abs(candidate or 0), 4)

        return round((candidate or 0) - (baseline or 0), 4)

    def _metric_status(self, metric, delta):
        threshold = 0.01

        if metric in {"average_holding_period", "trade_frequency"}:
            threshold = 0.1

        if delta > threshold:
            return "Improved"

        if delta < -threshold:
            return "Regression"

        return "Neutral"

    def _named_status(self, values):
        if not values:
            return "Not Enough Evidence"

        status = values.get("status")
        if status in {
            "Improved",
            "Neutral",
            "Regression",
            "Not Enough Evidence",
        }:
            return status

        sample_size = values.get("sample_size", self.MIN_SAMPLE_SIZE)
        if sample_size < self.MIN_SAMPLE_SIZE:
            return "Not Enough Evidence"

        delta = values.get("candidate_return", 0) - values.get(
            "baseline_return",
            0,
        )
        return self._metric_status("average_return", delta)
