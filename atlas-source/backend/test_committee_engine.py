import json

from engines.committee_engine import CommitteeEngine
from engines.strategy_registry_engine import StrategyRegistryEngine


engine = CommitteeEngine()


# ---------------------------------------------------------------------------
# Built-in committee: six named members sourced from the strategy registry.
# ---------------------------------------------------------------------------
assert len(engine.members) == 6
assert [member.strategy_id for member in engine.members] == [
    "atlas-baseline-v1",
    "momentum-trend-v1",
    "quality-compounder-v1",
    "growth-horizon-v1",
    "value-discipline-v1",
    "defensive-ballast-v1",
]
assert engine.quorum == 3

registry = StrategyRegistryEngine()
for strategy_id in CommitteeEngine.BUILT_IN_COMMITTEE:
    strategy = registry.get_strategy(strategy_id)
    assert strategy is not None and strategy["valid"], strategy_id

try:
    CommitteeEngine(member_ids=["does-not-exist-v1"])
    raise AssertionError("Unknown member id must be rejected")
except ValueError as error:
    assert "not found in registry" in str(error)


def full_record(**overrides):
    """Record with every whitelisted signal populated (uniform 85)."""
    record = {
        "ticker": "AAPL",
        "confidence": 85,
        "overall_conviction": 85,
        "overall_score": 85,
        "technical_score": 85,
        "fundamental_score": 85,
        "forecast_score": 85,
        "news_confidence": 85,
        "signal_quality_score": 8.5,
        "committee_agreement": 85,
        "stability_score": 85,
        "knowledge_score": 85,
    }
    record.update(overrides)
    return record


# ---------------------------------------------------------------------------
# Unanimous BUY: uniform 85 clears every member's buy band (max 78).
# ---------------------------------------------------------------------------
unanimous = engine.evaluate(full_record())
assert unanimous["status"] == "EVALUATED"
assert unanimous["ticker"] == "AAPL"

recommendation = unanimous["committee_recommendation"]
assert recommendation["action"] == "BUY"
assert recommendation["agreement_pct"] == 100.0
assert recommendation["strength"] == "STRONG"
assert unanimous["agreement"]["voting_members"] == 6
assert unanimous["agreement"]["abstaining_members"] == 0
assert unanimous["agreement"]["tally"] == {"BUY": 6}
assert len(unanimous["votes"]) == 6
assert unanimous["minority_report"]["dissenters"] == []
assert "No dissent" in unanimous["minority_report"]["summary"]
assert unanimous["majority_report"]["action"] == "BUY"
assert len(unanimous["majority_report"]["members"]) == 6

# Weighted confidence at full coverage = mean member confidence.
# Every score is 85; margins vs buy bands: 15,13,15,15,20,7 -> conf 80,76,80,80,90,64.
assert unanimous["confidence"] == round((80 + 76 + 80 + 80 + 90 + 64) / 6, 2)

# Driver summary aggregates across members, capped at 5, sorted by weight.
assert 1 <= len(unanimous["driver_summary"]) <= 5
totals = [item["total_contribution"] for item in unanimous["driver_summary"]]
assert totals == sorted(totals, reverse=True)

# Unanimous AVOID on uniformly weak inputs.
weak = engine.evaluate(full_record(
    confidence=30, overall_conviction=30, overall_score=30, technical_score=30,
    fundamental_score=30, forecast_score=30, news_confidence=30,
    signal_quality_score=3, committee_agreement=30, stability_score=30,
    knowledge_score=30,
))
assert weak["committee_recommendation"]["action"] == "AVOID"
assert weak["agreement"]["tally"] == {"AVOID": 6}


# ---------------------------------------------------------------------------
# Split committee: growth signals strong, value signals weak.
# Expected votes: momentum BUY, growth BUY, baseline HOLD,
# quality/value/defensive AVOID -> consensus AVOID at 50% agreement.
# ---------------------------------------------------------------------------
split_record = full_record(
    technical_score=90, forecast_score=90, news_confidence=80,
    overall_conviction=75, confidence=75, fundamental_score=35,
    stability_score=40, knowledge_score=40, committee_agreement=40,
    signal_quality_score=8,
)
split = engine.evaluate(split_record)
by_member = {vote["member_id"]: vote for vote in split["votes"]}
assert by_member["momentum-trend-v1"]["action"] == "BUY"
assert by_member["growth-horizon-v1"]["action"] == "BUY"
assert by_member["atlas-baseline-v1"]["action"] == "HOLD"
assert by_member["quality-compounder-v1"]["action"] == "AVOID"
assert by_member["value-discipline-v1"]["action"] == "AVOID"
assert by_member["defensive-ballast-v1"]["action"] == "AVOID"

