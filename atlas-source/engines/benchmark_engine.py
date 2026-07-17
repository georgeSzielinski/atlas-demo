from datetime import datetime


class BenchmarkEngine:
    DEFAULT_VERSION = "abs-v1"
    HIGH_CONFIDENCE_THRESHOLD = 70
    HIGH_SIGNAL_QUALITY_THRESHOLD = 7

    def benchmark_recommendations(
        self,
        validation_results,
        engine_name="recommendation",
        version=DEFAULT_VERSION,
        benchmark_date=None,
        notes="",
    ):
        completed = [
            result for result in validation_results
            if result.get("status") in {"Succeeded", "Failed"}
        ]
        returns = [
            result.get("percentage_return")
            for result in completed
            if result.get("percentage_return") is not None
        ]
        gains = [value for value in returns if value > 0]
        losses = [value for value in returns if value < 0]

        metrics = {
            "per_engine_accuracy": self._accuracy(completed),
            "rolling_accuracy": self._rolling_accuracy(completed),
            "buy_accuracy": self._accuracy_for_action(completed, "BUY"),
            "hold_accuracy": self._accuracy_for_action(completed, "HOLD"),
            "avoid_accuracy": self._accuracy_for_action(completed, "AVOID"),
            "overall_hit_rate": self._accuracy(completed),
            "recommendation_accuracy": self._accuracy(completed),
            "validation_success": self._accuracy(completed),
            "average_return": self._average(returns),
            "average_gain": self._average(gains),
            "average_loss": self._average(losses),
            "average_recommendation_lifetime": self._average_lifetime(
                completed
            ),
            "rolling_performance": self._rolling_return(completed),
            "high_confidence_accuracy": self._accuracy_for_threshold(
                completed,
                "confidence",
                self.HIGH_CONFIDENCE_THRESHOLD,
                high=True,
            ),
            "low_confidence_accuracy": self._accuracy_for_threshold(
                completed,
                "confidence",
                self.HIGH_CONFIDENCE_THRESHOLD,
                high=False,
            ),
            "confidence_calibration": self._confidence_calibration(
                completed
            ),
        }

        return self._benchmark_rows(
            engine_name,
            version,
            benchmark_date,
            metrics,
            notes,
        )

    def benchmark_signal_quality(
        self,
        validation_results,
        engine_name="signal_quality",
        version=DEFAULT_VERSION,
        benchmark_date=None,
        notes="",
    ):
        completed = [
            result for result in validation_results
            if result.get("status") in {"Succeeded", "Failed"}
        ]
        metrics = {
            "high_signal_quality_accuracy": self._accuracy_for_threshold(
                completed,
                "signal_quality_score",
                self.HIGH_SIGNAL_QUALITY_THRESHOLD,
                high=True,
            ),
            "low_signal_quality_accuracy": self._accuracy_for_threshold(
                completed,
                "signal_quality_score",
                self.HIGH_SIGNAL_QUALITY_THRESHOLD,
                high=False,
            ),
            "sample_count": len(completed),
        }

        return self._benchmark_rows(
            engine_name,
            version,
            benchmark_date,
            metrics,
            notes,
        )

    def benchmark_confidence_calibration(
        self,
        validation_results,
        engine_name="confidence",
        version=DEFAULT_VERSION,
        benchmark_date=None,
        notes="",
    ):
        return self.benchmark_recommendations(
            validation_results=validation_results,
            engine_name=engine_name,
            version=version,
            benchmark_date=benchmark_date,
            notes=notes,
        )

    def benchmark_evidence_sources(
        self,
        evidence_sources,
        engine_name="evidence",
        version=DEFAULT_VERSION,
        benchmark_date=None,
        notes="",
    ):
        date = benchmark_date or datetime.now().isoformat()
        rows = []

        for source in evidence_sources:
            rows.append({
                "engine_name": engine_name,
                "version": version,
                "benchmark_date": date,
                "source_name": self._get(source, "source_name", ""),
                "effectiveness_score": self._get(
                    source,
                    "effectiveness_score",
                    0,
                ),
                "sample_count": self._get(source, "sample_count", 0),
                "notes": self._get(source, "notes", notes),
            })

        return rows

    def benchmark_forecasts(
        self,
        forecast_results,
        engine_name="forecast",
        version=DEFAULT_VERSION,
        benchmark_date=None,
        notes="",
    ):
        comparable = [
            result for result in forecast_results
            if (
                self._get(result, "predicted_direction", None) is not None
                and self._get(result, "actual_direction", None) is not None
            )
        ]
        hits = [
            result for result in comparable
            if self._get(result, "predicted_direction", None)
            == self._get(result, "actual_direction", None)
        ]
        direction_accuracy = (
            round(len(hits) / len(comparable) * 100, 2)
            if comparable else 0
        )
        metrics = {
            "direction_accuracy": direction_accuracy,
            "mae": None,
            "rmse": None,
            "runtime": None,
        }

        return self._benchmark_rows(
            engine_name,
            version,
            benchmark_date,
            metrics,
            notes,
        )

    def save_benchmark_results(self, benchmark_rows):
        from database.repository import save_benchmark_results

        save_benchmark_results(benchmark_rows)

    def save_evidence_benchmarks(self, evidence_rows):
        from database.repository import save_evidence_benchmarks

        save_evidence_benchmarks(evidence_rows)

    def _benchmark_rows(
        self,
        engine_name,
        version,
        benchmark_date,
        metrics,
        notes,
    ):
        date = benchmark_date or datetime.now().isoformat()

        return [
            {
                "engine_name": engine_name,
                "version": version,
                "benchmark_date": date,
                "metric": metric,
                "value": value,
                "notes": notes,
                "suggested_adjustment": self._suggested_adjustment(
                    metric,
                    value,
                ),
                "adjustment_reason": self._adjustment_reason(metric, value),
                "requires_human_approval": True,
                "benchmark_snapshot": self._snapshot(
                    engine_name,
                    version,
                    date,
                    metric,
                    value,
                ),
            }
            for metric, value in metrics.items()
        ]

    def _snapshot(self, engine_name, version, date, metric, value):
        return {
            "engine_name": engine_name,
            "version": version,
            "benchmark_date": date,
            "metric": metric,
            "value": value,
        }

    def _suggested_adjustment(self, metric, value):
        if value is None:
            return "collect_more_data"

        if metric.endswith("accuracy") and value < 50:
            return "review_signal_weight_or_threshold"

        if metric == "overall_hit_rate" and value < 50:
            return "review_recommendation_rules"

        if metric == "average_return" and value < 0:
            return "review_loss_drivers"

        return "no_change_suggested"

    def _adjustment_reason(self, metric, value):
        if value is None:
            return f"{metric} is not calculated yet."

        if metric.endswith("accuracy") and value < 50:
            return f"{metric} is below the review threshold."

        if metric == "overall_hit_rate" and value < 50:
            return "Overall hit rate is below the review threshold."

        if metric == "average_return" and value < 0:
            return "Average return is negative."

        return "Metric does not indicate a required adjustment."

    def _accuracy_for_action(self, results, action):
        matching = [
            result for result in results
            if self._get(result, "recommendation", "") == action
        ]

        return self._accuracy(matching)

    def _accuracy_for_threshold(self, results, key, threshold, high):
        matching = []

        for result in results:
            value = self._get(result, key, None)

            if value is None:
                continue

            if high and value >= threshold:
                matching.append(result)
            elif not high and value < threshold:
                matching.append(result)

        return self._accuracy(matching)

    def _accuracy(self, results):
        if not results:
            return 0

        hits = [
            result for result in results
            if self._get(result, "success", False)
            or self._get(result, "hit", False)
        ]

        return round(len(hits) / len(results) * 100, 2)

    def _average(self, values):
        if not values:
            return 0

        return round(sum(values) / len(values), 2)

    def _rolling_accuracy(self, results, window=3):
        return self._accuracy(results[-window:])

    def _rolling_return(self, results, window=3):
        returns = [
            result.get("percentage_return")
            for result in results[-window:]
            if result.get("percentage_return") is not None
        ]

        return self._average(returns)

    def _average_lifetime(self, results):
        periods = [
            result.get("holding_period")
            for result in results
            if result.get("holding_period") is not None
        ]

        return self._average(periods)

    def _confidence_calibration(self, results):
        high_confidence_accuracy = self._accuracy_for_threshold(
            results,
            "confidence",
            self.HIGH_CONFIDENCE_THRESHOLD,
            high=True,
        )
        low_confidence_accuracy = self._accuracy_for_threshold(
            results,
            "confidence",
            self.HIGH_CONFIDENCE_THRESHOLD,
            high=False,
        )

        return round(high_confidence_accuracy - low_confidence_accuracy, 2)

    def _get(self, item, key, fallback):
        if isinstance(item, dict):
            return item.get(key, fallback)

        return getattr(item, key, fallback)
