import json
import os
import tempfile
from datetime import datetime, timedelta
from types import SimpleNamespace

import database.connection as connection
from database.migrator import run_migrations
from database.repository import (
    get_latest_recommendation_for_ticker,
    save_dashboard_run,
    save_recommendations,
)
from engines.committee_engine import CommitteeEngine
from engines.live_paper_fund_engine import LivePaperFundEngine
from engines.watchlist_research_engine import WatchlistResearchEngine
from models.investment_recommendation import InvestmentRecommendation


engine = WatchlistResearchEngine()
NOW = datetime(2026, 7, 5, 12, 0, 0)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
class _FakeMarketEngine:
    def __init__(self, tickers):
        self._tickers = tickers

    def analyze_market(self, tickers):
        return [
            SimpleNamespace(ticker=ticker, rsi=50, volatility=1.0)
            for ticker in tickers
            if ticker in self._tickers
        ]


class _FakeRecommendationEngine:
    def build_recommendations(self, stocks):
        return [
            SimpleNamespace(ticker=stock.ticker, action="HOLD", confidence=60)
            for stock in stocks
        ]


class _FakeDashboardEngine:
    def build_dashboard(self, stocks, recommendations):
        return SimpleNamespace(
            market_status="open", average_rsi=50.0, average_volatility=1.0
        )


class _CapturingSavers(dict):
    def __init__(self):
        self.run_saved = None
        self.recommendations_saved = None
        super().__init__(
            run=self._save_run, recommendations=self._save_recommendations
        )

    def _save_run(self, dashboard):
        self.run_saved = dashboard
        return 101

    def _save_recommendations(self, run_id, recommendations, entry_contexts=None):
        # entry_contexts is accepted for signature compatibility with the real
        # saver and captured so tests can assert on it; this mock persists nothing.
        self.recommendations_saved = (run_id, list(recommendations))
        self.entry_contexts_saved = entry_contexts
        return [201 + index for index, _ in enumerate(recommendations)]


def generate(**overrides):
    kwargs = {
        "market_engine": _FakeMarketEngine({"AAA", "BBB"}),
        "recommendation_engine": _FakeRecommendationEngine(),
        "dashboard_engine": _FakeDashboardEngine(),
        "provider_resolver": lambda: "yahoo",
        "state_loader": lambda: None,
        "approved_tickers": [],
        "savers": _CapturingSavers(),
        "now": NOW,
    }
    kwargs.update(overrides)
    return engine.generate(**kwargs), kwargs["savers"]


# ---------------------------------------------------------------------------
# Provider gate: mock/test/unknown providers are refused, nothing written.
# ---------------------------------------------------------------------------
for unsafe in ("mock", "test", "unknown", "", None, "mock_history", "test_live"):
    refused, savers = generate(
        tickers=["AAA"], provider_resolver=lambda unsafe=unsafe: unsafe
    )
    assert refused["status"] == "REFUSED", unsafe
    assert "not a real provider" in refused["reason"]
    assert refused["run_id"] is None
    assert refused["recommendations"] == []
    assert savers.run_saved is None
    assert savers.recommendations_saved is None
assert engine._provider_is_real("yahoo") is True


# ---------------------------------------------------------------------------
# Ticker resolution: explicit > paper-fund watchlist > APPROVED_TICKERS.
# ---------------------------------------------------------------------------
explicit, _ = generate(tickers=["bbb", "AAA", "aaa "])
assert explicit["ticker_source"] == "explicit"
assert explicit["tickers_requested"] == ["AAA", "BBB"]  # normalized, deduped

watchlist_run, _ = generate(
    state_loader=lambda: {"fund_status": "READY", "watchlist": ["AAA"]},
)
assert watchlist_run["ticker_source"] == "paper_fund_watchlist"
assert watchlist_run["tickers_requested"] == ["AAA"]

# An OFF fund's watchlist is ignored in favor of approved tickers.
approved_run, _ = generate(
    state_loader=lambda: {"fund_status": "OFF", "watchlist": ["AAA"]},
    approved_tickers=["BBB"],
)
assert approved_run["ticker_source"] == "approved_tickers"
assert approved_run["tickers_requested"] == ["BBB"]