assert split["committee_recommendation"]["action"] == "AVOID"
assert split["committee_recommendation"]["agreement_pct"] == 50.0
assert split["committee_recommendation"]["strength"] == "WEAK"
assert split["agreement"]["tally"] == {"AVOID": 3, "BUY": 2, "HOLD": 1}

minority = split["minority_report"]
assert {item["member_id"] for item in minority["dissenters"]} == {
    "momentum-trend-v1", "growth-horizon-v1", "atlas-baseline-v1",
}
assert "dissents" in minority["summary"]
for dissenter in minority["dissenters"]:
    assert dissenter["top_driver"]
    assert dissenter["explanation"]


# ---------------------------------------------------------------------------
# Tie-break is conservative: 3 BUY vs 3 AVOID resolves to AVOID.
# ---------------------------------------------------------------------------
tie_record = full_record(
    technical_score=90, forecast_score=90, news_confidence=80,
    overall_conviction=95, confidence=95, fundamental_score=35,
    stability_score=40, knowledge_score=40, committee_agreement=40,
    signal_quality_score=8,
)
tie = engine.evaluate(tie_record)
assert tie["agreement"]["tally"] == {"AVOID": 3, "BUY": 3}
assert tie["committee_recommendation"]["action"] == "AVOID"
assert tie["committee_recommendation"]["agreement_pct"] == 50.0


# ---------------------------------------------------------------------------
# NOT_EVALUATED propagation: below quorum the committee abstains entirely.
# knowledge_score alone gives every member under 50% weight coverage.
# ---------------------------------------------------------------------------
no_quorum = engine.evaluate({"ticker": "AAPL", "knowledge_score": 90})
assert no_quorum["status"] == "NOT_EVALUATED"
assert no_quorum["committee_recommendation"]["action"] is None
assert no_quorum["committee_recommendation"]["strength"] == "NOT_EVALUATED"
assert no_quorum["confidence"] is None
assert no_quorum["agreement"]["voting_members"] == 0
assert no_quorum["agreement"]["abstaining_members"] == 6
assert "quorum is 3" in no_quorum["reason"]
assert no_quorum["driver_summary"] == []
for vote in no_quorum["votes"]:
    assert vote["status"] == "NOT_EVALUATED"

# Partial data: four members can vote (quorum met), two abstain -> PARTIAL.
partial_record = {
    "ticker": "MSFT",
    "overall_conviction": 80,
    "confidence": 80,
    "knowledge_score": 80,
    "stability_score": 80,
    "fundamental_score": 80,
    "news_confidence": 80,
}
partial = engine.evaluate(partial_record)
assert partial["status"] == "PARTIAL"
assert partial["agreement"]["voting_members"] == 4
assert partial["agreement"]["abstaining_members"] == 2
abstainers = {
    vote["member_id"] for vote in partial["votes"]
    if vote["status"] == "NOT_EVALUATED"
}
assert abstainers == {"momentum-trend-v1", "growth-horizon-v1"}
assert partial["committee_recommendation"]["action"] is not None
assert "abstained" in partial["committee_recommendation"]["explanation"]


# ---------------------------------------------------------------------------
# Determinism: identical input -> byte-identical committee output.
# ---------------------------------------------------------------------------
assert json.dumps(engine.evaluate(split_record), sort_keys=True) == json.dumps(
    engine.evaluate(split_record), sort_keys=True
)


# ---------------------------------------------------------------------------
# Read-only guarantee: convening the committee performs no database writes.
# ---------------------------------------------------------------------------
import database.repository as repository

WRITE_FUNCTIONS = [
    name for name in dir(repository)
    if name.startswith(("save_", "add_", "update_", "delete_", "reset_"))
]
originals = {name: getattr(repository, name) for name in WRITE_FUNCTIONS}


def forbidden(name):
    def _fail(*args, **kwargs):
        raise AssertionError(f"Committee must not call repository.{name}")
    return _fail


try:
    for name in WRITE_FUNCTIONS:
        setattr(repository, name, forbidden(name))
    engine.evaluate(full_record())
    engine.evaluate({"ticker": "AAPL"})
finally:
    for name, original in originals.items():
        setattr(repository, name, original)


# ---------------------------------------------------------------------------
# Policy block: research-only safety flags on every output.
# ---------------------------------------------------------------------------
for report in (unanimous, split, no_quorum, partial):
    policy = report["policy"]
    assert policy["research_only"] is True
    assert policy["deterministic"] is True
    assert policy["llm_decisions"] is False
    assert policy["randomness"] is False
    assert policy["broker_integration"] is False
    assert policy["real_money"] is False
    assert policy["creates_orders"] is False
    assert policy["modifies_live_paper_fund"] is False
    assert policy["modifies_portfolio_construction"] is False
    assert policy["modifies_risk_management"] is False
    assert policy["modifies_trading_execution"] is False

print("CommitteeEngine test passed.")
