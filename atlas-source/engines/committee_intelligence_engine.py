"""Read-only outcome analytics for provable persisted committee context."""

from datetime import datetime

from engines.learning_intelligence_metrics import group_metrics, normalize_records, subset


class CommitteeIntelligenceEngine:
    VERSION = "committee-intelligence-v1"
    TRUNCATION_WARNING = (
        "Source projection was truncated; committee analytics may be incomplete."
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
        if engine:
            engine_key = str(engine).strip().lower()
            dataset = subset(dataset, [
                row["recommendation_id"]
                for row in dataset["recommendations"]
                if any(name.lower() == engine_key for name in row["engine_names"])
            ])
        names = sorted({
            name
            for recommendation in dataset["recommendations"]
            for name in recommendation["committee_names"]
        })
        if committee:
            needle = str(committee).strip().lower()
            names = [name for name in names if name.lower() == needle]

        committees = []
        for name in names:
            ids = [
                row["recommendation_id"]
                for row in dataset["recommendations"]
                if name in row["committee_names"]
            ]
            committees.append({
                "committee": name,
                **group_metrics(
                    subset(dataset, ids), rolling_window=rolling_window
                ),
            })

        truncated = bool(source.get("truncated"))
        return {
            "generated_at": self._moment(now).isoformat(),
            "version": self.VERSION,
            "status": "EVALUATED" if committees else "NOT_EVALUATED",
            "reason": None if committees else (
                "No persisted committee relationship matched the selectors."
            ),
            "committees": committees,
            "leaderboard": self._leaderboard(committees),
            "selectors": {
                **(source.get("filters") or {}),
                "committee": committee,
                "engine": engine,
                "rolling_window": max(1, min(int(rolling_window), 500)),
            },
            "data": {
                "analyzed_row_count": len(source.get("records") or []),
                "source_total_row_count": source.get("total", 0),
                "limit": source.get("limit"),
                "truncated": truncated,
                "warning": self.TRUNCATION_WARNING if truncated else None,
                "relationship_scope": "persisted_recommendation_committee_context",
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
                "committee_count": 0,
                "truncated": False,
                "warning": None,
                "policy": self.policy(),
            }
        return {
            "status": report["status"],
            "reason": report["reason"],
            "committee_count": len(report["committees"]),
            "truncated": report["data"]["truncated"],
            "analyzed_row_count": report["data"]["analyzed_row_count"],
            "source_total_row_count": report["data"]["source_total_row_count"],
            "warning": report["data"]["warning"],
            "policy": self.policy(),
        }

    def _leaderboard(self, committees):
        return sorted(
            committees,
            key=lambda row: (
                row["accuracy"] is not None,
                row["accuracy"] if row["accuracy"] is not None else -1,
                row["accuracy_sample_size"],
                row["committee"],
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
            "changes_recommendation_behavior": False,
            "changes_trading_behavior": False,
        }
