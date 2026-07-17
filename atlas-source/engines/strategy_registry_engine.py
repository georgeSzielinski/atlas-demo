import hashlib
import json


class StrategyRegistryEngine:
    """Deterministic, research-only registry of investment strategy specs.

    A strategy is a declarative JSON-style spec over a whitelisted vocabulary
    of deterministic signal inputs (fields that already exist on stored
    recommendation records) and simple scoring logic (a weight vector plus
    action bands). Specs are interpreted, never executed: there is no code in
    a spec, no LLM anywhere, and unknown signal keys, universe sources, or
    filters are rejected at validation time.

    Registry v1 is code-defined and read-only: the built-in strategies below
    are the entire registry, every spec carries a research-only policy, there
    is no activation switch, and the Live Paper Fund never reads this module.
    Comparison runs are handled by StrategyComparisonEngine; nothing here
    writes to the database or changes any live behavior.
    """

    VERSION = "strategy-registry-v1"

    # Whitelisted deterministic signal inputs. Every key maps to a numeric
    # column already persisted on recommendation rows; "scale" is the value's
    # native maximum so scoring can normalize each input to 0-100.
    SIGNAL_INPUTS = {
        "confidence": {
            "scale": 100,
            "description": "Final recommendation confidence (0-100).",
        },
        "overall_conviction": {
            "scale": 100,
            "description": "Fusion-engine overall conviction (0-100).",
        },
        "overall_score": {
            "scale": 100,
            "description": "Investment intelligence overall score (0-100).",
        },
        "technical_score": {
            "scale": 100,
            "description": "Technical analysis score (0-100).",
        },
        "fundamental_score": {
            "scale": 100,
            "description": "Fundamental analysis score (0-100).",
        },
        "forecast_score": {
            "scale": 100,
            "description": "Deterministic forecast score (0-100).",
        },
        "news_confidence": {
            "scale": 100,
            "description": "News sentiment agreement confidence (0-100).",
        },
        "signal_quality_score": {
            "scale": 10,
            "description": "Signal quality gate score (0-10).",
        },
        "committee_agreement": {
            "scale": 100,
            "description": "Investment committee agreement (0-100).",
        },
        "stability_score": {
            "scale": 100,
            "description": "Recommendation stability score (0-100).",
        },
        "knowledge_score": {
            "scale": 100,
            "description": "Evidence knowledge depth score (0-100).",
        },
    }

    UNIVERSE_SOURCES = ("paper_fund_watchlist", "approved_tickers", "explicit")

    # Whitelisted deterministic universe filters (applied to recommendation
    # records, never to fabricated data).
    UNIVERSE_FILTERS = ("min_confidence", "min_signal_quality", "max_candidates")

    REQUIRED_FIELDS = (
        "strategy_id",
        "name",
        "description",
        "universe_rules",
        "signal_inputs",
        "scoring_logic",
        "risk_assumptions",
        "expected_holding_period",
        "explanation",
    )

    # Fields hashed into definition_hash: the definitional content of a
    # strategy, excluding presentation-only metadata.
    HASHED_FIELDS = (
        "strategy_id",
        "universe_rules",
        "signal_inputs",
        "scoring_logic",
        "risk_assumptions",
        "expected_holding_period",
    )

    # ------------------------------------------------------------------
    # Built-in research-only strategies
    # ------------------------------------------------------------------
    BUILTIN_STRATEGIES = [
        {
            "strategy_id": "atlas-baseline-v1",
            "name": "Atlas Baseline",
            "description": (
                "Research mirror of the current portfolio-construction blend: "
                "conviction-led with knowledge and stability support. The live "
                "construction engine's probability input is represented by "
                "recommendation confidence because per-run probability is not "
                "stored as a scalar column."
            ),
            "universe_rules": {"source": "paper_fund_watchlist", "filters": {}},
            "signal_inputs": [
                "overall_conviction",
                "confidence",
                "knowledge_score",
                "stability_score",
            ],
            "scoring_logic": {
                "weights": {
                    "overall_conviction": 0.40,
                    "confidence": 0.25,
                    "knowledge_score": 0.18,
                    "stability_score": 0.17,
                },
                "action_bands": {"buy": 70, "hold": 45},
            },
            "risk_assumptions": {
                "max_position_pct": 20,
                "max_positions": 8,
                "cash_reserve_pct": 5,
                "drawdown_tolerance_pct": 12,
                "max_correlation": 0.80,
            },
            "expected_holding_period": "30-90 days",
            "explanation": (
                "Serves as the named, versioned baseline so every alternative "
                "strategy is compared against what Atlas effectively does "
                "today rather than against an implicit default."
            ),
        },
        {
            "strategy_id": "quality-compounder-v1",
            "name": "Quality Compounder",
            "description": (
                "Fundamental-quality weighted selection intended for long "
                "holding periods; favors stable, well-understood businesses "
                "over momentum."
            ),
            "universe_rules": {
                "source": "paper_fund_watchlist",
                "filters": {"min_confidence": 40},
            },
            "signal_inputs": [
                "fundamental_score",
                "stability_score",
                "knowledge_score",
                "news_confidence",
            ],
            "scoring_logic": {
                "weights": {
                    "fundamental_score": 0.50,
                    "stability_score": 0.20,
                    "knowledge_score": 0.20,
                    "news_confidence": 0.10,
                },
                "action_bands": {"buy": 70, "hold": 50},
            },
            "risk_assumptions": {
                "max_position_pct": 15,
                "max_positions": 10,
                "cash_reserve_pct": 10,
                "drawdown_tolerance_pct": 15,
                "max_correlation": 0.75,
            },
            "expected_holding_period": "180-365 days",
            "explanation": (
                "Buys only when fundamentals dominate the score; low turnover "
                "assumption means signal freshness matters less than balance-"
                "sheet quality."
            ),
        },
        {
            "strategy_id": "momentum-trend-v1",
            "name": "Momentum Trend",
            "description": (
                "Technical- and forecast-weighted selection for shorter "
                "holding periods; requires a minimum signal-quality gate so "
                "weak signals never qualify."
            ),
            "universe_rules": {
                "source": "paper_fund_watchlist",
                "filters": {"min_signal_quality": 5},
            },
            "signal_inputs": [
                "technical_score",
                "forecast_score",
                "news_confidence",
                "confidence",
            ],
            "scoring_logic": {
                "weights": {
                    "technical_score": 0.55,
                    "forecast_score": 0.25,
                    "news_confidence": 0.10,
                    "confidence": 0.10,
                },
                "action_bands": {"buy": 72, "hold": 50},
            },
            "risk_assumptions": {
                "max_position_pct": 12,
                "max_positions": 12,
                "cash_reserve_pct": 15,
                "drawdown_tolerance_pct": 10,
                "max_correlation": 0.70,
            },
            "expected_holding_period": "14-45 days",
            "explanation": (
                "Trend-following logic assumes faster mean reversion of edge; "
                "smaller positions and a larger cash reserve compensate for "
                "higher turnover risk."
            ),
        },
        {
            "strategy_id": "growth-horizon-v1",
            "name": "Growth Horizon",
            "description": (
                "Forward-looking growth selection weighted toward the "
                "deterministic forecast and technical trend, with conviction "
                "and news agreement as supporting context."
            ),
            "universe_rules": {"source": "paper_fund_watchlist", "filters": {}},
            "signal_inputs": [
                "forecast_score",
                "technical_score",
                "overall_conviction",
                "news_confidence",
            ],
            "scoring_logic": {
                "weights": {
                    "forecast_score": 0.35,
                    "technical_score": 0.25,
                    "overall_conviction": 0.25,
                    "news_confidence": 0.15,
                },
                "action_bands": {"buy": 70, "hold": 48},
            },
            "risk_assumptions": {
                "max_position_pct": 15,
                "max_positions": 10,
                "cash_reserve_pct": 10,
                "drawdown_tolerance_pct": 14,
                "max_correlation": 0.75,
            },
            "expected_holding_period": "60-180 days",
            "explanation": (
                "Prioritizes expected forward trajectory over trailing "
                "fundamentals; forecast and trend must agree before the "
                "score can clear the buy band."
            ),
        },
        {
            "strategy_id": "value-discipline-v1",
            "name": "Value Discipline",
            "description": (
                "Fundamentals-first selection with a lower buy threshold: "
                "willing to act on strong balance-sheet evidence before "
                "sentiment confirms, holding for long periods."
            ),
            "universe_rules": {"source": "paper_fund_watchlist", "filters": {}},
            "signal_inputs": [
                "fundamental_score",
                "knowledge_score",
                "stability_score",
                "news_confidence",
            ],
            "scoring_logic": {
                "weights": {
                    "fundamental_score": 0.45,
                    "knowledge_score": 0.25,
                    "stability_score": 0.20,
                    "news_confidence": 0.10,
                },
                "action_bands": {"buy": 65, "hold": 45},
            },
            "risk_assumptions": {
                "max_position_pct": 15,
                "max_positions": 12,
                "cash_reserve_pct": 10,
                "drawdown_tolerance_pct": 18,
                "max_correlation": 0.75,
            },
            "expected_holding_period": "365-730 days",
            "explanation": (
                "Accepts interim drawdowns in exchange for entry prices "
                "justified by fundamental evidence; news carries the "
                "smallest weight by design."
            ),
        },
        {
            "strategy_id": "defensive-ballast-v1",
            "name": "Defensive Ballast",
            "description": (
                "Capital-preservation profile: stability-dominated scoring, "
                "the highest buy threshold in the registry, small positions, "
                "and a large cash reserve assumption."
            ),
            "universe_rules": {"source": "paper_fund_watchlist", "filters": {}},
            "signal_inputs": [
                "stability_score",
                "fundamental_score",
                "knowledge_score",
                "committee_agreement",
            ],
            "scoring_logic": {
                "weights": {
                    "stability_score": 0.40,
                    "fundamental_score": 0.25,
                    "knowledge_score": 0.20,
                    "committee_agreement": 0.15,
                },
                "action_bands": {"buy": 78, "hold": 55},
            },
            "risk_assumptions": {
                "max_position_pct": 8,
                "max_positions": 12,
                "cash_reserve_pct": 25,
                "drawdown_tolerance_pct": 8,
                "max_correlation": 0.65,
            },
            "expected_holding_period": "180-365 days",
            "explanation": (
                "Only broadly-agreed, stable, well-understood candidates can "
                "clear the 78-point buy band; everything else defaults to "
                "holding cash."
            ),
        },
        {
            "strategy_id": "balanced-core-v1",
            "name": "Balanced Core",
            "description": (
                "Evenly diversified signal blend across technicals, "
                "fundamentals, forecast, and context scores; the neutral "
                "reference point between the momentum and quality profiles."
            ),
            "universe_rules": {"source": "paper_fund_watchlist", "filters": {}},
            "signal_inputs": [
                "technical_score",
                "fundamental_score",
                "forecast_score",
                "news_confidence",
                "stability_score",
                "knowledge_score",
            ],
            "scoring_logic": {
                "weights": {
                    "technical_score": 0.25,
                    "fundamental_score": 0.25,
                    "forecast_score": 0.20,
                    "news_confidence": 0.10,
                    "stability_score": 0.10,
                    "knowledge_score": 0.10,
                },
                "action_bands": {"buy": 68, "hold": 48},
            },
            "risk_assumptions": {
                "max_position_pct": 15,
                "max_positions": 10,
                "cash_reserve_pct": 8,
                "drawdown_tolerance_pct": 12,
                "max_correlation": 0.75,
            },
            "expected_holding_period": "90-180 days",
            "explanation": (
                "No single signal family can dominate the score, so a data "
                "gap in one input degrades the strategy gracefully instead of "
                "flipping its conclusions."
            ),
        },
    ]

    BASELINE_STRATEGY_ID = "atlas-baseline-v1"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self, spec):
        """Return a list of problems with a spec; an empty list means valid."""
        problems = []
        if not isinstance(spec, dict):
            return ["Strategy spec must be a dict."]

        for field in self.REQUIRED_FIELDS:
            value = spec.get(field)
            if value is None or value == "" or value == {} or value == []:
                problems.append(f"Missing required field: {field}.")
        if problems:
            return problems

        strategy_id = str(spec["strategy_id"])
        if strategy_id != strategy_id.strip().lower() or " " in strategy_id:
            problems.append("strategy_id must be a lowercase slug without spaces.")

        universe = spec["universe_rules"]
        if not isinstance(universe, dict):
            problems.append("universe_rules must be a dict.")
        else:
            source = universe.get("source")
            if source not in self.UNIVERSE_SOURCES:
                problems.append(
                    f"universe_rules.source must be one of {list(self.UNIVERSE_SOURCES)}."
                )
            if source == "explicit" and not universe.get("tickers"):
                problems.append(
                    "universe_rules.tickers is required when source is explicit."
                )
            filters = universe.get("filters", {})
            if not isinstance(filters, dict):
                problems.append("universe_rules.filters must be a dict.")
            else:
                for key in filters:
                    if key not in self.UNIVERSE_FILTERS:
                        problems.append(f"Unknown universe filter: {key}.")

        signals = spec["signal_inputs"]
        if not isinstance(signals, list) or not signals:
            problems.append("signal_inputs must be a non-empty list.")
            signals = []
        for signal in signals:
            if signal not in self.SIGNAL_INPUTS:
                problems.append(f"Unknown signal input: {signal}.")

        scoring = spec["scoring_logic"]
        if not isinstance(scoring, dict):
            problems.append("scoring_logic must be a dict.")
        else:
            weights = scoring.get("weights")
            if not isinstance(weights, dict) or not weights:
                problems.append("scoring_logic.weights must be a non-empty dict.")
            else:
                for key, value in weights.items():
                    if key not in signals:
                        problems.append(
                            f"Weight key {key} is not declared in signal_inputs."
                        )
                    if not isinstance(value, (int, float)) or value <= 0:
                        problems.append(f"Weight for {key} must be a positive number.")
                total = sum(
                    value for value in weights.values()
                    if isinstance(value, (int, float))
                )
                if total <= 0:
                    problems.append("scoring_logic.weights must sum to a positive total.")

            bands = scoring.get("action_bands")
            if not isinstance(bands, dict):
                problems.append("scoring_logic.action_bands must be a dict.")
            else:
                buy = bands.get("buy")
                hold = bands.get("hold")
                if not isinstance(buy, (int, float)) or not isinstance(hold, (int, float)):
                    problems.append("action_bands.buy and action_bands.hold are required numbers.")
                elif not (0 < hold < buy <= 100):
                    problems.append("action_bands must satisfy 0 < hold < buy <= 100.")

        if not isinstance(spec["risk_assumptions"], dict):
            problems.append("risk_assumptions must be a dict.")

        return problems

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------
    def definition_hash(self, spec):
        """Stable content hash of a spec's definitional fields."""
        canonical = {field: spec.get(field) for field in self.HASHED_FIELDS}
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Read-only access
    # ------------------------------------------------------------------
    def list_strategies(self):
        """All registered strategies, validated, hashed, deterministic order."""
        strategies = []
        for spec in sorted(
            self.BUILTIN_STRATEGIES, key=lambda item: item["strategy_id"]
        ):
            problems = self.validate(spec)
            strategies.append({
                **spec,
                "definition_hash": self.definition_hash(spec),
                "status": "RESEARCH",
                "valid": not problems,
                "validation_problems": problems,
                "is_baseline": spec["strategy_id"] == self.BASELINE_STRATEGY_ID,
                "policy": self.strategy_policy(),
            })
        return strategies

    def get_strategy(self, strategy_id):
        wanted = str(strategy_id or "").strip().lower()
        for strategy in self.list_strategies():
            if strategy["strategy_id"] == wanted:
                return strategy
        return None

    def report(self):
        strategies = self.list_strategies()
        return {
            "version": self.VERSION,
            "strategies": strategies,
            "count": len(strategies),
            "baseline_strategy_id": self.BASELINE_STRATEGY_ID,
            "signal_catalog": {
                key: value["description"]
                for key, value in self.SIGNAL_INPUTS.items()
            },
            "universe_sources": list(self.UNIVERSE_SOURCES),
            "universe_filters": list(self.UNIVERSE_FILTERS),
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Policy
    # ------------------------------------------------------------------
    def strategy_policy(self):
        return {
            "research_only": True,
            "execution_enabled": False,
            "read_only": True,
            "deterministic": True,
            "llm_decisions": False,
            "broker_integration": False,
            "real_money": False,
            "used_by_live_paper_fund": False,
            "activation_switch": False,
        }

    def policy(self):
        return {
            **self.strategy_policy(),
            "writes": False,
            "persists_comparisons": False,
            "modifies_recommendations": False,
            "modifies_portfolio_construction": False,
            "modifies_risk": False,
            "modifies_scheduler": False,
        }
