from fastapi.testclient import TestClient

import api.main as api_main
import database.repository as repository
from api.main import app
from engines.committee_engine import CommitteeEngine


client = TestClient(app)

FULL_RECORD = {
    "id": 42,
    "run_id": 7,
    "ticker": "AAPL",
    "action": "BUY",
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

RESPONSE_KEYS = {
    "committee_recommendation",
    "votes",
    "agreement",
    "confidence",
    "majority_report",
    "minority_report",
    "driver_summary",
    "policy",
}


def with_loader(loader, call):
    """Run `call` with api.main's record loader swapped for `loader`."""
    original = api_main.get_latest_recommendation_for_ticker
    api_main.get_latest_recommendation_for_ticker = loader
    try:
        return call()
    finally:
        api_main.get_latest_recommendation_for_ticker = original


# ---------------------------------------------------------------------------
# Existing ticker: full committee evaluation with every required section.
# ---------------------------------------------------------------------------
response = with_loader(
    lambda ticker: dict(FULL_RECORD),
    lambda: client.get("/committee/evaluate/AAPL"),
)
assert response.status_code == 200
body = response.json()
assert RESPONSE_KEYS <= set(body)
assert body["ticker"] == "AAPL"
assert body["status"] == "EVALUATED"
assert body["committee_recommendation"]["action"] == "BUY"
assert body["committee_recommendation"]["strength"] == "STRONG"
assert body["committee_recommendation"]["agreement_pct"] == 100.0
assert len(body["votes"]) == 6
assert body["agreement"]["voting_members"] == 6
assert body["confidence"] == body["committee_recommendation"]["confidence"]
assert body["majority_report"]["action"] == "BUY"
assert body["minority_report"]["dissenters"] == []
assert len(body["driver_summary"]) >= 1
assert body["source"] == {
    "recommendation_id": 42,
    "run_id": 7,
    "stored_action": "BUY",
    "read_only": True,
}

# Policy block is research-only on the wire.
policy = body["policy"]
assert policy["research_only"] is True
assert policy["read_only"] is True
assert policy["llm_decisions"] is False
assert policy["broker_integration"] is False
assert policy["real_money"] is False
assert policy["creates_orders"] is False
assert policy["modifies_live_paper_fund"] is False


# ---------------------------------------------------------------------------
# Missing ticker: NOT_EVALUATED with a clear reason, no fabricated inputs.
# ---------------------------------------------------------------------------
missing = with_loader(
    lambda ticker: None,
    lambda: client.get("/committee/evaluate/ZZZZ"),
)
assert missing.status_code == 200
missing_body = missing.json()
assert RESPONSE_KEYS <= set(missing_body)
assert missing_body["status"] == "NOT_EVALUATED"
assert missing_body["ticker"] == "ZZZZ"
assert "No stored recommendation exists for ZZZZ" in missing_body["reason"]
assert "never fabricated" in missing_body["reason"]
assert missing_body["committee_recommendation"]["action"] is None
assert missing_body["committee_recommendation"]["strength"] == "NOT_EVALUATED"
assert missing_body["confidence"] is None
assert missing_body["votes"] == []
assert missing_body["agreement"]["voting_members"] == 0
assert missing_body["agreement"]["quorum"] == CommitteeEngine().quorum
assert missing_body["driver_summary"] == []
assert missing_body["policy"]["research_only"] is True

# Ticker casing is normalized.
lower = with_loader(
    lambda ticker: None,
    lambda: client.get("/committee/evaluate/msft"),
)
assert lower.json()["ticker"] == "MSFT"


# ---------------------------------------------------------------------------
# Read-only guarantee: neither endpoint performs any database write.
# ---------------------------------------------------------------------------
WRITE_FUNCTIONS = [
    name for name in dir(repository)
    if name.startswith(("save_", "add_", "update_", "delete_", "reset_"))
]
originals = {name: getattr(repository, name) for name in WRITE_FUNCTIONS}


def forbidden(name):
    def _fail(*args, **kwargs):
        raise AssertionError(f"Committee API must not call repository.{name}")
    return _fail


try:
    for name in WRITE_FUNCTIONS:
        setattr(repository, name, forbidden(name))
    ok = with_loader(
        lambda ticker: dict(FULL_RECORD),
        lambda: client.get("/committee/evaluate/AAPL"),
    )
    assert ok.status_code == 200
    assert client.get("/committee/members").status_code == 200
finally:
    for name, original in originals.items():
        setattr(repository, name, original)


# ---------------------------------------------------------------------------
# Members endpoint: research-only roster from the Strategy Registry.
# ---------------------------------------------------------------------------
members_response = client.get("/committee/members")
assert members_response.status_code == 200
roster = members_response.json()
assert roster["count"] == 6
assert roster["quorum"] == 3
assert [member["member_id"] for member in roster["members"]] == list(
    CommitteeEngine.BUILT_IN_COMMITTEE
)
baselines = [m for m in roster["members"] if m["is_baseline"]]
assert len(baselines) == 1 and baselines[0]["member_id"] == "atlas-baseline-v1"
for member in roster["members"]:
    assert member["name"]
    assert member["description"]
    assert member["expected_holding_period"]
    assert member["scoring_weights"]
    assert member["action_bands"]["buy"] > member["action_bands"]["hold"]
    assert len(member["definition_hash"]) == 64
    member_policy = member["policy"]
    assert member_policy["research_only"] is True
    assert member_policy["broker_integration"] is False
    assert member_policy["real_money"] is False
assert roster["policy"]["modifies_trading_execution"] is False


# ---------------------------------------------------------------------------
# Live path (no loader patch): endpoint answers 200 whatever the DB holds —
# either a real evaluation or an honest NOT_EVALUATED, never an error.
# ---------------------------------------------------------------------------
live = client.get("/committee/evaluate/AAPL")
assert live.status_code == 200
assert live.json()["status"] in {"EVALUATED", "PARTIAL", "NOT_EVALUATED"}

print("Committee API test passed.")
