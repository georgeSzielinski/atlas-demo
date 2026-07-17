import json

from engines.strategy_comparison_engine import StrategyComparisonEngine
from engines.strategy_registry_engine import StrategyRegistryEngine


engine = StrategyComparisonEngine()

NOW = "2026-07-05T12:00:00"


def full_record(ticker, base=70):
    """A recommendation record with every whitelisted signal populated."""
    return {
        "ticker": ticker,
        "confidence": base,
        "overall_conviction": base + 5,
        "overall_score": base,
        "technical_score": base + 10,
        "fundamental_score": base - 5,
        "forecast_score": base,
        "news_confidence": base - 10,
        "signal_quality_score": 8,
        "committee_agreement": base,
        "stability_score": base,
        "knowledge_score": base - 5,
    }


STATE = {
    "fund_status": "READY",
    "updated_at": NOW,
    "watchlist": ["AAPL", "MSFT", "NVDA"],
    "starting_cash": 100000,
    "cash": 60000,
    "positions": {
        "AAPL": {"quantity": 100, "cost_basis": 200, "current_price": 210},
    },
    "realized_pl": 0,
}

RECORDS = [full_record("AAPL", 80), full_record("MSFT", 60), full_record("NVDA", 45)]


# ---------------------------------------------------------------------------
# Full-coverage comparison: EVALUATED strategies, deterministic output.
# ---------------------------------------------------------------------------
report = engine.compare(
    recommendations=RECORDS,
    paper_fund_state=STATE,
    approved_tickers=["AAPL", "MSFT"],
    now=NOW,
)

assert report["version"] == "strategy-comparison-v1"
assert report["inputs"]["recommendation_count"] == 3
assert report["inputs"]["paper_fund_status"] == "READY"
assert len(report["strategies"]) == len(StrategyRegistryEngine.BUILTIN_STRATEGIES)

policy = report["policy"]
assert policy["read_only"] is True
assert policy["on_demand_only"] is True
assert policy["persists_nothing"] is True
assert policy["creates_orders"] is False
assert policy["invokes_risk_gate"] is False
assert policy["modifies_live_paper_fund"] is False
assert policy["activation_switch"] is False
assert policy["llm_decisions"] is False
assert policy["broker_integration"] is False
assert policy["real_money"] is False

baseline = next(
    s for s in report["strategies"] if s["strategy_id"] == "atlas-baseline-v1"
)
assert baseline["status"] == "EVALUATED"
assert baseline["is_baseline"] is True
assert len(baseline["candidates"]) == 3

# Candidates ordered by score desc; full coverage; every candidate explained.
scores = [c["score"] for c in baseline["candidates"]]
assert scores == sorted(scores, reverse=True)
for candidate in baseline["candidates"]:
    assert candidate["coverage_pct"] == 100
    assert candidate["status"] == "EVALUATED"
    assert candidate["action"] in {"BUY", "HOLD", "AVOID", "EXCLUDED"}
    assert candidate["explanation"]
    assert candidate["missing_inputs"] == []

# Scoring is the documented weighted blend (AAPL, base 80).
aapl = next(c for c in baseline["candidates"] if c["ticker"] == "AAPL")
expected = round((85 * 0.40 + 80 * 0.25 + 75 * 0.18 + 80 * 0.17) / 1.0, 2)
assert aapl["score"] == expected, (aapl["score"], expected)
assert aapl["action"] == "BUY"

# Determinism: identical inputs produce an identical report.
repeat = engine.compare(
    recommendations=RECORDS,
    paper_fund_state=STATE,
    approved_tickers=["AAPL", "MSFT"],
    now=NOW,
)
assert json.dumps(report, sort_keys=True) == json.dumps(repeat, sort_keys=True)

# Portfolio fit is a dry run against the injected paper portfolio.
fit = baseline["portfolio_fit"]
assert fit["status"] == "EVALUATED"
assert fit["dry_run"] is True
assert any(row["already_held"] for row in fit["suggested_allocations"])

# Expected risks are advisory with correlation honestly NOT_EVALUATED.
risks = baseline["expected_risks"]
assert risks["advisory_only"] is True
assert risks["status"] == "EVALUATED"
assert risks["correlation"]["status"] == "NOT_EVALUATED"
assert all("within_limit" in check for check in risks["limit_checks"])

# Baseline divergence covers every non-baseline strategy.
divergence = report["baseline_divergence"]
assert divergence["status"] == "EVALUATED"
assert divergence["baseline_strategy_id"] == "atlas-baseline-v1"
assert len(divergence["rows"]) == len(report["strategies"]) - 1

