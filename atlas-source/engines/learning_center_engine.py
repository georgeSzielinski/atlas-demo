"""Deterministic, read-only health analytics for the ATLAS learning platform."""

from collections import Counter
from datetime import datetime

from engines.committee_intelligence_engine import CommitteeIntelligenceEngine
from engines.engine_intelligence_engine import EngineIntelligenceEngine
from engines.learning_intelligence_metrics import (
    COMPLETED_STATUSES,
    HORIZONS,
    MINIMUM_SAMPLE,
    group_metrics,
    horizon_maturity,
    normalize_records,
    rate,
    subset,
)
from engines.recommendation_intelligence_engine import RecommendationIntelligenceEngine


class LearningCenterEngine:
    VERSION = "learning-center-v1"
    TRUNCATION_WARNING = (
        "Source projection was truncated; reported Learning Intelligence may be incomplete."
    )

    def report(
        self,
        ticker=None,
        committee=None,
        engine=None,
        sector=None,
        regime=None,
        horizon=None,
        evaluation_source="paper",
        rolling_window=20,
        limit=10000,
        source_loader=None,
        now=None,
    ):
        source = (source_loader or self._source)(
            ticker=ticker,
            sector=sector,
            regime=regime,
            horizon=horizon,
            evaluation_source=evaluation_source,
            limit=limit,
        )
        full_dataset = normalize_records(list(source.get("records") or []))
        selected_ids = self._selected_ids(full_dataset, committee, engine)
        dataset = subset(full_dataset, selected_ids)
        normalized_source = self._normalized_source(source, dataset)
        recommendation_report = RecommendationIntelligenceEngine().report(
            rolling_window=rolling_window,
            source_loader=lambda **_: normalized_source,
            now=now,
        )
        overall = group_metrics(dataset, rolling_window=rolling_window)
        committee_report = CommitteeIntelligenceEngine().report(
            committee=committee,
            rolling_window=rolling_window,
            source=normalized_source,
            now=now,
        )
        engine_report = EngineIntelligenceEngine().report(
            engine=engine,
            rolling_window=rolling_window,
            source=normalized_source,
            now=now,
        )
        context = self._recommendation_context(
            dataset, overall, committee_report, engine_report
        )
        outcomes = dataset["outcomes"]
        recommendations = dataset["recommendations"]
        truncated = bool(source.get("truncated"))
        data_maturity = self._data_maturity(
            len(recommendations), overall["accuracy_sample_size"]
        )

        return {
            "generated_at": self._moment(now).isoformat(),
            "version": self.VERSION,
            "status": "EVALUATED" if recommendations else "NOT_EVALUATED",
            "reason": None if recommendations else (
                "No persisted recommendation history matched the selectors."
            ),
            "summary": {
                "overall_recommendation_accuracy": overall["accuracy"],
                "accuracy_scope": "recommendation_horizon_evaluations",
                "multiple_horizons_weight_separately": True,
                "unique_recommendation_accuracy": "NOT_EVALUATED",
                "recommendation_volume": overall["recommendation_count"],
                "completed_evaluations": overall["completed_outcomes"],
                "accuracy_evaluations": overall["accuracy_sample_size"],
                "pending_evaluations": overall["pending"],
                "deferred_evaluations": overall["deferred"],
                "expired_evaluations": overall["expired"],
                "outcome_completion_rate": overall["outcome_completion"],
                "recommendation_coverage": overall["recommendation_coverage"],
                "data_maturity": data_maturity,
                "average_return": overall["average_return"],
                "return_sample_size": overall["return_sample_size"],
            },
            "rolling_accuracy": overall["rolling_accuracy"],
            "best_recommendations": self._top_performance(
                dataset, reverse=True, limit=10
            ),
            "worst_recommendations": self._top_performance(
                dataset, reverse=False, limit=10
            ),
            "outcome_distribution": self._outcome_distribution(outcomes),
            "historical_recommendation_volume": self._historical_volume(recommendations),
            "evaluation_maturity_by_horizon": horizon_maturity(outcomes),
            "confidence_calibration": self._calibration_summary(
                recommendation_report, overall
            ),
            "committee_intelligence": committee_report,
            "engine_intelligence": engine_report,
            "signal_intelligence": self._signal_intelligence(dataset, rolling_window),
            "sector_intelligence": self._dimension_intelligence(
                dataset, "sector", rolling_window
            ),
            "regime_intelligence": self._dimension_intelligence(
                dataset, "market_regime", rolling_window
            ),
            "system_health": self._system_health(
                recommendations,
                outcomes,
                committee_report,
                engine_report,
                recommendation_report,
                data_maturity,
            ),
            "evidence_quality": self._evidence_quality(outcomes),
            "recommendation_metrics": context,
            "selectors": {
                **(source.get("filters") or {}),
                "committee": committee,
                "engine": engine,
                "rolling_window": max(1, min(int(rolling_window), 500)),
            },
            "data": {
                "analyzed_row_count": len(source.get("records") or []),
                "selected_recommendation_count": len(recommendations),
                "source_total_row_count": source.get("total", 0),
                "limit": source.get("limit"),
                "truncated": truncated,
                "warning": self.TRUNCATION_WARNING if truncated else None,
                "accuracy_sample_explanation": (
                    "Each Succeeded or Failed completed horizon is a separate accuracy "
                    "sample; a recommendation with five scored horizons contributes five "
                    "evaluation samples."
                ),
                "performance_target": "O(n) normalization and indexed group lookups",
            },
            "policy": self.policy(),
        }

    def status(self, **kwargs):
        try:
            report = self.report(**kwargs)
        except Exception as error:
            return {
                "status": "Unavailable",
                "reason": f"{type(error).__name__}: {error}",
                "summary": self._empty_summary(),
                "committee_analytics_health": "Unavailable",
                "engine_analytics_health": "Unavailable",
                "truncated": False,
                "warning": None,
                "policy": self.policy(),
            }
        return {
            "status": report["status"],
            "reason": report["reason"],
            "summary": report["summary"],
            "committee_analytics_health": report["committee_intelligence"]["status"],
            "engine_analytics_health": report["engine_intelligence"]["status"],
            "committee_leader": (
                report["committee_intelligence"]["leaderboard"][0]
                if report["committee_intelligence"]["leaderboard"] else None
            ),
            "engine_leader": (
                report["engine_intelligence"]["leaderboard"][0]
                if report["engine_intelligence"]["leaderboard"] else None
            ),
            "calibration_health": report["confidence_calibration"]["status"],
            "rolling_accuracy": (
                report["rolling_accuracy"][-1]["accuracy"]
                if report["rolling_accuracy"] else None
            ),
            "data_freshness": report["system_health"]["data_freshness"],
            "truncated": report["data"]["truncated"],
            "analyzed_row_count": report["data"]["analyzed_row_count"],
            "source_total_row_count": report["data"]["source_total_row_count"],
            "warning": report["data"]["warning"],
            "deterministic": True,
            "paper_only": True,
            "policy": self.policy(),
        }

    def _selected_ids(self, dataset, committee, engine):
        ids = []
        committee_key = str(committee).strip().lower() if committee else None
        engine_key = str(engine).strip().lower() if engine else None
        for row in dataset["recommendations"]:
            if committee_key and not any(
                name.lower() == committee_key for name in row["committee_names"]
            ):
                continue
            if engine_key and not any(
                name.lower() == engine_key for name in row["engine_names"]
            ):
                continue
            ids.append(row["recommendation_id"])
        return ids

    def _normalized_source(self, source, dataset):
        outcomes_by_id = {}
        for outcome in dataset["outcomes"]:
            outcomes_by_id.setdefault(outcome["recommendation_id"], []).append(outcome)
        records = []
        for recommendation in dataset["recommendations"]:
            projection = {
                **recommendation,
                "committee_members": [
                    {"name": name} for name in recommendation["committee_names"]
                ],
                "evidence_breakdown": [
                    {
                        "category": name,
                        "confidence": recommendation["engine_confidence"].get(name),
                        "weight": 1 if name == recommendation.get("primary_engine") else 0,
                    }
                    for name in recommendation["engine_names"]
                ],
            }
            outcomes = outcomes_by_id.get(recommendation["recommendation_id"], [])
            if not outcomes:
                records.append({**projection, "outcome_id": None})
            for outcome in outcomes:
                records.append({**projection, **outcome})
        return {
            "records": records,
            "total": source.get("total", len(records)),
            "limit": source.get("limit"),
            "truncated": bool(source.get("truncated")),
            "filters": source.get("filters") or {},
        }

    def _calibration_summary(self, recommendation_report, overall):
        buckets = recommendation_report["confidence_calibration"]
        sample_size = overall["accuracy_sample_size"]
        gap = overall["calibration_gap"]
        if not sample_size:
            status = "NOT_EVALUATED"
        elif sample_size < MINIMUM_SAMPLE:
            status = "INSUFFICIENT_SAMPLE"
        elif gap is None:
            status = "NOT_EVALUATED"
        elif gap > 0:
            status = "OVERCONFIDENT"
        elif gap < 0:
            status = "UNDERCONFIDENT"
        else:
            status = "CALIBRATED"
        return {
            "status": status,
            "expected_confidence": overall["observed_confidence"],
            "observed_accuracy": overall["observed_accuracy"],
            "calibration_gap": gap,
            "sample_size": sample_size,
            "minimum_sample_size": MINIMUM_SAMPLE,
            "minimum_sample_warning": (
                "INSUFFICIENT_SAMPLE" if sample_size < MINIMUM_SAMPLE else None
            ),
            "statistical_confidence": "NOT_EVALUATED",
            "statistical_warning": (
                "Descriptive calibration only; statistical significance is not claimed."
            ),
            "overconfident_bucket_count": sum(
                row["calibration"] == "OVERCONFIDENT" for row in buckets
            ),
            "underconfident_bucket_count": sum(
                row["calibration"] == "UNDERCONFIDENT" for row in buckets
            ),
            "reliability_buckets": buckets,
        }

    def _recommendation_context(self, dataset, overall, committee_report, engine_report):
        outcomes_by_id = {}
        for outcome in dataset["outcomes"]:
            outcomes_by_id.setdefault(outcome["recommendation_id"], []).append(outcome)
        committee_by_name = {
            row["committee"]: row for row in committee_report["committees"]
        }
        engine_by_name = {row["engine"]: row for row in engine_report["engines"]}
        result = []
        for recommendation in dataset["recommendations"]:
            outcomes = outcomes_by_id.get(recommendation["recommendation_id"], [])
            completed = [row for row in outcomes if row["status"] in COMPLETED_STATUSES]
            horizons = sorted({row["horizon_days"] for row in completed})
            committee_name = recommendation["committee_names"][0] if recommendation["committee_names"] else None
            primary_engine = recommendation.get("primary_engine")
            committee_metrics = committee_by_name.get(committee_name, {})
            engine_metrics = engine_by_name.get(primary_engine, {})
            result.append({
                "recommendation_id": recommendation["recommendation_id"],
                "committee": committee_name,
                "committee_historical_accuracy": committee_metrics.get("accuracy"),
                "primary_engine": primary_engine,
                "engine_historical_accuracy": engine_metrics.get("accuracy"),
                "calibration_gap": committee_metrics.get(
                    "calibration_gap", overall.get("calibration_gap")
                ),
                "evaluation_maturity": rate(len(horizons), len(HORIZONS)),
                "recommendation_maturity": (
                    f"{horizons[-1]}d completed" if horizons else "NOT_EVALUATED"
                ),
                "outcome_maturity": rate(len(horizons), len(HORIZONS)),
                "evaluation_coverage": rate(len(horizons), len(HORIZONS)),
                "completion_rate": rate(len(completed), len(outcomes)),
            })
        return result

    def _dimension_intelligence(self, dataset, field, rolling_window):
        values = sorted({
            row[field] for row in dataset["recommendations"] if row.get(field)
        })
        groups = []
        for value in values:
            ids = [
                row["recommendation_id"] for row in dataset["recommendations"]
                if row.get(field) == value
            ]
            groups.append({field: value, **group_metrics(
                subset(dataset, ids), rolling_window=rolling_window
            )})
        return {
            "status": "EVALUATED" if groups else "NOT_EVALUATED",
            "reason": None if groups else f"No stored {field.replace('_', ' ')} evidence exists.",
            "groups": groups,
        }

    def _signal_intelligence(self, dataset, rolling_window):
        groups = []
        for signal in ("Forecast direction", "News sentiment", "Signal label"):
            values = sorted({
                row["signals"].get(signal)
                for row in dataset["recommendations"]
                if row["signals"].get(signal)
            })
            for value in values:
                ids = [
                    row["recommendation_id"] for row in dataset["recommendations"]
                    if row["signals"].get(signal) == value
                ]
                groups.append({
                    "signal": signal,
                    "value": value,
                    **group_metrics(subset(dataset, ids), rolling_window=rolling_window),
                })
        unavailable = [
            {"signal": name, "status": "NOT_EVALUATED", "reason": "Not stored per recommendation."}
            for name in ("RSI", "MACD", "Moving averages", "Momentum", "Trend", "Volatility", "Valuation percentile")
        ]
        return {
            "status": "EVALUATED" if groups else "NOT_EVALUATED",
            "groups": groups,
            "unavailable": unavailable,
        }

    def _top_performance(self, dataset, reverse, limit):
        rows = [
            row for row in dataset["outcomes"]
            if row["status"] in {"Succeeded", "Failed"}
            and row["percentage_return"] is not None
        ]
        return sorted(
            rows,
            key=lambda row: (
                row["percentage_return"],
                str(row["recommendation_id"]),
                str(row["outcome_id"]),
            ),
            reverse=reverse,
        )[:limit]

    def _outcome_distribution(self, outcomes):
        counts = Counter(row["status"] for row in outcomes)
        return [
            {"status": status, "count": counts[status]}
            for status in ("Succeeded", "Failed", "Pending", "Deferred", "Expired")
        ]

    def _historical_volume(self, recommendations):
        counts = Counter(
            str(row["recommendation_at"])[:10]
            for row in recommendations if row.get("recommendation_at")
        )
        return [{"date": date, "count": counts[date]} for date in sorted(counts)]

    def _data_maturity(self, recommendation_count, scored_count):
        if not recommendation_count:
            return "NOT_EVALUATED"
        if not scored_count:
            return "OUTCOMES_PENDING"
        if scored_count < MINIMUM_SAMPLE:
            return "LIMITED"
        if scored_count < 100:
            return "DEVELOPING"
        return "MATURE"

    def _evidence_quality(self, outcomes):
        if not outcomes:
            return {
                "status": "NOT_EVALUATED",
                "price_lineage_coverage": None,
                "evaluation_source_coverage": None,
                "sample_size": 0,
            }
        return {
            "status": "EVALUATED",
            "price_lineage_coverage": rate(sum(
                row["starting_price"] is not None and row["ending_price"] is not None
                for row in outcomes
            ), len(outcomes)),
            "evaluation_source_coverage": rate(sum(
                bool(row["evaluation_source"]) for row in outcomes
            ), len(outcomes)),
            "sample_size": len(outcomes),
        }

    def _system_health(
        self,
        recommendations,
        outcomes,
        committee_report,
        engine_report,
        recommendation_report,
        data_maturity,
    ):
        timestamps = [
            value
            for value in [
                *[row.get("evaluation_at") for row in outcomes],
                *[row.get("recommendation_at") for row in recommendations],
            ]
            if value
        ]
        return {
            "deterministic_status": "CONFIRMED",
            "paper_only_status": "CONFIRMED",
            "read_only_status": "CONFIRMED",
            "outcome_evidence": "EVALUATED" if outcomes else "NOT_EVALUATED",
            "committee_analytics": committee_report["status"],
            "engine_analytics": engine_report["status"],
            "calibration": (
                "EVALUATED" if recommendation_report["summary"]["accuracy_evaluations"]
                else "NOT_EVALUATED"
            ),
            "data_maturity": data_maturity,
            "data_freshness": max(timestamps) if timestamps else None,
        }

    def _empty_summary(self):
        return {
            "overall_recommendation_accuracy": None,
            "recommendation_volume": 0,
            "completed_evaluations": 0,
            "pending_evaluations": 0,
            "deferred_evaluations": 0,
            "expired_evaluations": 0,
            "outcome_completion_rate": None,
            "recommendation_coverage": None,
            "data_maturity": "NOT_EVALUATED",
            "average_return": None,
        }

    def _source(self, **filters):
        from database.repository import get_learning_intelligence_records
        return get_learning_intelligence_records(**filters)

    def _moment(self, value):
        if isinstance(value, datetime):
            return value
        if value:
            try:
                return datetime.fromisoformat(str(value))
            except ValueError:
                pass
        return datetime.now()

    def policy(self):
        return {
            "deterministic": True,
            "read_only": True,
            "paper_only": True,
            "uses_ai": False,
            "writes": False,
            "automatic_execution": False,
            "changes_recommendation_behavior": False,
            "changes_committee_behavior": False,
            "changes_scheduler_behavior": False,
            "changes_trading_behavior": False,
        }
