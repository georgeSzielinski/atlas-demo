"""Tests for Sprint 1B.1: recommendation entry-context capture and
paper-order-to-recommendation linkage.

Deterministic and offline, against throwaway temporary databases (never
database/atlas.db). Covers: observed vs deferred entry capture, no duplicate
market fetch, legacy save_recommendations compatibility, returned recommendation
ids, exact-causality order linkage, unrelated/rebalance orders left unlinked,
ambiguity-free identity when a ticker has multiple recommendations,
INSERT-OR-REPLACE linkage preservation, and that linkage never alters any other
order field or the recommendation action/confidence.
"""

import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace

import database.connection as connection
from database.connection import get_connection
from database.migrator import run_migrations
from database.repository import (
    save_dashboard_run,
    save_recommendations,
    save_paper_fund_order,
    link_order_to_recommendation,
    get_latest_recommendation_for_ticker,
)
from engines.watchlist_research_engine import WatchlistResearchEngine
from engines.live_paper_fund_engine import LivePaperFundEngine
from models.investment_recommendation import InvestmentRecommendation


@contextmanager
def temp_database():
    original = connection.DATABASE_PATH
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as handle:
        path = handle.name
    connection.DATABASE_PATH = path
    connection._wal_initialized_paths.discard(path)
    try:
        run_migrations()
        yield path
    finally:
        connection.DATABASE_PATH = original
        connection._wal_initialized_paths.discard(path)
        for candidate in (path, f"{path}-wal", f"{path}-shm"):
            if os.path.exists(candidate):
                os.remove(candidate)


def _recommendation_row(ticker):
    db = get_connection()
    try:
        return db.execute(
            "SELECT action, confidence, created_at, entry_at, entry_price, "
            "entry_price_source, entry_validated, entry_fallback_used, entry_status, "
            "market_regime, sector, expected_horizon_days, outcome_state, "
            "outcome_schema_version FROM recommendations WHERE ticker = ? "
            "ORDER BY id DESC LIMIT 1",
            (ticker,),
        ).fetchone()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Entry capture: engine helper (pure) decides OBSERVED vs DEFERRED honestly.
# ---------------------------------------------------------------------------
_engine = WatchlistResearchEngine()
_moment = datetime(2026, 7, 5, 12, 0, 0)

observed = _engine._entry_contexts(
    [SimpleNamespace(ticker="AAA", price=150.0)], "yahoo", _moment
)["AAA"]
assert observed["entry_status"] == "OBSERVED"
assert observed["outcome_state"] == "PENDING"
assert observed["entry_price"] == 150.0
assert observed["entry_price_source"] == "yahoo"
assert observed["entry_validated"] is True
assert observed["entry_fallback_used"] is None
assert observed["entry_at"] == _moment.isoformat()
# Never invented when the cycle does not compute them:
assert observed["market_regime"] is None
assert observed["sector"] is None
assert observed["expected_horizon_days"] is None

for bad_price in (0.0, None, -5.0, float("nan"), float("inf")):
    deferred = _engine._entry_contexts(
        [SimpleNamespace(ticker="BBB", price=bad_price)], "yahoo", _moment
    )["BBB"]
    assert deferred["entry_status"] == "DEFERRED", bad_price
    assert deferred["outcome_state"] == "DEFERRED"
    assert deferred["entry_price"] is None
    assert deferred["entry_price_source"] is None
    assert deferred["entry_validated"] is None


# ---------------------------------------------------------------------------
# Entry capture: save_recommendations persists context; legacy calls stay NULL.
# ---------------------------------------------------------------------------
with temp_database():
    run_id = save_dashboard_run(
        SimpleNamespace(market_status="open", average_rsi=50.0, average_volatility=1.0)
    )
    contexts = _engine._entry_contexts(
        [SimpleNamespace(ticker="AAA", price=150.0),
         SimpleNamespace(ticker="BBB", price=0.0)],
        "yahoo",
        _moment,
    )
    ids = save_recommendations(
        run_id,
        [InvestmentRecommendation(ticker="AAA", action="BUY", confidence=77),
         InvestmentRecommendation(ticker="BBB", action="HOLD", confidence=55)],
        entry_contexts=contexts,
    )
    assert len(ids) == 2
    db = get_connection()
    try:
        inserted = db.execute(
            "SELECT id, ticker FROM recommendations WHERE run_id = ? ORDER BY id",
            (run_id,),
        ).fetchall()
    finally:
        db.close()
    assert inserted == [(ids[0], "AAA"), (ids[1], "BBB")]

    aaa = _recommendation_row("AAA")
    assert aaa[0] == "BUY" and aaa[1] == 77  # action/confidence untouched
    assert aaa[2] is not None  # created_at set
    assert aaa[3] == _moment.isoformat()  # entry_at
    assert aaa[4] == 150.0  # entry_price
    assert aaa[5] == "yahoo"  # entry_price_source
    assert aaa[6] == 1  # entry_validated
    assert aaa[7] is None  # analyzer exposes no per-price fallback lineage
    assert aaa[8] == "OBSERVED"
    assert aaa[9] is None and aaa[10] is None and aaa[11] is None  # regime/sector/horizon
    assert aaa[12] == "PENDING" and aaa[13] == 1  # outcome_state / schema_version

    bbb = _recommendation_row("BBB")
    assert bbb[0] == "HOLD" and bbb[1] == 55
    assert bbb[2] is not None  # created_at still stamped
    assert bbb[4] is None and bbb[5] is None  # deferred: null price/source
    assert bbb[8] == "DEFERRED" and bbb[12] == "DEFERRED"


