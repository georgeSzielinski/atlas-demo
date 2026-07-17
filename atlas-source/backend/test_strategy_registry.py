from engines.strategy_registry_engine import StrategyRegistryEngine


engine = StrategyRegistryEngine()

REQUIRED_POLICY_KEYS = {
    "research_only",
    "execution_enabled",
    "read_only",
    "deterministic",
    "llm_decisions",
    "broker_integration",
    "real_money",
    "used_by_live_paper_fund",
    "activation_switch",
}


# ---------------------------------------------------------------------------
# Built-in strategies are complete and valid.
# ---------------------------------------------------------------------------
strategies = engine.list_strategies()
assert len(strategies) == len(engine.BUILTIN_STRATEGIES)

for strategy in strategies:
    assert strategy["valid"], (
        f"{strategy['strategy_id']} invalid: {strategy['validation_problems']}"
    )
    for field in engine.REQUIRED_FIELDS:
        assert strategy.get(field) not in (None, "", {}, []), (
            f"{strategy['strategy_id']} is missing {field}"
        )
    assert strategy["status"] == "RESEARCH"
    assert len(strategy["definition_hash"]) == 64

    # Research-only policy on every strategy, with every safety flag correct.
    policy = strategy["policy"]
    assert REQUIRED_POLICY_KEYS <= set(policy)
    assert policy["research_only"] is True
    assert policy["execution_enabled"] is False
    assert policy["llm_decisions"] is False
    assert policy["broker_integration"] is False
    assert policy["real_money"] is False
    assert policy["used_by_live_paper_fund"] is False
    assert policy["activation_switch"] is False

    # Weights reference declared signal inputs only, all whitelisted.
    weights = strategy["scoring_logic"]["weights"]
    assert set(weights) <= set(strategy["signal_inputs"])
    assert set(strategy["signal_inputs"]) <= set(engine.SIGNAL_INPUTS)

# Deterministic ordering and exactly one baseline.
assert [s["strategy_id"] for s in strategies] == sorted(
    s["strategy_id"] for s in strategies
)
baselines = [s for s in strategies if s["is_baseline"]]
assert len(baselines) == 1
assert baselines[0]["strategy_id"] == engine.BASELINE_STRATEGY_ID


# ---------------------------------------------------------------------------
# definition_hash is stable, content-sensitive, and metadata-insensitive.
# ---------------------------------------------------------------------------
spec = dict(engine.BUILTIN_STRATEGIES[0])
hash_one = engine.definition_hash(spec)
hash_two = engine.definition_hash(dict(spec))
assert hash_one == hash_two

renamed = {**spec, "name": "Different Display Name", "description": "Changed."}
assert engine.definition_hash(renamed) == hash_one  # presentation fields excluded

reweighted = {
    **spec,
    "scoring_logic": {
        **spec["scoring_logic"],
        "weights": {**spec["scoring_logic"]["weights"], "confidence": 0.99},
    },
}
assert engine.definition_hash(reweighted) != hash_one  # definitional change


# ---------------------------------------------------------------------------
# Validation rejects malformed specs.
# ---------------------------------------------------------------------------
assert engine.validate(None) == ["Strategy spec must be a dict."]
assert any("Missing required field" in p for p in engine.validate({}))

valid_spec = {
    "strategy_id": "test-valid-v1",
    "name": "Test",
    "description": "Test spec.",
    "universe_rules": {"source": "explicit", "tickers": ["AAPL"], "filters": {}},
    "signal_inputs": ["confidence"],
    "scoring_logic": {
        "weights": {"confidence": 1.0},
        "action_bands": {"buy": 70, "hold": 45},
    },
    "risk_assumptions": {"max_position_pct": 10},
    "expected_holding_period": "30 days",
    "explanation": "Test.",
}
assert engine.validate(valid_spec) == []

bad_signal = {**valid_spec, "signal_inputs": ["confidence", "made_up_signal"]}
assert any("Unknown signal input" in p for p in engine.validate(bad_signal))

bad_weight_key = {
    **valid_spec,
    "scoring_logic": {
        "weights": {"technical_score": 1.0},
        "action_bands": {"buy": 70, "hold": 45},
    },
}
assert any("not declared in signal_inputs" in p for p in engine.validate(bad_weight_key))

negative_weight = {
    **valid_spec,
    "scoring_logic": {
        "weights": {"confidence": -1},
        "action_bands": {"buy": 70, "hold": 45},
    },
}
assert any("positive number" in p for p in engine.validate(negative_weight))

inverted_bands = {
    **valid_spec,
    "scoring_logic": {
        "weights": {"confidence": 1.0},
        "action_bands": {"buy": 40, "hold": 60},
    },
}
assert any("0 < hold < buy" in p for p in engine.validate(inverted_bands))

bad_source = {
    **valid_spec,
    "universe_rules": {"source": "live_broker", "filters": {}},
}
assert any("universe_rules.source" in p for p in engine.validate(bad_source))

explicit_without_tickers = {
    **valid_spec,
    "universe_rules": {"source": "explicit", "filters": {}},
}
assert any("tickers is required" in p for p in engine.validate(explicit_without_tickers))

unknown_filter = {
    **valid_spec,
    "universe_rules": {
        "source": "explicit",
        "tickers": ["AAPL"],
        "filters": {"min_market_cap": 1},
    },
}
assert any("Unknown universe filter" in p for p in engine.validate(unknown_filter))


# ---------------------------------------------------------------------------
# Lookup and report.
# ---------------------------------------------------------------------------
found = engine.get_strategy("ATLAS-BASELINE-V1")  # case-insensitive
assert found is not None and found["strategy_id"] == "atlas-baseline-v1"
assert engine.get_strategy("does-not-exist") is None

report = engine.report()
assert report["count"] == len(strategies)
assert report["baseline_strategy_id"] == engine.BASELINE_STRATEGY_ID
assert set(report["signal_catalog"]) == set(engine.SIGNAL_INPUTS)
assert report["policy"]["writes"] is False
assert report["policy"]["persists_comparisons"] is False

print("StrategyRegistryEngine test passed.")