# The momentum strategy's signal-quality filter excludes weak signals.
weak = full_record("WEAK", 75)
weak["signal_quality_score"] = 2
filtered = engine.compare(
    strategy_ids=["momentum-trend-v1"],
    recommendations=RECORDS + [weak],
    paper_fund_state={**STATE, "watchlist": ["AAPL", "WEAK"]},
    now=NOW,
)
weak_candidate = next(
    c
    for c in filtered["strategies"][0]["candidates"]
    if c["ticker"] == "WEAK"
)
assert weak_candidate["action"] == "EXCLUDED"
assert "signal quality" in weak_candidate["reason"]


# ---------------------------------------------------------------------------
# Missing data degrades to NOT_EVALUATED — never fabricated.
# ---------------------------------------------------------------------------
# No paper fund state -> watchlist universes are NOT_EVALUATED with reasons.
no_state = engine.compare(
    recommendations=RECORDS,
    paper_fund_state=None,
    approved_tickers=[],
    now=NOW,
)
for strategy in no_state["strategies"]:
    assert strategy["status"] == "NOT_EVALUATED"
    assert strategy["reason"]
    assert strategy["candidates"] == []
    assert strategy["portfolio_fit"]["status"] == "NOT_EVALUATED"
assert no_state["baseline_divergence"]["status"] == "NOT_EVALUATED"

# No recommendation records -> universe exists but nothing to score.
no_records = engine.compare(
    recommendations=[],
    paper_fund_state=STATE,
    approved_tickers=[],
    now=NOW,
)
for strategy in no_records["strategies"]:
    assert strategy["status"] == "NOT_EVALUATED"
    assert "recommendation" in strategy["reason"].lower()

# Sparse record: below 50% weight coverage -> candidate gets no score/action.
sparse = {"ticker": "AAPL", "knowledge_score": 70}
sparse_report = engine.compare(
    strategy_ids=["atlas-baseline-v1"],
    recommendations=[sparse],
    paper_fund_state={**STATE, "watchlist": ["AAPL"], "positions": {}},
    now=NOW,
)
sparse_strategy = sparse_report["strategies"][0]
sparse_candidate = sparse_strategy["candidates"][0]
assert sparse_candidate["status"] == "NOT_EVALUATED"
assert sparse_candidate["score"] is None
assert sparse_candidate["action"] is None
assert "overall_conviction" in sparse_candidate["missing_inputs"]
assert sparse_strategy["status"] == "NOT_EVALUATED"

# Partial record: >=50% coverage -> PARTIAL with renormalized score.
partial = {
    "ticker": "AAPL",
    "overall_conviction": 80,
    "confidence": 80,
    "stability_score": 80,
}
partial_report = engine.compare(
    strategy_ids=["atlas-baseline-v1"],
    recommendations=[partial],
    paper_fund_state={**STATE, "watchlist": ["AAPL"], "positions": {}},
    now=NOW,
)
partial_candidate = partial_report["strategies"][0]["candidates"][0]
assert partial_candidate["status"] == "PARTIAL"
assert partial_candidate["coverage_pct"] == 82.0  # 0.40+0.25+0.17 of 1.00
assert partial_candidate["score"] == 80.0
assert partial_candidate["missing_inputs"] == ["knowledge_score"]
assert partial_report["strategies"][0]["status"] == "PARTIAL"

# Universe ticker without any record is reported, not invented.
missing_ticker_report = engine.compare(
    strategy_ids=["atlas-baseline-v1"],
    recommendations=[full_record("AAPL", 80)],
    paper_fund_state={**STATE, "watchlist": ["AAPL", "ZZZZ"]},
    now=NOW,
)
explain = missing_ticker_report["strategies"][0]["explainability"]
assert explain["missing_tickers"] == ["ZZZZ"]
assert missing_ticker_report["strategies"][0]["status"] == "PARTIAL"


# ---------------------------------------------------------------------------
# Read-only guarantee: comparison performs no database writes.
# ---------------------------------------------------------------------------
import database.repository as repository

WRITE_FUNCTIONS = [
    name for name in dir(repository)
    if name.startswith(("save_", "add_", "update_", "delete_", "reset_"))
]
calls = []


def spy(name):
    def _record(*args, **kwargs):
        calls.append(name)
        raise AssertionError(f"Comparison must not call repository.{name}")
    return _record


originals = {name: getattr(repository, name) for name in WRITE_FUNCTIONS}
try:
    for name in WRITE_FUNCTIONS:
        setattr(repository, name, spy(name))
    engine.compare(
        recommendations=RECORDS,
        paper_fund_state=STATE,
        approved_tickers=["AAPL"],
        now=NOW,
    )
finally:
    for name, original in originals.items():
        setattr(repository, name, original)

assert calls == [], f"Unexpected repository writes: {calls}"

print("StrategyComparisonEngine test passed.")