with temp_database():
    # Legacy caller (no entry_contexts) is unchanged: all new columns NULL.
    run_id = save_dashboard_run(
        SimpleNamespace(market_status="open", average_rsi=50.0, average_volatility=1.0)
    )
    ids = save_recommendations(
        run_id, [InvestmentRecommendation(ticker="AAA", action="BUY", confidence=77)]
    )
    assert ids and len(ids) == 1  # ids still returned
    row = _recommendation_row("AAA")
    assert row[0] == "BUY" and row[1] == 77
    assert row[2] is None  # created_at NULL (legacy)
    assert all(value is None for value in row[3:13])  # every new column NULL


with temp_database():
    # Same ticker across runs stays unambiguous by returned row id + run id.
    run_one = save_dashboard_run(
        SimpleNamespace(market_status="open", average_rsi=50.0, average_volatility=1.0)
    )
    first_id = save_recommendations(
        run_one, [InvestmentRecommendation(ticker="AAA", action="BUY", confidence=60)]
    )[0]
    run_two = save_dashboard_run(
        SimpleNamespace(market_status="open", average_rsi=50.0, average_volatility=1.0)
    )
    second_id = save_recommendations(
        run_two, [InvestmentRecommendation(ticker="AAA", action="BUY", confidence=90)]
    )[0]
    assert first_id != second_id
    db = get_connection()
    try:
        rows = db.execute(
            "SELECT id, run_id, confidence FROM recommendations "
            "WHERE id IN (?, ?) ORDER BY id",
            (first_id, second_id),
        ).fetchall()
    finally:
        db.close()
    assert rows == [(first_id, run_one, 60), (second_id, run_two, 90)]


# ---------------------------------------------------------------------------
# Entry capture integration: generate() reuses the cycle's price (no 2nd fetch)
# and never changes the recommendation action/confidence.
# ---------------------------------------------------------------------------
class _PricedStock:
    def __init__(self, ticker, price):
        self.ticker = ticker
        self.price = price


class _CountingMarketEngine:
    def __init__(self):
        self.calls = 0

    def analyze_market(self, tickers):
        self.calls += 1
        return [_PricedStock(ticker, 150.0) for ticker in tickers]


class _BuyRecommendationEngine:
    def build_recommendations(self, stocks):
        return [
            InvestmentRecommendation(ticker=stock.ticker, action="BUY", confidence=77)
            for stock in stocks
        ]


class _StubDashboardEngine:
    def build_dashboard(self, stocks, recommendations):
        return SimpleNamespace(
            market_status="open", average_rsi=50.0, average_volatility=1.0
        )


with temp_database():
    market = _CountingMarketEngine()
    result = WatchlistResearchEngine().generate(
        tickers=["AAA"],
        market_engine=market,
        recommendation_engine=_BuyRecommendationEngine(),
        dashboard_engine=_StubDashboardEngine(),
        provider_resolver=lambda: "yahoo",
        state_loader=lambda: None,
        approved_tickers=["AAA"],
        now=_moment,
    )
    assert result["status"] == "COMPLETED"
    assert len(result["recommendation_ids"]) == 1
    assert market.calls == 1  # exactly one fetch: entry capture reused it

    row = _recommendation_row("AAA")
    assert row[0] == "BUY" and row[1] == 77  # action/confidence unchanged
    assert row[4] == 150.0 and row[5] == "yahoo"  # entry price + real source
    assert row[6] == 1 and row[8] == "OBSERVED" and row[12] == "PENDING"


# ---------------------------------------------------------------------------
# Order linkage: rebalance orders remain unlinked because stored research is
# normalized to HOLD before construction and is not causally used by orders.
# ---------------------------------------------------------------------------
class _ValidatedTestPriceManager:
    provider_name = "test_live_prices"

    def __init__(self, prices):
        self._prices = prices

    def market_status(self, as_of=None):
        return {"is_open": True, "session": "open", "as_of": str(as_of)}

    def latest_prices(self, tickers, use_cache=True):
        return {
            "requested_provider": self.provider_name,
            "prices": {ticker: self._prices[ticker] for ticker in tickers},
            "results": {
                ticker: {"provider": self.provider_name, "fallback_used": False, "validated": True}
                for ticker in tickers
            },
            "fallback_used": False,
            "validated": True,
            "as_of": "2026-07-05T10:00:00",
        }


WATCHLIST = ["AAA", "BBB"]
PRICES = {"AAA": 100.0, "BBB": 50.0}


