import hashlib
from datetime import datetime

from engines.research_engine import ResearchEngine
from engines.scientific_validation_engine import ScientificValidationEngine
from engines.simulation_arena import SimulationArena


class ResearchLabEngine:
    """Atlas Research Laboratory.

    Deterministic, read-only orchestration layer that manages the experiment
    registry and reuses existing Atlas research systems (Simulation Arena and
    Scientific Validation) to evaluate every proposed improvement. No experiment
    may automatically change Atlas behavior; adoption always requires human
    approval.
    """

    EXPERIMENT_STATES = [
        "PROPOSED",
        "IMPLEMENTING",
        "READY_FOR_TEST",
        "RUNNING",
        "VALIDATING",
        "ADOPTED",
        "REJECTED",
        "ARCHIVED",
    ]
    ACTIVE_STATES = {"IMPLEMENTING", "READY_FOR_TEST", "RUNNING", "VALIDATING"}
    WAITING_STATES = {"PROPOSED", "IMPLEMENTING", "READY_FOR_TEST"}
    COMPLETED_STATES = {"ADOPTED", "REJECTED", "ARCHIVED"}
    PRIORITIES = ["High", "Medium", "Low"]
    # Metrics stored for every experiment executed inside Simulation Arena.
    ARENA_METRICS = [
        "sharpe",
        "sortino",
        "win_rate",
        "average_return",
        "drawdown",
        "trade_frequency",
        "holding_period",
        "alpha",
        "probability_calibration",
        "knowledge_score",
        "stability_score",
    ]
    LOWER_IS_BETTER = {"drawdown"}
    VALIDATION_STATES = [
        "Improved",
        "Neutral",
        "Regression",
        "Not Enough Evidence",
    ]
    DEFAULT_ROADMAP = {
        "High": ["Improve probability calibration."],
        "Medium": ["Study macro weighting."],
        "Low": ["Alternative technical indicators."],
    }

    def __init__(
        self,
        scientific_validation=None,
        simulation_arena=None,
        research_engine=None,
    ):
        self.scientific_validation = (
            scientific_validation or ScientificValidationEngine()
        )
        self.simulation_arena = simulation_arena or SimulationArena()
        self.research_engine = research_engine or ResearchEngine()

    # ------------------------------------------------------------------
    # Part 1 - Experiment Registry
    # ------------------------------------------------------------------
    def create_experiment(
        self,
        title,
        description,
        feature_being_tested,
        baseline_strategy,
        candidate_strategy,
        author="Atlas Research",
        priority="Medium",
        status="PROPOSED",
        validation_state="Not Enough Evidence",
        notes="",
        created_date=None,
    ):
        date = created_date or datetime.now().isoformat()
        status = status if status in self.EXPERIMENT_STATES else "PROPOSED"
        priority = priority if priority in self.PRIORITIES else "Medium"
        if validation_state not in self.VALIDATION_STATES:
            validation_state = "Not Enough Evidence"

        return {
            "experiment_id": self.generate_experiment_id(
                title,
                feature_being_tested,
                date,
            ),
            "title": title,
            "description": description,
            "status": status,
            "created_date": date,
            "author": author,
            "feature_being_tested": feature_being_tested,
            "baseline_strategy": baseline_strategy,
            "candidate_strategy": candidate_strategy,
            "validation_state": validation_state,
            "notes": notes,
            "priority": priority,
            "arena_metrics": {},
            "adoption_decision": "RETEST",
            "policy": self.policy(),
        }

    def generate_experiment_id(self, title, feature, date):
        seed = f"{title}|{feature}|{date}"
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]

        return f"exp-{digest}"

    def persist_experiment(self, experiment):
        from database.repository import save_registry_experiment

        save_registry_experiment(experiment)

    # ------------------------------------------------------------------
    # Part 3 + Part 4 - Simulation + Scientific Validation
    # ------------------------------------------------------------------
    def run_experiment(
        self,
        experiment,
        dataset="atlas-core",
        tickers=None,
        date_range=None,
        validation_window=30,
        historical_data=None,
        run_date=None,
    ):
        """Execute an experiment inside Simulation Arena and validate it.

        Reuses SimulationArena for deterministic metrics and
        ScientificValidationEngine for the adoption decision. Nothing here
        changes Atlas behavior.
        """
        tickers = tickers or ["AAPL", "MSFT", "GOOGL", "AMZN"]
        date_range = date_range or {"start": "2026-01-01", "end": "2026-06-30"}
        arena = self.simulation_arena.run(
            dataset=dataset,
            tickers=tickers,
            date_range=date_range,
            validation_window=validation_window,
            historical_data=historical_data,
            run_date=run_date,
        )
        baseline_result = self._arena_strategy(
            arena,
            experiment.get("baseline_strategy"),
            "Current Atlas",
        )
        candidate_result = self._arena_strategy(
            arena,
            experiment.get("candidate_strategy"),
            arena["comparison"]["best_overall"],
        )
        baseline_metrics = self._lab_metrics(baseline_result["metrics"])
        candidate_metrics = self._lab_metrics(
            candidate_result["metrics"],
            baseline_average_return=baseline_result["metrics"].get(
                "average_return",
                0,
            ),
        )
        sample_size = candidate_result.get("sample_size", 0)
        validation = self.validate_experiment(
            experiment,
            baseline_result["metrics"],
            candidate_result["metrics"],
            sample_size,
            experiment_date=run_date,
        )
        comparison = self.compare_metrics(baseline_metrics, candidate_metrics)
        updated = dict(experiment)
        updated.update({
            "status": "VALIDATING",
            "validation_state": validation["scientific_result"],
            "adoption_decision": validation["adoption_decision"],
            "arena_metrics": {
                "baseline": baseline_metrics,
                "candidate": candidate_metrics,
            },
        })

        return {
            "experiment": updated,
            "arena_id": arena["arena_id"],
            "baseline_strategy": baseline_result["strategy_name"],
            "candidate_strategy": candidate_result["strategy_name"],
            "baseline_metrics": baseline_metrics,
            "candidate_metrics": candidate_metrics,
            "sample_size": sample_size,
            "comparison": comparison,
            "validation": validation,
            "policy": self.policy(),
        }

    def validate_experiment(
        self,
        experiment,
        baseline_metrics,
        candidate_metrics,
        sample_size,
        experiment_date=None,
    ):
        regimes = {
            regime: {"status": "Neutral", "sample_size": sample_size}
            for regime in ScientificValidationEngine.REGIMES
        }
        generalization = {
            test: {"status": "Neutral", "sample_size": sample_size}
            for test in ScientificValidationEngine.GENERALIZATION_TESTS
        }

        return self.scientific_validation.evaluate(
            experiment_id=experiment.get("experiment_id"),
            experiment_date=experiment_date,
            feature_tested=experiment.get(
                "feature_being_tested",
                experiment.get("title", ""),
            ),
            baseline=baseline_metrics,
            candidate=candidate_metrics,
            sample_size=sample_size,
            regimes=regimes,
            generalization=generalization,
        )

    # ------------------------------------------------------------------
    # Part 7 - Experiment Comparison
    # ------------------------------------------------------------------
    def compare_metrics(self, baseline, candidate):
        rows = []

        for metric in self.ARENA_METRICS:
            baseline_value = baseline.get(metric, 0)
            candidate_value = candidate.get(metric, 0)

            if metric in self.LOWER_IS_BETTER:
                difference = round(
                    abs(baseline_value) - abs(candidate_value),
                    2,
                )
            else:
                difference = round(candidate_value - baseline_value, 2)

            rows.append({
                "metric": metric,
                "baseline": baseline_value,
                "candidate": candidate_value,
                "difference": difference,
                "improved": difference > 0,
            })

        return {
            "rows": rows,
            "improvements": [
                row["metric"] for row in rows if row["improved"]
            ],
            "regressions": [
                row["metric"] for row in rows if row["difference"] < 0
            ],
        }

    def compare_experiment(self, experiment):
        arena_metrics = experiment.get("arena_metrics", {}) or {}
        baseline = arena_metrics.get("baseline", {})
        candidate = arena_metrics.get("candidate", {})

        return self.compare_metrics(baseline, candidate)

    # ------------------------------------------------------------------
    # Part 2 - Experiment Queue
    # ------------------------------------------------------------------
    def build_queue(self, experiments):
        open_experiments = [
            item for item in experiments
            if item.get("status") not in self.COMPLETED_STATES
        ]
        running = [
            item for item in experiments
            if item.get("status") == "RUNNING"
        ]
        waiting = [
            item for item in experiments
            if item.get("status") in self.WAITING_STATES
        ]
        completed = [
            item for item in experiments
            if item.get("status") in self.COMPLETED_STATES
        ]

        return {
            "highest_priority": self._priority_sorted(open_experiments)[:5],
            "waiting": self._priority_sorted(waiting),
            "running": self._by_date(running, reverse=True),
            "recently_completed": self._by_date(completed, reverse=True)[:5],
        }

    # ------------------------------------------------------------------
    # Part 5 - Research Timeline
    # ------------------------------------------------------------------
    def build_timeline(self, experiments):
        return {
            "planned": self._by_date([
                item for item in experiments
                if item.get("status")
                in {"PROPOSED", "IMPLEMENTING", "READY_FOR_TEST"}
            ]),
            "active": self._by_date([
                item for item in experiments
                if item.get("status") in {"RUNNING", "VALIDATING"}
            ]),
            "completed": self._by_date([
                item for item in experiments
                if item.get("status") in {"ADOPTED", "ARCHIVED"}
            ], reverse=True),
            "rejected": self._by_date([
                item for item in experiments
                if item.get("status") == "REJECTED"
            ], reverse=True),
        }

    # ------------------------------------------------------------------
    # Part 6 - Research Roadmap
    # ------------------------------------------------------------------
    def build_roadmap(self, experiments=None):
        experiments = experiments or []
        roadmap = {level: [] for level in self.PRIORITIES}

        for experiment in self._priority_sorted(experiments):
            if experiment.get("status") in self.COMPLETED_STATES:
                continue

            priority = experiment.get("priority", "Medium")
            roadmap.setdefault(priority, []).append({
                "experiment_id": experiment.get("experiment_id"),
                "title": experiment.get("title"),
                "feature_being_tested": experiment.get("feature_being_tested"),
                "status": experiment.get("status"),
                "priority": priority,
            })

        for level, defaults in self.DEFAULT_ROADMAP.items():
            if not roadmap.get(level):
                roadmap[level] = [
                    {
                        "experiment_id": None,
                        "title": item,
                        "feature_being_tested": item,
                        "status": "PROPOSED",
                        "priority": level,
                    }
                    for item in defaults
                ]

        return roadmap

    # ------------------------------------------------------------------
    # Part 8 - History
    # ------------------------------------------------------------------
    def build_history(self, experiments):
        return {
            "experiments": self._by_date(experiments, reverse=True),
            "features": sorted({
                item.get("feature_being_tested")
                for item in experiments
                if item.get("feature_being_tested")
            }),
            "statuses": sorted({
                item.get("status")
                for item in experiments
                if item.get("status")
            }),
            "results": sorted({
                item.get("validation_state")
                for item in experiments
                if item.get("validation_state")
            }),
        }

    def search_history(
        self,
        experiments,
        feature=None,
        regime=None,
        date=None,
        result=None,
        status=None,
    ):
        rows = list(experiments)

        if feature:
            rows = [
                item for item in rows
                if feature.lower()
                in str(item.get("feature_being_tested", "")).lower()
            ]

        if regime:
            rows = [
                item for item in rows
                if regime.lower() in str(item.get("notes", "")).lower()
                or regime.lower()
                in str(item.get("candidate_strategy", "")).lower()
            ]

        if date:
            rows = [
                item for item in rows
                if str(item.get("created_date", "")).startswith(date)
            ]

        if result:
            rows = [
                item for item in rows
                if item.get("validation_state") == result
            ]

        if status:
            rows = [item for item in rows if item.get("status") == status]

        return self._by_date(rows, reverse=True)

    # ------------------------------------------------------------------
    # Part 9 - Operations
    # ------------------------------------------------------------------
    def operations_summary(self, experiments, latest_validation=None):
        active = [
            item for item in experiments
            if item.get("status") in self.ACTIVE_STATES
        ]
        completed = [
            item for item in experiments
            if item.get("status") in self.COMPLETED_STATES
        ]
        adopted = [
            item for item in experiments
            if item.get("status") == "ADOPTED"
        ]
        total = len(experiments)
        latest_validation = latest_validation or {}

        return {
            "active_experiment_count": len(active),
            "active_experiments": self._by_date(active, reverse=True)[:5],
            "latest_validation": latest_validation or None,
            "latest_adoption_decision": latest_validation.get(
                "adoption_decision",
                "Not Enough Evidence",
            ),
            "research_progress": {
                "total_experiments": total,
                "completed": len(completed),
                "adopted": len(adopted),
                "completion_rate": self._rate(len(completed), total),
                "adoption_rate": self._rate(len(adopted), total),
                "state_distribution": self._distribution(experiments),
            },
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Dashboard assembly
    # ------------------------------------------------------------------
    def laboratory_dashboard(
        self,
        experiments=None,
        latest_validation=None,
        latest_arena=None,
    ):
        if experiments is None:
            from database.repository import get_registry_experiments

            experiments = get_registry_experiments(limit=200)

        if not experiments:
            experiments = self.default_experiments()

        if latest_validation is None:
            from database.repository import get_scientific_validation_reports

            reports = get_scientific_validation_reports(limit=1)
            latest_validation = reports[0] if reports else None

        if latest_arena is None:
            from database.repository import get_simulation_arena_runs

            runs = get_simulation_arena_runs(limit=1)
            latest_arena = runs[0] if runs else None

        return {
            "experiments": experiments,
            "experiment_count": len(experiments),
            "experiment_states": self.EXPERIMENT_STATES,
            "queue": self.build_queue(experiments),
            "timeline": self.build_timeline(experiments),
            "roadmap": self.build_roadmap(experiments),
            "history": self.build_history(experiments),
            "latest_validation": latest_validation,
            "latest_arena": latest_arena,
            "operations_summary": self.operations_summary(
                experiments,
                latest_validation,
            ),
            "policy": self.policy(),
        }

    def learning_metrics(self, experiments=None, validations=None):
        """Deterministic learning-curve inputs for Performance Analytics.

        Read-only. Reuses the registry and scientific validation reports to
        report how much Atlas is adopting and completing research over time.
        """
        if experiments is None:
            from database.repository import get_registry_experiments

            experiments = get_registry_experiments(limit=200)

        if not experiments:
            experiments = self.default_experiments()

        if validations is None:
            from database.repository import get_scientific_validation_reports

            validations = get_scientific_validation_reports(limit=200)

        validations = validations or []
        completed = [
            item for item in experiments
            if item.get("status") in self.COMPLETED_STATES
        ]
        adopted = [
            item for item in experiments
            if item.get("status") == "ADOPTED"
        ]
        validation_success = [
            item for item in validations
            if item.get("adoption_decision") == "ADOPT"
            or item.get("scientific_result") == "Improved"
        ]

        return {
            "experiment_count": len(experiments),
            "experiment_adoption_rate": self._rate(len(adopted), len(experiments)),
            "research_completion_rate": self._rate(
                len(completed),
                len(experiments),
            ),
            "scientific_validation_success_rate": self._rate(
                len(validation_success),
                len(validations),
            ),
        }

    def active_experiments(self, experiments=None):
        if experiments is None:
            from database.repository import get_registry_experiments

            experiments = get_registry_experiments(limit=200)

        if not experiments:
            experiments = self.default_experiments()

        return self._by_date([
            item for item in experiments
            if item.get("status") in self.ACTIVE_STATES
        ], reverse=True)

    def policy(self):
        return {
            "read_only": True,
            "deterministic": True,
            "research_only": True,
            "paper_trading_only": True,
            "changes_recommendation_behavior": False,
            "automatic_adoption": False,
            "automatic_execution": False,
            "broker_integration": False,
            "human_approval_required": True,
        }

    # ------------------------------------------------------------------
    # Deterministic empty-state examples
    # ------------------------------------------------------------------
    def default_experiments(self):
        specs = [
            {
                "title": "Probability calibration refinement",
                "description": (
                    "Test whether a recalibrated probability curve improves "
                    "calibration without regressing win rate."
                ),
                "feature_being_tested": "Probability calibration",
                "baseline_strategy": "Current Atlas",
                "candidate_strategy": "Recalibrated probability curve",
                "priority": "High",
                "status": "VALIDATING",
                "validation_state": "Improved",
                "created_date": "2026-06-20T09:00:00",
                "notes": "Bull and Sideways regimes.",
                "baseline": {
                    "sharpe": 0.82,
                    "win_rate": 55,
                    "average_return": 1.2,
                    "drawdown": -8,
                    "probability_calibration": 70,
                    "knowledge_score": 78,
                    "stability_score": 80,
                    "trade_frequency": 5,
                    "holding_period": 30,
                },
                "candidate": {
                    "sharpe": 1.05,
                    "win_rate": 61,
                    "average_return": 2.1,
                    "drawdown": -6,
                    "probability_calibration": 79,
                    "knowledge_score": 82,
                    "stability_score": 83,
                    "trade_frequency": 5,
                    "holding_period": 31,
                },
                "adoption_decision": "ADOPT",
            },
            {
                "title": "Macro weighting study",
                "description": (
                    "Study whether macro regime weighting adds measurable "
                    "alpha across rate regimes."
                ),
                "feature_being_tested": "Macro weighting",
                "baseline_strategy": "Current Atlas",
                "candidate_strategy": "Macro-weighted evidence",
                "priority": "Medium",
                "status": "RUNNING",
                "validation_state": "Not Enough Evidence",
                "created_date": "2026-06-24T09:00:00",
                "notes": "Rising Rates and Falling Rates regimes.",
                "baseline": {},
                "candidate": {},
                "adoption_decision": "RETEST",
            },
            {
                "title": "Alternative technical indicators",
                "description": (
                    "Compare an alternative technical indicator set against "
                    "the current technical evidence source."
                ),
                "feature_being_tested": "Technical indicators",
                "baseline_strategy": "Current Atlas",
                "candidate_strategy": "Alternative technical set",
                "priority": "Low",
                "status": "PROPOSED",
                "validation_state": "Not Enough Evidence",
                "created_date": "2026-06-27T09:00:00",
                "notes": "High Volatility regime.",
                "baseline": {},
                "candidate": {},
                "adoption_decision": "RETEST",
            },
            {
                "title": "News sentiment provider swap",
                "description": (
                    "Evaluate a candidate news sentiment provider for "
                    "recommendation accuracy."
                ),
                "feature_being_tested": "News sentiment",
                "baseline_strategy": "Current Atlas",
                "candidate_strategy": "Candidate news provider",
                "priority": "Medium",
                "status": "REJECTED",
                "validation_state": "Regression",
                "created_date": "2026-06-10T09:00:00",
                "notes": "Bear regime regression observed.",
                "baseline": {
                    "sharpe": 0.82,
                    "win_rate": 55,
                    "average_return": 1.2,
                    "drawdown": -8,
                    "probability_calibration": 70,
                    "knowledge_score": 78,
                    "stability_score": 80,
                    "trade_frequency": 5,
                    "holding_period": 30,
                },
                "candidate": {
                    "sharpe": 0.6,
                    "win_rate": 49,
                    "average_return": 0.4,
                    "drawdown": -12,
                    "probability_calibration": 64,
                    "knowledge_score": 74,
                    "stability_score": 72,
                    "trade_frequency": 6,
                    "holding_period": 28,
                },
                "adoption_decision": "REJECT",
            },
            {
                "title": "Committee agreement threshold study",
                "description": (
                    "Measure whether a higher committee agreement threshold "
                    "improves validated accuracy."
                ),
                "feature_being_tested": "Committee threshold",
                "baseline_strategy": "Current Atlas",
                "candidate_strategy": "Higher agreement threshold",
                "priority": "Medium",
                "status": "READY_FOR_TEST",
                "validation_state": "Not Enough Evidence",
                "created_date": "2026-06-26T09:00:00",
                "notes": "Bull regime.",
                "baseline": {},
                "candidate": {},
                "adoption_decision": "RETEST",
            },
            {
                "title": "Forecast provider benchmark",
                "description": (
                    "Benchmark a candidate forecast provider against the "
                    "current forecast evidence source."
                ),
                "feature_being_tested": "Forecast provider",
                "baseline_strategy": "Current Atlas",
                "candidate_strategy": "Candidate forecast provider",
                "priority": "High",
                "status": "ADOPTED",
                "validation_state": "Improved",
                "created_date": "2026-06-05T09:00:00",
                "notes": "Improved across Bull and Low Volatility regimes.",
                "baseline": {
                    "sharpe": 0.8,
                    "win_rate": 54,
                    "average_return": 1.1,
                    "drawdown": -9,
                    "probability_calibration": 69,
                    "knowledge_score": 77,
                    "stability_score": 79,
                    "trade_frequency": 5,
                    "holding_period": 29,
                },
                "candidate": {
                    "sharpe": 1.1,
                    "win_rate": 62,
                    "average_return": 2.3,
                    "drawdown": -6,
                    "probability_calibration": 80,
                    "knowledge_score": 84,
                    "stability_score": 85,
                    "trade_frequency": 5,
                    "holding_period": 30,
                },
                "adoption_decision": "ADOPT",
            },
        ]

        experiments = []
        for spec in specs:
            experiment = self.create_experiment(
                title=spec["title"],
                description=spec["description"],
                feature_being_tested=spec["feature_being_tested"],
                baseline_strategy=spec["baseline_strategy"],
                candidate_strategy=spec["candidate_strategy"],
                author="Atlas Research",
                priority=spec["priority"],
                status=spec["status"],
                validation_state=spec["validation_state"],
                notes=spec["notes"],
                created_date=spec["created_date"],
            )
            experiment["adoption_decision"] = spec["adoption_decision"]

            if spec["baseline"] and spec["candidate"]:
                baseline_metrics = self._lab_metrics(spec["baseline"])
                candidate_metrics = self._lab_metrics(
                    spec["candidate"],
                    baseline_average_return=spec["baseline"].get(
                        "average_return",
                        0,
                    ),
                )
                experiment["arena_metrics"] = {
                    "baseline": baseline_metrics,
                    "candidate": candidate_metrics,
                }

            experiment["is_example"] = True
            experiments.append(experiment)

        return experiments

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _arena_strategy(self, arena, name, fallback):
        results = arena.get("results", [])

        if name:
            match = next(
                (
                    item for item in results
                    if item.get("strategy_name") == name
                ),
                None,
            )
            if match is not None:
                return match

        match = next(
            (
                item for item in results
                if item.get("strategy_name") == fallback
            ),
            None,
        )
        if match is not None:
            return match

        return results[0] if results else {"strategy_name": fallback, "metrics": {}, "sample_size": 0}

    def _lab_metrics(self, metrics, baseline_average_return=None):
        metrics = metrics or {}
        average_return = round(metrics.get("average_return", 0), 2)
        sharpe = round(metrics.get("sharpe_ratio", metrics.get("sharpe", 0)), 2)

        if baseline_average_return is None:
            alpha = 0
        else:
            alpha = round(average_return - baseline_average_return, 2)

        return {
            "sharpe": sharpe,
            "sortino": round(sharpe * 1.15, 2),
            "win_rate": metrics.get("win_rate", 0),
            "average_return": average_return,
            "drawdown": metrics.get("max_drawdown", metrics.get("drawdown", 0)),
            "trade_frequency": metrics.get("trade_frequency", 0),
            "holding_period": metrics.get(
                "average_holding_period",
                metrics.get("holding_period", 0),
            ),
            "alpha": alpha,
            "probability_calibration": metrics.get(
                "probability_calibration",
                0,
            ),
            "knowledge_score": metrics.get("knowledge_score", 0),
            "stability_score": metrics.get("stability_score", 0),
        }

    def _priority_sorted(self, experiments):
        def key(item):
            priority = item.get("priority", "Medium")
            rank = (
                self.PRIORITIES.index(priority)
                if priority in self.PRIORITIES
                else len(self.PRIORITIES)
            )

            return (rank, item.get("created_date", ""), item.get("title", ""))

        return sorted(experiments, key=key)

    def _by_date(self, experiments, reverse=False):
        return sorted(
            experiments,
            key=lambda item: (
                item.get("created_date", ""),
                item.get("title", ""),
            ),
            reverse=reverse,
        )

    def _distribution(self, experiments):
        counts = {}

        for item in experiments:
            status = item.get("status", "PROPOSED")
            counts[status] = counts.get(status, 0) + 1

        return counts

    def _rate(self, numerator, denominator):
        if denominator == 0:
            return 0

        return round(numerator / denominator * 100, 2)
