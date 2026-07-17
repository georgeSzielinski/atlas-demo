import hashlib
import json
from datetime import datetime

from engines.historical_runner import HistoricalRunner
from engines.scientific_validation_engine import ScientificValidationEngine


class SimulationArena:
    STRATEGY_CONFIGS = [
        {
            "name": "Current Atlas",
            "toggles": {},
            "candidate_placeholder": False,
        },
        {
            "name": "No News",
            "toggles": {"use_news": False},
            "candidate_placeholder": False,
        },
        {
            "name": "No Forecast",
            "toggles": {"use_forecast": False},
            "candidate_placeholder": False,
        },
        {
            "name": "No SEC",
            "toggles": {"use_sec": False},
            "candidate_placeholder": False,
        },
        {
            "name": "No Macro",
            "toggles": {"use_macro": False},
            "candidate_placeholder": False,
        },
        {
            "name": "No Catalysts",
            "toggles": {"use_catalysts": False},
            "candidate_placeholder": False,
        },
        {
            "name": "No Committee",
            "toggles": {"use_committee": False},
            "candidate_placeholder": False,
        },
        {
            "name": "No Executive Review",
            "toggles": {"use_executive_review": False},
            "candidate_placeholder": False,
        },
        {
            "name": "No Probability",
            "toggles": {"use_probability": False},
            "candidate_placeholder": False,
        },
        {
            "name": "Candidate Model Placeholder",
            "toggles": {"use_candidate_model": True},
            "candidate_placeholder": True,
        },
    ]

    def __init__(self, historical_runner=None):
        self.historical_runner = historical_runner or HistoricalRunner()
        self.scientific_validation = ScientificValidationEngine()

    def run(
        self,
        dataset,
        tickers,
        date_range,
        validation_window=30,
        historical_data=None,
        strategy_configs=None,
        run_date=None,
        persist=False,
    ):
        date = run_date or datetime.now().isoformat()
        strategies = strategy_configs or self.STRATEGY_CONFIGS
        base_config = {
            "tickers": sorted(tickers),
            "start_date": date_range.get("start", ""),
            "end_date": date_range.get("end", ""),
            "validation_window": validation_window,
        }
        results = [
            self._strategy_result(
                strategy,
                base_config,
                historical_data,
            )
            for strategy in strategies
        ]
        comparison = self.compare_strategies(results)
        scientific_validation = self._scientific_validation(
            comparison,
            results,
            date,
        )
        arena = {
            "arena_id": self.arena_id(
                dataset,
                tickers,
                date_range,
                validation_window,
                strategies,
            ),
            "date": date,
            "dataset": dataset,
            "tickers": sorted(tickers),
            "date_range": date_range,
            "validation_window": validation_window,
            "strategy_configs": strategies,
            "market_regimes_tested": self._market_regimes(results),
            "results": results,
            "comparison": comparison,
            "scientific_validation": scientific_validation,
            "policy": self.policy(),
        }

        if persist:
            self.persist_run(arena)

        return arena

    def compare_strategies(self, results):
        ranked = sorted(
            results,
            key=lambda item: (
                item["overall_score"],
                item["metrics"]["win_rate"],
                item["metrics"]["average_return"],
                item["strategy_name"],
            ),
            reverse=True,
        )
        recommended = [
            item for item in ranked
            if item["recommendation"] != "Not recommended"
        ]
        not_recommended = [
            item["strategy_name"] for item in sorted(
                results,
                key=lambda item: item["strategy_name"],
            )
            if item["recommendation"] == "Not recommended"
        ]

        return {
            "best_overall": self._name(ranked),
            "best_risk_adjusted": self._name(sorted(
                recommended,
                key=lambda item: (
                    item["metrics"]["sharpe_ratio"],
                    item["overall_score"],
                    item["strategy_name"],
                ),
                reverse=True,
            )),
            "best_low_drawdown": self._name(sorted(
                recommended,
                key=lambda item: (
                    item["metrics"]["max_drawdown"],
                    item["overall_score"],
                    item["strategy_name"],
                ),
                reverse=True,
            )),
            "most_stable": self._name(sorted(
                recommended,
                key=lambda item: (
                    item["metrics"]["stability_score"],
                    item["overall_score"],
                    item["strategy_name"],
                ),
                reverse=True,
            )),
            "most_knowledgeable": self._name(sorted(
                recommended,
                key=lambda item: (
                    item["metrics"]["knowledge_score"],
                    item["overall_score"],
                    item["strategy_name"],
                ),
                reverse=True,
            )),
            "not_recommended": not_recommended,
            "ordered": ranked,
        }

    def persist_run(self, arena):
        from database.repository import (
            save_scientific_validation_report,
            save_simulation_arena_run,
        )

        save_simulation_arena_run(arena)

        if arena.get("scientific_validation"):
            save_scientific_validation_report(arena["scientific_validation"])

    def policy(self):
        return {
            "read_only": True,
            "deterministic": True,
            "research_only": True,
            "changes_recommendation_behavior": False,
            "automatic_execution": False,
            "broker_integration": False,
        }

    def arena_id(self, dataset, tickers, date_range, validation_window, strategies):
        seed = json.dumps(
            {
                "dataset": dataset,
                "tickers": sorted(tickers),
                "date_range": date_range,
                "validation_window": validation_window,
                "strategies": strategies,
            },
            sort_keys=True,
        )
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]

        return f"arena-{digest}"

    def _strategy_result(self, strategy, base_config, historical_data):
        config = dict(base_config)
        config.update(strategy.get("toggles", {}))
        replay = self.historical_runner.replay_configuration(
            config,
            historical_data=historical_data,
        )
        metrics = self._arena_metrics(replay, config, strategy)
        overall_score = self._overall_score(metrics, strategy)

        return {
            "strategy_name": strategy["name"],
            "disabled_subsystems": replay["disabled_subsystems"],
            "candidate_placeholder": strategy.get(
                "candidate_placeholder",
                False,
            ),
            "market_regimes_tested": replay["market_regimes_tested"],
            "sample_size": len(replay["validations"]),
            "metrics": metrics,
            "overall_score": overall_score,
            "recommendation": self._strategy_recommendation(
                metrics,
                strategy,
            ),
            "notes": self._strategy_notes(strategy),
        }

    def _arena_metrics(self, replay, config, strategy):
        metrics = replay["metrics"]
        records = replay["recommendations"]
        disabled = set(replay["disabled_subsystems"])
        confidence_penalty = len(disabled) * 2
        placeholder_penalty = 10 if strategy.get("candidate_placeholder") else 0

        return {
            "win_rate": metrics["win_rate"],
            "average_return": metrics["average_return"],
            "sharpe_ratio": metrics["sharpe_ratio"],
            "max_drawdown": metrics["maximum_drawdown"],
            "probability_calibration": max(
                0,
                metrics["confidence_calibration"] - confidence_penalty,
            ),
            "recommendation_accuracy": metrics["recommendation_accuracy"],
            "trade_frequency": self._trade_frequency(replay),
            "average_holding_period": metrics["average_holding_period"],
            "stability_score": max(
                0,
                self._average([
                    item.get("stability_score", 0) for item in records
                ]) or (82 - len(disabled) * 5 - placeholder_penalty),
            ),
            "knowledge_score": max(
                0,
                self._average([
                    item.get("knowledge_score", 0) for item in records
                ]) or (80 - len(disabled) * 6 - placeholder_penalty),
            ),
        }

    def _overall_score(self, metrics, strategy):
        placeholder_penalty = 15 if strategy.get("candidate_placeholder") else 0
        drawdown_score = max(0, 100 + metrics["max_drawdown"])
        score = (
            metrics["win_rate"] * 0.2
            + metrics["average_return"] * 2
            + metrics["sharpe_ratio"] * 8
            + drawdown_score * 0.1
            + metrics["probability_calibration"] * 0.1
            + metrics["recommendation_accuracy"] * 0.15
            + metrics["stability_score"] * 0.15
            + metrics["knowledge_score"] * 0.1
            - placeholder_penalty
        )

        return round(score, 2)

    def _strategy_recommendation(self, metrics, strategy):
        if strategy.get("candidate_placeholder"):
            return "Not recommended"

        if metrics["win_rate"] < 45 or metrics["average_return"] < 0:
            return "Not recommended"

        if metrics["stability_score"] < 45 or metrics["knowledge_score"] < 45:
            return "Not recommended"

        return "Research candidate"

    def _scientific_validation(self, comparison, results, date):
        current = next(
            (item for item in results if item["strategy_name"] == "Current Atlas"),
            results[0] if results else None,
        )
        best = next(
            (
                item for item in results
                if item["strategy_name"] == comparison["best_overall"]
            ),
            current,
        )

        if not current or not best:
            return {}

        regimes = {
            regime: {"status": "Neutral", "sample_size": current["sample_size"]}
            for regime in ScientificValidationEngine.REGIMES
        }
        generalization = {
            test: {"status": "Neutral", "sample_size": current["sample_size"]}
            for test in ScientificValidationEngine.GENERALIZATION_TESTS
        }

        return self.scientific_validation.evaluate(
            experiment_id=f"sv-{comparison['best_overall'].lower().replace(' ', '-')}",
            experiment_date=date,
            feature_tested=(
                "Simulation Arena Strategy: "
                f"{comparison['best_overall']}"
            ),
            baseline=current["metrics"],
            candidate=best["metrics"],
            sample_size=best["sample_size"],
            regimes=regimes,
            generalization=generalization,
        )

    def _market_regimes(self, results):
        regimes = sorted({
            regime
            for result in results
            for regime in result.get("market_regimes_tested", [])
        })

        return regimes

    def _trade_frequency(self, replay):
        validations = replay["validations"]
        tickers = {
            item.get("ticker")
            for item in replay["recommendations"]
            if item.get("ticker")
        }

        if not tickers:
            return 0

        return round(len(validations) / len(tickers), 2)

    def _strategy_notes(self, strategy):
        if strategy.get("candidate_placeholder"):
            return "Candidate model placeholder requires validation before adoption."

        disabled = sorted(strategy.get("toggles", {}).keys())
        if not disabled:
            return "Current Atlas baseline configuration."

        return f"Research-only configuration with {', '.join(disabled)} adjusted."

    def _name(self, rows):
        if not rows:
            return None

        return rows[0]["strategy_name"]

    def _average(self, values):
        clean = [value for value in values if value is not None]

        if not clean:
            return 0

        return round(sum(clean) / len(clean), 2)