def _seed_recommendation(ticker, action, confidence):
    run_id = save_dashboard_run(
        SimpleNamespace(market_status="open", average_rsi=50.0, average_volatility=1.0)
    )
    save_recommendations(
        run_id, [InvestmentRecommendation(ticker=ticker, action=action, confidence=confidence)]
    )


def _orders_by_ticker():
    db = get_connection()
    try:
        rows = db.execute(
            "SELECT ticker, side, quantity, fill_price, status, recommendation_id "
            "FROM paper_fund_orders"
        ).fetchall()
    finally:
        db.close()
    return {row[0]: row for row in rows}


with temp_database():
    _seed_recommendation("AAA", "BUY", 88)
    start = datetime.now()
    fund = LivePaperFundEngine()
    fund.start(WATCHLIST, starting_cash=100000, now=start)
    fund.run_cycle(manager=_ValidatedTestPriceManager(PRICES), now=start + timedelta(minutes=1))

    orders = _orders_by_ticker()
    assert "AAA" in orders, "expected a rebalancing order for the seeded ticker"
    assert orders["AAA"][5] is None
    if "BBB" in orders:
        assert orders["BBB"][5] is None  # no stored recommendation -> unlinked


# Exact eligibility requires ticker + persisted id + run id from the same cycle
# snapshot; ticker alone, a mismatched run, or absent causal metadata never links.
fund = LivePaperFundEngine()
snapshots = [{"ticker": "AAA", "recommendation_id": 22, "run_id": 7}]
assert fund._exact_order_recommendation_id(
    {"ticker": "AAA", "recommendation_id": 22, "recommendation_run_id": 7},
    snapshots,
) == 22
assert fund._exact_order_recommendation_id(
    {"ticker": "AAA", "recommendation_id": 22, "recommendation_run_id": 8},
    snapshots,
) is None
assert fund._exact_order_recommendation_id({"ticker": "AAA"}, snapshots) is None


# ---------------------------------------------------------------------------
# Order writer: INSERT OR REPLACE preserves linkage; linkage alters no other field.
# ---------------------------------------------------------------------------
with temp_database():
    _seed_recommendation("AAA", "BUY", 88)
    rec_id = get_latest_recommendation_for_ticker("AAA")["id"]

    base_order = {
        "order_id": "o-1", "cycle_id": "c1", "ticker": "AAA", "side": "BUY",
        "quantity": 10, "status": "FILLED_SIMULATED", "fill_price": 100.0,
        "price_source": "test_live_prices", "validated": True, "simulated": True,
        "reason": "rebalance", "policy": {"paper": True}, "recommendation_id": rec_id,
    }
    save_paper_fund_order(base_order)

    def _order(order_id):
        db = get_connection()
        try:
            return db.execute(
                "SELECT recommendation_id, side, quantity, fill_price, status, "
                "price_source, validated, simulated FROM paper_fund_orders WHERE order_id = ?",
                (order_id,),
            ).fetchone()
        finally:
            db.close()

    assert _order("o-1")[0] == rec_id

    # Re-save the SAME order omitting recommendation_id -> linkage preserved,
    # and no other field changed.
    resave = dict(base_order)
    resave.pop("recommendation_id")
    save_paper_fund_order(resave)
    after = _order("o-1")
    assert after[0] == rec_id  # preserved through INSERT OR REPLACE
    assert after[1:] == ("BUY", 10, 100.0, "FILLED_SIMULATED", "test_live_prices", 1, 1)

    # An unrelated order never linked stays null.
    save_paper_fund_order({
        "order_id": "o-2", "cycle_id": "c1", "ticker": "ZZZ", "side": "BUY",
        "quantity": 1, "status": "FILLED_SIMULATED", "fill_price": 10.0,
        "validated": True, "simulated": True,
    })
    assert _order("o-2")[0] is None

    # A re-save that DOES provide a new recommendation_id updates it.
    _seed_recommendation("AAA", "BUY", 90)
    new_rec_id = get_latest_recommendation_for_ticker("AAA")["id"]
    relinked = dict(base_order)
    relinked["recommendation_id"] = new_rec_id
    save_paper_fund_order(relinked)
    assert _order("o-1")[0] == new_rec_id

    # A non-existent explicit id fails clearly and does not rewrite the order.
    invalid = dict(base_order)
    invalid["recommendation_id"] = 999999
    try:
        save_paper_fund_order(invalid)
        raise AssertionError("invalid recommendation id must be rejected")
    except ValueError as error:
        assert "does not exist" in str(error)
    assert _order("o-1")[0] == new_rec_id

    # The 1A narrow-link helper still works and touches only recommendation_id.
    assert link_order_to_recommendation("o-2", rec_id)["linked"] is True
    assert _order("o-2")[0] == rec_id
    assert _order("o-2")[1:] == ("BUY", 1, 10.0, "FILLED_SIMULATED", None, 1, 1)


print("Entry-capture and order-linkage tests passed.")
