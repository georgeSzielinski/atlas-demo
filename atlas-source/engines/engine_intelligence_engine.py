"""Read-only outcome association analytics for stored evidence engines."""

from datetime import datetime

from engines.learning_intelligence_metrics import group_metrics, normalize_records, subset


class EngineIntelligenceEngine:
    VERSION = "engine-intelligence-v1"
    TRUNCATION_WARNING = (
        "Source projection was truncated; engine analytics may be incomplete."
    )
    ASSOCIATION_NOTICE = (
        "Metrics describe outcomes of recommendations carrying stored engine evidence; "
        "they do not prove causal or independent engine performance."
    )

    def report(
        self,
        ticker=None,
        engine=None,
        committee=None,
        sector=None,
        regime=None,
        horizon=None,
        evaluation_source="paper",
        rolling_window=20,
        limit=10000,
        source_loader=None,
        source=None,
        now=None,
    ):
        source = source or (source_loader or self._source)(
            ticker=ticker,
            sector=sector,
            regime=regime,
            horizon=horizon,
            evaluation_source=evaluation_source,
            limit=limit,
        )
        dataset = normalize_records(list(source.get("records") or []))
        if committee:
            committee_key = str(committee).strip().lower()
            dataset = subset(dataset, [
                row["recommendation_id"]
                for row in dataset["recommendations"]
                if any(name.lower() == committee_key for name in row["committee_names"])
            ])
        names = sorted({
            name
            for recommendation in dataset["recommendations"]
            for name in recommendation["engine_names"]
        })
        if engine:
            needle = str(engine).strip().lower()
            names = [name for name in names if name.lower() == needle]

        engines = []
        for name in names:
            ids = [
                row["recommendation_id"]
                for row in dataset["recommendations"]
                if name in row["engine_names"]
            ]
            engine_dataset = subset(dataset, ids)
            confidence_available = sum(
                row.get("engine_confidence", {}).get(name) is not None
                for row in engine_dataset["recommendations"]
            )
            engines.append({
                "engine": name,
                **group_metrics(
                    engine_dataset,
                    rolling_window=rolling_window,
                    confidence_key=name,
                ),
                "engine_confidence_coverage": (
                    None if not engine_dataset["recommendations"] else
                    round(
                        confidence_available / len(engine_dataset["recommendations"]) * 100,
                        2,
                    )
                ),
            })

        truncated = bool(source.get("truncated"))
        return {
            "generated_at": self._moment(now).isoformat(),
            "version": self.VERSION,
            "status": "EVALUATED" if engines else "NOT_EVALUATED",
            "reason": None if engines else (
                "No stored engine evidence matched the selectors."
            ),
            "engines": engines,
            "leaderboard": self._leaderboard(engines),
            "selectors": {
                **(source.get("filters") or {}),
                "engine": engine,
                "committee": committee,
                "rolling_window": max(1, min(int(rolling_window), 500)),
            },
            "data": {
                "analyzed_row_count": len(source.get("records") or []),
                "source_total_row_count": source.get("total", 0),
                "limit": source.get("limit"),
                "truncated": truncated,
                "warning": self.TRUNCATION_WARNING if truncated else None,
                "relationship_scope": "stored_recommendation_evidence_association",
                "association_notice": self.ASSOCIATION_NOTICE,
                "accuracy_scope": "recommendation_horizon_evaluations",
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
                "engine_count": 0,
                "truncated": False,
                "warning": None,
                "policy": self.policy(),
            }
        return {
            "status": report["status"],
            "reason": report["reason"],
            "engine_count": len(report["engines"]),
            "truncated": report["data"]["truncated"],
            "analyzed_row_count": report["data"]["analyzed_row_count"],
            "source_total_row_count": report["data"]["source_total_row_count"],
            "warning": report["data"]["warning"],
            "association_notice": self.ASSOCIATION_NOTICE,
            "policy": self.policy(),
        }

    def _leaderboard(self, engines):
        return sorted(
            engines,
            key=lambda row: (
                row["accuracy"] is not None,
                row["accuracy"] if row["accuracy"] is not None else -1,
                row["accuracy_sample_size"],
                row["engine"],
            ),
            reverse=True,
        )

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
            "causal_attribution": False,
            "changes_recommendation_behavior": False,
            "changes_trading_behavior": False,
        }