nothing, savers = generate(state_loader=lambda: None, approved_tickers=[])
assert nothing["status"] == "NOT_EVALUATED"
assert "No tickers to analyze" in nothing["reason"]
assert savers.run_saved is None


# ---------------------------------------------------------------------------
# Completed run: persists via savers; failures are skipped with reasons.
# ---------------------------------------------------------------------------
completed, savers = generate(tickers=["AAA", "BBB", "ZZZZ"])
assert completed["status"] == "COMPLETED"
assert completed["run_id"] == 101
assert completed["tickers_analyzed"] == ["AAA", "BBB"]
assert completed["skipped"] == [{
    "ticker": "ZZZZ",
    "reason": (
        "Market analysis unavailable: no or insufficient price history "
        "from the provider."
    ),
}]
assert completed["recommendation_count"] == 2
assert completed["recommendation_ids"] == [201, 202]
assert savers.recommendations_saved[0] == 101
assert len(savers.recommendations_saved[1]) == 2
assert completed["policy"]["manual_only"] is True
assert completed["policy"]["llm_decisions"] is False
assert completed["policy"]["modifies_live_paper_fund"] is False

# Nothing analyzable -> NOT_EVALUATED, nothing persisted.
none_analyzed, savers = generate(tickers=["ZZZZ"])
assert none_analyzed["status"] == "NOT_EVALUATED"
assert none_analyzed["skipped"][0]["ticker"] == "ZZZZ"
assert savers.run_saved is None

# Determinism: identical inputs -> identical report.
report_one, _ = generate(tickers=["AAA", "BBB"])
report_two, _ = generate(tickers=["AAA", "BBB"])
assert json.dumps(report_one, sort_keys=True) == json.dumps(report_two, sort_keys=True)


# ---------------------------------------------------------------------------
# Hidden mock substitution regression: provider configured as yahoo but Yahoo
# data actually unavailable -> the REAL pipeline analyzes nothing and no
# mock-backed recommendations are ever persisted under the yahoo identity.
# ---------------------------------------------------------------------------
import builtins

import market.data as market_data
from engines.market_engine import MarketEngine

_original_import = builtins.__import__


def _no_yfinance(name, *args, **kwargs):
    if name == "yfinance":
        raise ImportError("yfinance unavailable in deterministic test")
    return _original_import(name, *args, **kwargs)


_original_data_provider = market_data.DATA_PROVIDER
builtins.__import__ = _no_yfinance
market_data.DATA_PROVIDER = "yahoo"
try:
    yahoo_down, savers = generate(
        tickers=["AAPL"],
        market_engine=MarketEngine(),
        provider_resolver=lambda: "yahoo",
    )
finally:
    builtins.__import__ = _original_import
    market_data.DATA_PROVIDER = _original_data_provider

assert yahoo_down["status"] == "NOT_EVALUATED"
assert yahoo_down["run_id"] is None
assert yahoo_down["recommendation_count"] == 0
assert yahoo_down["recommendations"] == []
assert yahoo_down["skipped"][0]["ticker"] == "AAPL"
assert savers.run_saved is None
assert savers.recommendations_saved is None


# ---------------------------------------------------------------------------
# Stored-recommendation freshness rules on the paper fund's research lookup.
# ---------------------------------------------------------------------------
import database.repository as repository

fund_engine = LivePaperFundEngine()
original_lookup = repository.get_latest_recommendation_for_ticker
try:
    repository.get_latest_recommendation_for_ticker = lambda ticker: None
    record, reason = fund_engine._stored_recommendation("AAA", NOW)
    assert record is None and reason == "none stored"

    repository.get_latest_recommendation_for_ticker = (
        lambda ticker: {"ticker": "AAA", "action": "BUY", "run_time": None}
    )
    record, reason = fund_engine._stored_recommendation("AAA", NOW)
    assert record is None and "no run time" in reason

    stale_time = (NOW - timedelta(days=8)).isoformat()
    repository.get_latest_recommendation_for_ticker = (
        lambda ticker: {"ticker": "AAA", "action": "BUY", "run_time": stale_time}
    )
    record, reason = fund_engine._stored_recommendation("AAA", NOW)
    assert record is None and "stale" in reason

    fresh_time = (NOW - timedelta(days=1)).isoformat()
    repository.get_latest_recommendation_for_ticker = (
        lambda ticker: {"ticker": "AAA", "action": "BUY", "run_time": fresh_time}
    )
    record, reason = fund_engine._stored_recommendation("AAA", NOW)
    assert record is not None and reason is None

    def _broken(ticker):
        raise RuntimeError("no such table")

    repository.get_latest_recommendation_for_ticker = _broken
    record, reason = fund_engine._stored_recommendation("AAA", NOW)
    assert record is None and "lookup unavailable" in reason
