import json
from types import SimpleNamespace

from engines.committee_member import CommitteeMember
from engines.strategy_registry_engine import StrategyRegistryEngine


registry = StrategyRegistryEngine()


# ---------------------------------------------------------------------------
# Construction: only valid registry specs become members.
# ---------------------------------------------------------------------------
baseline_spec = registry.get_strategy("atlas-baseline-v1")
member = CommitteeMember(baseline_spec)
assert member.strategy_id == "atlas-baseline-v1"
assert member.name == "Atlas Baseline"

try:
    CommitteeMember({"strategy_id": "broken"})
    raise AssertionError("Invalid spec must be rejected")
except ValueError as error:
    assert "Invalid strategy spec" in str(error)


# ---------------------------------------------------------------------------
# Full coverage: exact deterministic score, action, and confidence.
# Uniform normalized inputs of 85 make every weighted blend equal 85.
# ---------------------------------------------------------------------------
uniform_85 = {
    "ticker": "AAPL",
    "confidence": 85,
    "overall_conviction": 85,
    "knowledge_score": 85,
    "stability_score": 85,
}
vote = member.evaluate(uniform_85)
assert vote["status"] == "EVALUATED"
assert vote["score"] == 85.0
assert vote["action"] == "BUY"  # baseline buy band is 70
# band_margin = 85 - 70 = 15 -> confidence = 50 + 2*15 = 80 at 100% coverage.
assert vote["confidence"] == 80
assert vote["coverage_pct"] == 100
assert vote["missing_inputs"] == []
assert vote["explanation"].startswith("Atlas Baseline votes BUY")

# Drivers are sorted by contribution (weight x normalized), descending.
driver_signals = [driver["signal"] for driver in vote["drivers"]]
assert driver_signals[0] == "overall_conviction"  # largest weight 0.40
assert len(vote["drivers"]) == 4
for driver in vote["drivers"]:
    assert driver["contribution"] == round(driver["normalized"] * driver["weight"], 2)

# Action bands: low uniform inputs -> AVOID; middle -> HOLD.
low_vote = member.evaluate({**uniform_85, "confidence": 30, "overall_conviction": 30,
                            "knowledge_score": 30, "stability_score": 30})
assert low_vote["action"] == "AVOID"
mid_vote = member.evaluate({**uniform_85, "confidence": 55, "overall_conviction": 55,
                            "knowledge_score": 55, "stability_score": 55})
assert mid_vote["action"] == "HOLD"

# Confidence at an exact band boundary is 50 (no margin).
boundary_vote = member.evaluate({**uniform_85, "confidence": 70, "overall_conviction": 70,
                                 "knowledge_score": 70, "stability_score": 70})
assert boundary_vote["score"] == 70.0
assert boundary_vote["action"] == "BUY"
assert boundary_vote["confidence"] == 50


# ---------------------------------------------------------------------------
# Scale normalization: signal_quality_score is 0-10, normalized to 0-100.
# ---------------------------------------------------------------------------
quality_gate_spec = {
    "strategy_id": "test-quality-gate-v1",
    "name": "Test Quality Gate",
    "description": "Test spec for scale normalization.",
    "universe_rules": {"source": "explicit", "tickers": ["AAPL"], "filters": {}},
    "signal_inputs": ["signal_quality_score"],
    "scoring_logic": {
        "weights": {"signal_quality_score": 1.0},
        "action_bands": {"buy": 70, "hold": 45},
    },
    "risk_assumptions": {"max_position_pct": 10},
    "expected_holding_period": "30 days",
    "explanation": "Test.",
}
gate_member = CommitteeMember(quality_gate_spec)
gate_vote = gate_member.evaluate({"ticker": "AAPL", "signal_quality_score": 8})
assert gate_vote["score"] == 80.0  # 8 of 10 -> 80 of 100
assert gate_vote["action"] == "BUY"
assert gate_vote["drivers"][0]["normalized"] == 80.0


# ---------------------------------------------------------------------------
# Partial coverage: missing signals are excluded and reported, never defaulted.
# Coverage 0.40+0.25+0.17 = 82% of weight -> PARTIAL, confidence scaled down.
# ---------------------------------------------------------------------------
partial = {
    "ticker": "AAPL",
    "overall_conviction": 85,
    "confidence": 85,
    "stability_score": 85,
}
partial_vote = member.evaluate(partial)
assert partial_vote["status"] == "PARTIAL"
assert partial_vote["coverage_pct"] == 82.0
assert partial_vote["score"] == 85.0  # renormalized over available weight
assert partial_vote["missing_inputs"] == ["knowledge_score"]
# confidence = round((50 + 2*15) * 0.82) = round(65.6) = 66
assert partial_vote["confidence"] == 66


# ---------------------------------------------------------------------------
# Below 50% coverage: the member abstains with NOT_EVALUATED — no guessing.
# ---------------------------------------------------------------------------
sparse_vote = member.evaluate({"ticker": "AAPL", "knowledge_score": 90})
assert sparse_vote["status"] == "NOT_EVALUATED"
assert sparse_vote["action"] is None
assert sparse_vote["score"] is None
assert sparse_vote["confidence"] is None
assert "abstained" in sparse_vote["explanation"]
assert set(sparse_vote["missing_inputs"]) == {
    "confidence", "overall_conviction", "stability_score",
}

# Empty record -> NOT_EVALUATED with every input missing.
empty_vote = member.evaluate({})
assert empty_vote["status"] == "NOT_EVALUATED"
assert len(empty_vote["missing_inputs"]) == 4


# ---------------------------------------------------------------------------
# Records may be objects (attribute access), not just dicts.
# ---------------------------------------------------------------------------
object_vote = member.evaluate(SimpleNamespace(**uniform_85))
assert object_vote["score"] == 85.0
assert object_vote["action"] == "BUY"

# Non-numeric values are treated as missing, not coerced.
junk_vote = member.evaluate({**uniform_85, "confidence": "not-a-number"})
assert "confidence" in junk_vote["missing_inputs"]


# ---------------------------------------------------------------------------
# Determinism: identical input -> byte-identical vote.
# ---------------------------------------------------------------------------
assert json.dumps(member.evaluate(uniform_85), sort_keys=True) == json.dumps(
    member.evaluate(uniform_85), sort_keys=True
)


# ---------------------------------------------------------------------------
# Policy: research-only safety flags.
# ---------------------------------------------------------------------------
policy = member.policy()
assert policy["research_only"] is True
assert policy["llm_decisions"] is False
assert policy["randomness"] is False
assert policy["broker_integration"] is False
assert policy["real_money"] is False
assert policy["modifies_live_paper_fund"] is False

print("CommitteeMember test passed.")
