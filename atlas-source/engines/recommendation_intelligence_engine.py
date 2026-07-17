"""Deterministic, read-only analytics over recommendation outcome history."""

from collections import Counter
from datetime import datetime
import math


def normalize_confidence(value):
    """Normalize trusted stored confidence to 0-100, or return unavailable."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 100:
        return None
    return value * 100 if value <= 1 else value


class RecommendationIntelligenceEngine:
    VERSION = "recommendation-intelligence-v1"
    ACTIONS = ("BUY", "HOLD", "AVOID")
    COMPLETED_STATUSES = {"Succeeded", "Failed", "Expired"}
    ACCURACY_STATUSES = {"Succeeded", "Failed"}
    CONFIDENCE_BUCKETS = (
        (0, 49), (50, 59), (60, 69), (70, 79), (80, 89), (90, 100)
    )
    DEFAULT_ROLLING_WINDOW = 20
    DEFAULT_TOP_LIMIT = 10
    ACCURACY_SCOPE = "recommendation_horizon_evaluations"
    TRUNCATION_WARNING = (
        "Source projection was truncated; reported analytics may be incomplete."
    )
    MINIMUM_CALIBRATION_SAMPLE = 20

    def report(
        self,
        ticker=None,
        action=None,
        horizon=None,
        evaluation_source="paper",
        rolling_window=DEFAULT_ROLLING_WINDOW,
        top_limit=DEFAULT_TOP_LIMIT,
        source_loader=None,
        now=None,
    ):
        window = max(1, min(int(rolling_window), 500))
        top = max(1, min(int(top_limit), 100))
        source = (source_loader or self._source)(
            ticker=ticker,
            action=action,
            horizon=horizon,
            evaluation_source=evaluation_source,
        )
        records = list(source.get("records") or [])
        outcome_rows = [r for r in records if r.get("outcome_id") is not None]
        completed = [r for r in outcome_rows if r.get("status") in self.COMPLETED_STATUSES]
        scored = [r for r in outcome_rows if r.get("status") in self.ACCURACY_STATUSES]
        recommendations = self._recommendations(records)
        completed_recommendations = {
            row.get("recommendation_id") for row in completed
        }
        recommendations_with_outcomes = {
            row.get("recommendation_id") for row in outcome_rows
        }
        source_total = source.get("total", len(records))
        truncated = bool(source.get("truncated"))

        return {
            "generated_at": self._moment(now).isoformat(),
            "version": self.VERSION,
            "status": "EVALUATED" if records else "NOT_EVALUATED",
            "reason": None if records else "No recommendation history matched the selectors.",
            "summary": {
                "overall_accuracy": self._accuracy(scored),
                "accuracy_scope": self.ACCURACY_SCOPE,
                "multiple_horizons_weight_separately": True,
                "unique_recommendation_accuracy": "NOT_EVALUATED",
                "recommendation_volume": len(recommendations),
                "completed_evaluations": len(completed),
                "accuracy_evaluations": len(scored),
                "pending_evaluations": sum(
                    r.get("status") in {"Pending", "Deferred"} for r in outcome_rows
                ),
                "outcome_completion_rate": self._rate(len(completed), len(outcome_rows)),
                "recommendations_without_outcomes": (
                    len(recommendations) - len(recommendations_with_outcomes)
                ),
                "recommendation_outcome_coverage": self._rate(
                    len(completed_recommendations), len(recommendations)
                ),
            },
            "accuracy_by_action": self._accuracy_by_action(scored),
            "accuracy_by_confidence": self._confidence_buckets(scored),
            "confidence_calibration": self._confidence_calibration(scored),
            "average_returns_by_action": self._returns_by_action(scored),
            "best_performing_recommendations": self._ranked(scored, top, reverse=True),
            "worst_performing_recommendations": self._ranked(scored, top, reverse=False),
            "rolling_accuracy": self._rolling_accuracy(scored, window),
            "recommendation_volume": self._volume(recommendations),
            "outcome_status": self._outcome_status(outcome_rows),
            "selectors": source.get("filters") or {},
            "data": {
                "joined_record_count": len(records),
                "source_record_count": source_total,
                "analyzed_row_count": len(records),
                "source_total_row_count": source_total,
                "limit": source.get("limit"),
                "truncated": truncated,
                "warning": self.TRUNCATION_WARNING if truncated else None,
                "measurement_unit": "completed recommendation-horizon evaluation",
                "accuracy_sample_explanation": (
                    "Each Succeeded or Failed completed horizon is a separate accuracy "
                    "sample; an older recommendation with five such completed horizons "
                    "contributes five evaluation samples."
                ),
            },
            "policy": self.policy(),
        }

    def status(self, source_loader=None):
        try:
            report = self.report(source_loader=source_loader)
        except Exception as error:
            return {
                "status": "Unavailable",
                "reason": f"{type(error).__name__}: {error}",
                "overall_accuracy": None,
                "recommendation_volume": 0,
                "completed_evaluations": 0,
                "pending_evaluations": 0,
                "outcome_completion_rate": None,
                "recommendations_without_outcomes": 0,
                "recommendation_outcome_coverage": None,
                "truncated": False,
                "analyzed_row_count": 0,
                "source_total_row_count": 0,
                "warning": None,
                "accuracy_scope": self.ACCURACY_SCOPE,
                "multiple_horizons_weight_separately": True,
                "unique_recommendation_accuracy": "NOT_EVALUATED",
                "policy": self.policy(),
            }
        summary = report["summary"]
        return {
            "status": report["status"],
            "overall_accuracy": summary["overall_accuracy"],
            "recommendation_volume": summary["recommendation_volume"],
            "completed_evaluations": summary["completed_evaluations"],
            "pending_evaluations": summary["pending_evaluations"],
            "outcome_completion_rate": summary["outcome_completion_rate"],
            "recommendations_without_outcomes": summary["recommendations_without_outcomes"],
            "recommendation_outcome_coverage": summary["recommendation_outcome_coverage"],
            "truncated": report["data"]["truncated"],
            "analyzed_row_count": report["data"]["analyzed_row_count"],
            "source_total_row_count": report["data"]["source_total_row_count"],
            "warning": report["data"]["warning"],
            "accuracy_scope": summary["accuracy_scope"],
            "multiple_horizons_weight_separately": summary[
                "multiple_horizons_weight_separately"
            ],
            "unique_recommendation_accuracy": summary[
                "unique_recommendation_accuracy"
            ],
            "policy": self.policy(),
        }

    def _recommendations(self, records):
        unique = {}
        for row in records:
            unique[row.get("recommendation_id")] = {
                "recommendation_id": row.get("recommendation_id"),
                "ticker": row.get("ticker"),
                "action": row.get("action"),
                "confidence": row.get("confidence"),
                "recommendation_at": row.get("recommendation_at"),
            }
        return list(unique.values())

    def _accuracy(self, rows):
        return self._rate(
            sum(row.get("status") == "Succeeded" for row in rows), len(rows)
        )

    def _accuracy_by_action(self, rows):
        return {
            action: self._metric([r for r in rows if r.get("action") == action])
            for action in self.ACTIONS
        }

    def _confidence_buckets(self, rows):
        return [
            {
                "bucket": f"{low}-{high}",
                "minimum": low,
                "maximum": high,
                **self._metric([
                    row for row in rows
                    if self._confidence(row) is not None
                    and low <= self._confidence(row) <= high
                ]),
            }
            for low, high in self.CONFIDENCE_BUCKETS
        ]

    def _confidence_calibration(self, rows):
        calibrated = []
        for bucket in self._confidence_buckets(rows):
            bucket_rows = [
                row for row in rows
                if self._confidence(row) is not None
                and bucket["minimum"] <= self._confidence(row) <= bucket["maximum"]
            ]
            confidences = [self._confidence(row) for row in bucket_rows]
            average_confidence = self._average(confidences)
            accuracy = bucket["accuracy"]
            gap = None if accuracy is None or average_confidence is None else round(average_confidence - accuracy, 2)
            calibrated.append({
                "bucket": bucket["bucket"],
                "sample_size": bucket["sample_size"],
                "average_confidence": average_confidence,
                "observed_accuracy": accuracy,
                "calibration_gap": gap,
                "calibration": (
                    "NO_DATA" if gap is None else
                    "OVERCONFIDENT" if gap > 0 else
                    "UNDERCONFIDENT" if gap < 0 else "CALIBRATED"
                ),
                "minimum_sample_size": self.MINIMUM_CALIBRATION_SAMPLE,
                "sample_warning": (
                    "NO_DATA" if not bucket["sample_size"] else
                    "INSUFFICIENT_SAMPLE" if bucket["sample_size"] < self.MINIMUM_CALIBRATION_SAMPLE else
                    None
                ),
                "statistical_confidence": (
                    "NOT_EVALUATED" if bucket["sample_size"] < self.MINIMUM_CALIBRATION_SAMPLE
                    else "DESCRIPTIVE_ONLY"
                ),
            })
        return calibrated

    def _returns_by_action(self, rows):
        result = {}
        for action in self.ACTIONS:
            returns = [
                float(row["percentage_return"])
                for row in rows
                if row.get("action") == action and row.get("percentage_return") is not None
            ]
            result[action] = {
                "average_return": self._average(returns),
                "sample_size": len(returns),
            }
        return result

    def _ranked(self, rows, limit, reverse):
        available = [r for r in rows if r.get("percentage_return") is not None]
        ordered = sorted(
            available,
            key=lambda r: (float(r["percentage_return"]), r.get("recommendation_id") or 0, r.get("outcome_id") or 0),
            reverse=reverse,
        )[:limit]
        return [self._performance_row(row) for row in ordered]

    def _rolling_accuracy(self, rows, window):
        ordered = sorted(
            rows,
            key=lambda r: (r.get("evaluation_at") or "", r.get("outcome_id") or 0),
        )
        points = []
        for index, row in enumerate(ordered):
            sample = ordered[max(0, index - window + 1):index + 1]
            points.append({
                "evaluation_at": row.get("evaluation_at"),
                "outcome_id": row.get("outcome_id"),
                "window": window,
                "sample_size": len(sample),
                "accuracy": self._accuracy(sample),
            })
        return points

    def _volume(self, recommendations):
        by_action = Counter(row.get("action") or "UNKNOWN" for row in recommendations)
        by_date = Counter(self._date(row.get("recommendation_at")) for row in recommendations)
        return {
            "total": len(recommendations),
            "by_action": {key: by_action.get(key, 0) for key in (*self.ACTIONS, "UNKNOWN")},
            "over_time": [
                {"date": date, "count": count}
                for date, count in sorted(by_date.items()) if date is not None
            ],
        }

    def _outcome_status(self, rows):
        counts = Counter(row.get("status") or "Pending" for row in rows)
        completed = sum(counts.get(status, 0) for status in self.COMPLETED_STATUSES)
        pending = counts.get("Pending", 0) + counts.get("Deferred", 0)
        return {
            "total_evaluations": len(rows),
            "completed": completed,
            "pending": pending,
            "deferred": counts.get("Deferred", 0),
            "expired": counts.get("Expired", 0),
            "succeeded": counts.get("Succeeded", 0),
            "failed": counts.get("Failed", 0),
            "completion_rate": self._rate(completed, len(rows)),
        }

    def _metric(self, rows):
        return {
            "accuracy": self._accuracy(rows),
            "successful": sum(row.get("status") == "Succeeded" for row in rows),
            "failed": sum(row.get("status") == "Failed" for row in rows),
            "sample_size": len(rows),
        }

    def _performance_row(self, row):
        return {
            key: row.get(key)
            for key in (
                "recommendation_id", "outcome_id", "ticker", "action", "confidence",
                "horizon_days", "percentage_return", "success", "evaluation_at",
            )
        }

    def _confidence(self, row):
        return normalize_confidence(row.get("confidence"))

    def _average(self, values):
        return None if not values else round(sum(values) / len(values), 2)

    def _rate(self, numerator, denominator):
        return None if denominator == 0 else round(numerator / denominator * 100, 2)

    def _date(self, value):
        return str(value)[:10] if value else None

    def _moment(self, value):
        if isinstance(value, datetime):
            return value
        if value:
            try:
                return datetime.fromisoformat(str(value))
            except ValueError:
                pass
        return datetime.now()

    def _source(self, **filters):
        from database.repository import get_recommendation_intelligence_records
        return get_recommendation_intelligence_records(**filters)

    def policy(self):
        return {
            "deterministic": True,
            "read_only": True,
            "paper_only": True,
            "uses_ai": False,
            "changes_recommendation_behavior": False,
            "changes_trading_behavior": False,
            "broker_integration": False,
        }