finally:
    repository.get_latest_recommendation_for_ticker = original_lookup


# ---------------------------------------------------------------------------
# GOLDEN TEST: identical paper-fund cycles with and without stored
# recommendations produce IDENTICAL construction, orders, and risk decisions
# — proving zero trading-behavior change. Only the research snapshots differ.
# ---------------------------------------------------------------------------
class _ValidatedTestPriceManager:
    provider_name = "test_live_prices"

    def __init__(self, prices):
        self._prices = prices

    def market_status(self, as_of=None):
        return {"is_open": True, "session": "open", "as_of": str(as_of)}

    def latest_prices(self, tickers, use_cache=True):
        prices = {ticker: self._prices[ticker] for ticker in tickers}
        return {
            "requested_provider": self.provider_name,
            "prices": prices,
            "results": {
                ticker: {
                    "provider": self.provider_name,
                    "fallback_used": False,
                    "validated": True,
                }
                for ticker in tickers
            },
            "fallback_used": False,
            "validated": True,
            "as_of": "2026-07-05T10:00:00",
        }


SAVE_DEFAULTS = {
    "reasons": [], "risks": [], "score": 0, "portfolio_score": 60,
    "risk_score": 70, "forecast_direction": "flat", "forecast_confidence": 60,
    "expected_change": 0.0, "rating": "Neutral", "news_sentiment": "Neutral",
    "headline_count": 0, "news_summary": "", "signal_label": "OK",
    "false_positive_warnings": [], "evidence_breakdown": [],
    "confidence_metadata": [], "validation_status": "Pending", "fusion": {},
    "fusion_summary": "", "committee_members": [], "committee_bull_case": [],
    "committee_bear_case": [], "committee_neutral_case": [],
    "bullish_members": [], "bearish_members": [], "neutral_members": [],
    "strongest_bull_argument": "", "strongest_bear_argument": "",
    "main_disagreement": "", "final_committee_summary": "",
    "top_positive_factors": [], "top_negative_factors": [],
    "missing_evidence": [], "suggested_follow_up_research": [],
    "confidence_explanation": "", "evidence_summary": "", "assumptions": [],
    "strongest_assumption": "", "weakest_assumption": "",
    "counterfactuals": [], "recommendation_flip_conditions": [],
    "confidence_drivers": [], "executive_review": {},
    "executive_status": "READY", "executive_confidence": 70,
    "executive_summary": "", "executive_warnings": [],
    "executive_strengths": [], "executive_weaknesses": [],
    "required_follow_up_research": [], "stability_level": "Stable",
    "most_sensitive_factor": "", "stability_explanation": "",
    "knowledge_level": "Good Knowledge", "knowledge_explanation": "",
    "research_memory_report": {},
}


def stored_recommendation(ticker, action, confidence):
    recommendation = InvestmentRecommendation(
        ticker=ticker, action=action, confidence=confidence
    )
    for key, value in SAVE_DEFAULTS.items():
        setattr(recommendation, key, value)
    recommendation.overall_conviction = confidence
    recommendation.overall_score = confidence
    recommendation.technical_score = confidence
    recommendation.fundamental_score = confidence
    recommendation.forecast_score = confidence
    recommendation.news_confidence = confidence
    recommendation.signal_quality_score = 8
    recommendation.committee_agreement = confidence
    recommendation.stability_score = confidence
    recommendation.knowledge_score = confidence
    return recommendation


WATCHLIST = ["AAA", "BBB"]
PRICES = {"AAA": 100.0, "BBB": 50.0}
START = datetime.now()
CYCLE_AT = START + timedelta(minutes=1)


def run_isolated_cycle(seed_recommendations):
    """Fresh temp DB -> optional stored records -> one identical fund cycle."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as handle:
        path = handle.name
    original_path = connection.DATABASE_PATH
    try:
        connection.DATABASE_PATH = path
        connection._wal_initialized_paths.discard(path)
        run_migrations()
        if seed_recommendations:
            run_id = save_dashboard_run(SimpleNamespace(
                market_status="open", average_rsi=50.0, average_volatility=1.0
            ))
            save_recommendations(run_id, seed_recommendations)
        fund = LivePaperFundEngine()
        fund.start(WATCHLIST, starting_cash=100000, now=START)
        result = fund.run_cycle(
            manager=_ValidatedTestPriceManager(PRICES), now=CYCLE_AT
        )
        committee_record = get_latest_recommendation_for_ticker("AAA")
        return result, committee_record
    finally:
        connection.DATABASE_PATH = original_path
        connection._wal_initialized_paths.discard(path)
        os.unlink(path)


baseline_result, _ = run_isolated_cycle(None)
seeded_result, seeded_record = run_isolated_cycle([
    stored_recommendation("AAA", "BUY", 88),
    stored_recommendation("BBB", "AVOID", 30),
])

# Trading behavior is IDENTICAL with and without stored recommendations.
assert baseline_result["cycle_status"] == seeded_result["cycle_status"] == "COMPLETED"
assert baseline_result["orders"] == seeded_result["orders"]
assert baseline_result["risk_summary"] == seeded_result["risk_summary"]
assert baseline_result["construction_summary"] == seeded_result["construction_summary"]
assert (
    baseline_result["snapshot"]["portfolio_value"]
    == seeded_result["snapshot"]["portfolio_value"]
)

# Only the research snapshots differ: real stored actions vs HOLD fallback.
baseline_snapshots = {r["ticker"]: r for r in baseline_result["recommendations"]}
seeded_snapshots = {r["ticker"]: r for r in seeded_result["recommendations"]}
for ticker in WATCHLIST:
    assert baseline_snapshots[ticker]["status"] == "LIVE_PAPER_SNAPSHOT"
    assert baseline_snapshots[ticker]["action"] == "HOLD"
    assert "No usable stored recommendation" in baseline_snapshots[ticker]["reason"]
    assert seeded_snapshots[ticker]["status"] == "STORED_RECOMMENDATION"
    assert seeded_snapshots[ticker]["price"] == PRICES[ticker]
assert seeded_snapshots["AAA"]["action"] == "BUY"
assert seeded_snapshots["AAA"]["confidence"] == 88
assert seeded_snapshots["AAA"]["recommendation_id"] is not None
assert seeded_snapshots["BBB"]["action"] == "AVOID"


# ---------------------------------------------------------------------------
# End-to-end: the persisted record powers the committee with full quorum.
# ---------------------------------------------------------------------------
assert seeded_record is not None
assert seeded_record["run_time"] is not None
committee = CommitteeEngine().evaluate(seeded_record)
assert committee["status"] in {"EVALUATED", "PARTIAL"}
assert committee["agreement"]["voting_members"] >= CommitteeEngine().quorum
assert committee["committee_recommendation"]["action"] in {"BUY", "HOLD", "AVOID"}


# ---------------------------------------------------------------------------
# API endpoint: refuses on a mock provider with nothing written (status 200).
# ---------------------------------------------------------------------------
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)
original_env = os.environ.get("MARKET_DATA_PROVIDER")
try:
    os.environ["MARKET_DATA_PROVIDER"] = "mock"
    response = client.post("/recommendations/generate", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REFUSED"
    assert body["run_id"] is None
    assert body["policy"]["requires_real_provider"] is True

    explicit_response = client.post(
        "/recommendations/generate", json={"tickers": ["AAPL"]}
    )
    assert explicit_response.json()["status"] == "REFUSED"
finally:
    if original_env is None:
        os.environ.pop("MARKET_DATA_PROVIDER", None)
    else:
        os.environ["MARKET_DATA_PROVIDER"] = original_env

print("WatchlistResearchEngine test passed.")
