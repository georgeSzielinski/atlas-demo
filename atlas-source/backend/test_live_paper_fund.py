import os
import tempfile
from datetime import datetime, timedelta

from fastapi import HTTPException

import database.connection as connection
from api.main import (
    app,
    paper_fund_cycle,
    paper_fund_pause,
    paper_fund_reset,
    paper_fund_resume,
    paper_fund_start,
    paper_fund_status,
    paper_fund_stop,
)
from database.repository import (
    get_recent_risk_decisions,
    get_paper_fund_orders,
    get_paper_fund_snapshots,
    get_paper_portfolio_history,
    get_paper_trades,
)
from database.migrator import run_migrations
from engines.live_paper_fund_engine import LivePaperFundEngine
from engines.paper_trading_engine import PaperTradingEngine


class _ValidatedTestPriceManager:
    """Test fixture: a real-provider-shaped manager with validated prices."""

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
            "as_of": "2026-07-01T10:00:00",
        }


class _MockPriceManager(_ValidatedTestPriceManager):
    """Test fixture: reports the mock provider, which the fund must reject."""

    def latest_prices(self, tickers, use_cache=True):
        report = super().latest_prices(tickers, use_cache=use_cache)
        for result in report["results"].values():
            result["provider"] = "mock"
        return report


class _UnvalidatedPriceManager(_ValidatedTestPriceManager):
    """Test fixture: prices that failed validation."""

    def latest_prices(self, tickers, use_cache=True):
        report = super().latest_prices(tickers, use_cache=use_cache)
        report["validated"] = False
        return report


# Deterministic identical return streams -> perfectly correlated (1.0) symbols.
CORR_RETURNS = [
    0.01, -0.02, 0.015, 0.02, -0.01, 0.03, -0.015, 0.02, 0.01, -0.02,
    0.025, -0.01, 0.02, 0.015, -0.025, 0.01, 0.02, -0.015, 0.03, -0.01,
    0.02, -0.02, 0.015,
]


def corr_history_rows(symbols, returns=CORR_RETURNS, start="2026-01-05"):
    origin = datetime.strptime(start, "%Y-%m-%d")
    rows = []
    for symbol in symbols:
        close = 100.0
        rows.append({"ticker": symbol, "date": origin.strftime("%Y-%m-%d"), "close": close})
        for index, value in enumerate(returns):
            close = close * (1 + value)
            date = (origin + timedelta(days=index + 1)).strftime("%Y-%m-%d")
            rows.append({"ticker": symbol, "date": date, "close": close})
    return rows


class _CorrelationPriceManager(_ValidatedTestPriceManager):
    """Test fixture: real-provider-shaped manager that also serves price-backed
    historical rows so correlation evidence can be evaluated."""

    provider_name = "yahoo"

    def __init__(self, prices, rows):
        super().__init__(prices)
        self._rows = rows

    def historical_prices(self, tickers, start_date, end_date, adapter=None):
        wanted = {str(ticker).upper() for ticker in tickers}
        rows = [row for row in self._rows if row["ticker"] in wanted]
        return {
            "requested_provider": "yahoo",
            "rows": rows,
            "fallback_used": False,
            "validated": bool(rows),
        }


class _FallbackHistoryManager(_CorrelationPriceManager):
    """Test fixture: historical rows that fell back to non-real data."""

    def historical_prices(self, tickers, start_date, end_date, adapter=None):
        report = super().historical_prices(tickers, start_date, end_date)
        report["fallback_used"] = True
        return report


original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()
    engine = LivePaperFundEngine()

    # No fake demo data: an untouched fund is OFF and empty.
    status = paper_fund_status()
    assert status["fund_status"] == "OFF"
    assert status["mode"] == "live_paper_fund"
    assert status["open_positions"] == {}
    assert status["virtual_orders"] == []
    assert status["snapshots"] == []
    assert status["latest_snapshot"] is None
    assert status["cash"] is None

    # Cycles are impossible before the fund starts.
    try:
        engine.run_cycle(manager=_ValidatedTestPriceManager({}))
        raise AssertionError("cycle must fail when the fund is OFF")
    except ValueError as error:
        assert "not started" in str(error)

    # Start the fund through the API.
    started = paper_fund_start(payload={
        "watchlist": ["AAPL", "MSFT"],
        "starting_cash": 100000,
        "interval_minutes": 30,
    })
    assert started["state"]["fund_status"] == "READY"
    assert started["state"]["watchlist"] == ["AAPL", "MSFT"]
    assert started["state"]["cash"] == 100000
    assert started["status"]["policy"]["broker_disabled"] is True
    assert started["status"]["policy"]["real_money"] is False
    assert started["status"]["policy"]["execution"] == "simulated_only"
    assert started["status"]["policy"]["human_approval_required_for_real_trading"] is True

    # Market data must be validated and real: mock provider fails loudly.
    mock_cycle = engine.run_cycle(
        manager=_MockPriceManager({"AAPL": 100.0, "MSFT": 200.0}),
        now="2026-07-01T10:00:00",
    )
    assert mock_cycle["cycle_status"] == "FAILED"
    assert mock_cycle["fund_status"] == "ERROR"
    assert mock_cycle["orders"] == []
    assert mock_cycle["snapshot"] is None
    assert "mock/demo prices are not allowed" in mock_cycle["error"]
    assert get_paper_fund_orders(limit=10) == []
    assert paper_fund_status()["fund_status"] == "ERROR"
    assert paper_fund_status()["last_error"] == mock_cycle["error"]

    unvalidated_cycle = engine.run_cycle(
        manager=_UnvalidatedPriceManager({"AAPL": 100.0, "MSFT": 200.0}),
        now="2026-07-01T10:05:00",
    )
    assert unvalidated_cycle["cycle_status"] == "FAILED"
    assert "failed validation" in unvalidated_cycle["error"]
    assert get_paper_fund_orders(limit=10) == []

    # Hidden mock substitution regression: a REAL MarketDataManager configured
    # for Yahoo with yfinance unavailable must never trade on mock prices
    # labeled as Yahoo. The manager reports the fallback honestly and the
    # cycle fails safely with no orders.
    import builtins

    from market.market_data_manager import MarketDataManager

    _original_import = builtins.__import__

    def _no_yfinance(name, *args, **kwargs):
        if name == "yfinance":
            raise ImportError("yfinance unavailable in deterministic test")
        return _original_import(name, *args, **kwargs)

    builtins.__import__ = _no_yfinance
    try:
        yahoo_down_cycle = engine.run_cycle(
            manager=MarketDataManager(provider_name="yahoo"),
            now="2026-07-01T10:10:00",
        )
    finally:
        builtins.__import__ = _original_import

    assert yahoo_down_cycle["cycle_status"] == "FAILED"
    assert yahoo_down_cycle["fund_status"] == "ERROR"
    assert yahoo_down_cycle["orders"] == []
    assert yahoo_down_cycle["snapshot"] is None
    assert "fallback" in yahoo_down_cycle["error"]
    assert "mock/demo prices are not allowed" in yahoo_down_cycle["error"]
    assert get_paper_fund_orders(limit=10) == []

    # A validated real-provider cycle creates ONLY simulated orders from
    # PortfolioConstructionEngine target allocations and fills them at
    # validated prices.
    cycle = engine.run_cycle(
        manager=_ValidatedTestPriceManager({"AAPL": 100.0, "MSFT": 200.0}),
        now="2026-07-01T10:30:00",
    )
    assert cycle["cycle_status"] == "COMPLETED"
    assert cycle["fund_status"] == "RUNNING"
    assert cycle["price_backed"] is True
    assert cycle["price_provider"] == "test_live_prices"
    assert len(cycle["recommendations"]) == 2
    assert cycle["recommendations"][0]["status"] == "LIVE_PAPER_SNAPSHOT"
    construction = cycle["construction_summary"]
    assert construction["engine"] == "PortfolioConstructionEngine"
    allocation_by_ticker = {
        item["ticker"]: item for item in construction["recommended_allocations"]
    }
    assert allocation_by_ticker["AAPL"]["suggested_allocation"] == 17.5
    assert allocation_by_ticker["MSFT"]["suggested_allocation"] == 17.5
    assert allocation_by_ticker["AAPL"]["capital_required"] == 17500
    assert allocation_by_ticker["AAPL"]["capital_required"] != 50000
    assert len(cycle["orders"]) == 2
    assert cycle["risk_summary"]["proposed"] == 2
    assert cycle["risk_summary"]["approved"] == 2
    assert cycle["risk_summary"]["rejected"] == 0
    assert len(cycle["risk_summary"]["decision_ids"]) == 2
    # No historical price feed on this fixture -> correlation is NOT_EVALUATED
    # and never blocks (values are not fabricated).
    assert cycle["risk_summary"]["correlation"]["status"] == "NOT_EVALUATED"
    for order in cycle["orders"]:
        assert order["simulated"] is True
        assert order["status"] == "FILLED_SIMULATED"
        assert order["validated"] is True
        assert order["risk_decision_id"] in cycle["risk_summary"]["decision_ids"]
        assert order["price_source"] == "test_live_prices"
        assert order["policy"]["broker_disabled"] is True
        assert order["policy"]["real_money"] is False
    by_ticker = {order["ticker"]: order for order in cycle["orders"]}
    assert by_ticker["AAPL"]["side"] == "BUY"
    assert by_ticker["AAPL"]["quantity"] == 175  # $17,500 / $100
    assert by_ticker["AAPL"]["target_value"] == 17500
    assert by_ticker["MSFT"]["quantity"] == 87  # floor($17,500 / $200)
    assert by_ticker["MSFT"]["target_value"] == 17500
    snapshot = cycle["snapshot"]
    assert snapshot["portfolio_value"] == 100000
    assert snapshot["cash"] == 65100
    assert snapshot["total_return"] == 0
    assert snapshot["price_source"] == "test_live_prices"
    assert cycle["next_update"] == "2026-07-01T11:00:00"
    assert cycle["learning"]["lesson"]
    first_learning = cycle["learning"]["details"]["learning_summary"]
    assert first_learning["recommended_symbols"] == ["AAPL", "MSFT"]
    assert first_learning["bought_symbols"] == ["AAPL", "MSFT"]
    assert first_learning["sold_symbols"] == []
    assert first_learning["rejected_orders"] == []
    assert first_learning["portfolio"]["current_value"] == 100000
    assert first_learning["portfolio"]["value_change"] == 0
    assert "Approved simulated orders executed" in first_learning["what_worked"][0]
    assert first_learning["what_did_not_work"] == [
        "No deterministic issue recorded this cycle."
    ]
    assert any("Monitor largest paper position" in item for item in first_learning["watch_next"])
    assert first_learning["policy"] == {
        "descriptive_only": True,
        "does_not_modify_recommendations": True,
        "does_not_modify_trades": True,
        "paper_only": True,
        "real_money": False,
    }

    # Prices move: the next cycle updates portfolio value and rebalances toward
    # construction-derived allocations, not equal weight.
    second_cycle = engine.run_cycle(
        manager=_ValidatedTestPriceManager({"AAPL": 110.0, "MSFT": 200.0}),
        now="2026-07-01T11:00:00",
    )
    assert second_cycle["cycle_status"] == "COMPLETED"
    assert second_cycle["risk_summary"]["proposed"] == 2
    assert second_cycle["risk_summary"]["approved"] == 2
    assert second_cycle["risk_summary"]["rejected"] == 0
    second_orders = {order["ticker"]: order for order in second_cycle["orders"]}
    # Portfolio is $101,750; construction caps each ticker at 20%.
    assert second_orders["AAPL"]["side"] == "BUY"
    assert second_orders["AAPL"]["quantity"] == 10
    assert second_orders["AAPL"]["target_allocation"] == 20
    assert second_orders["MSFT"]["side"] == "BUY"
    assert second_orders["MSFT"]["quantity"] == 14
    assert second_orders["MSFT"]["target_allocation"] == 20
    second_snapshot = second_cycle["snapshot"]
    assert second_snapshot["portfolio_value"] == 101750
    assert second_snapshot["realized_pl"] == 0
    assert second_snapshot["unrealized_pl"] == 1750.01
    assert second_snapshot["total_return"] == 1.75
    assert second_snapshot["daily_return"] == 1.75
    second_learning = second_cycle["learning"]["details"]["learning_summary"]
    assert second_learning["bought_symbols"] == ["AAPL", "MSFT"]
    assert second_learning["sold_symbols"] == []
    assert second_learning["portfolio"]["value_change"] == 1750
    assert second_learning["portfolio"]["realized_pl"] == 0
    assert second_learning["portfolio"]["unrealized_pl"] == 1750.01

    fund_status = paper_fund_status()
    assert fund_status["fund_status"] == "RUNNING"
    assert fund_status["last_update"] == "2026-07-01T11:00:00"
    assert fund_status["next_update"] == "2026-07-01T11:30:00"
    assert fund_status["price_provider"] == "test_live_prices"
    assert len(fund_status["snapshots"]) == 2
    assert len(fund_status["open_positions"]) == 2
    assert fund_status["activity_log"]
    assert fund_status["learning_log"]
    persisted_learning = fund_status["learning_log"][0]["details"]["learning_summary"]
    assert persisted_learning == second_learning
    activity_types = {entry["activity_type"] for entry in fund_status["activity_log"]}
    assert "CYCLE_STARTED" in activity_types
    assert "PRICES_REFRESHED" in activity_types
    assert "CORRELATION_EVALUATED" in activity_types
    assert "ORDERS_FILLED" in activity_types
    assert "PORTFOLIO_UPDATED" in activity_types
    assert "ANALYTICS_UPDATED" in activity_types
    assert "CYCLE_COMPLETED" in activity_types
    assert fund_status["cycle_state"]["state"] == "Complete"
    assert fund_status["cycle_state"]["last_successful_cycle_time"] == "2026-07-01T11:00:00"
    assert fund_status["cycle_state"]["duration_seconds"] == 0
    history = fund_status["trading_history"]
    assert [point["portfolio_value"] for point in history["equity_curve"]] == [
        100000,
        101750,
    ]
    assert [point["cash"] for point in history["cash_history"]] == [65100, 61200]
    assert history["daily_pl"]["status"] == "EVALUATED"
    assert history["daily_pl"]["items"][0]["pl"] == 1750
    assert history["weekly_pl"]["status"] == "EVALUATED"
    assert history["monthly_pl"]["status"] == "EVALUATED"
    assert history["statistics"]["drawdown"]["status"] == "EVALUATED"
    assert history["statistics"]["win_rate"]["value"] == 100
    assert history["statistics"]["cagr"]["status"] == "NOT_EVALUATED"
    assert history["statistics"]["sharpe"]["status"] == "NOT_EVALUATED"
    journal = fund_status["cycle_journal"]["latest"]
    assert fund_status["cycle_journal"]["status"] == "EVALUATED"
    assert journal["cycle_id"] == second_cycle["cycle_id"]
    assert journal["market_conditions"]["session"] == "open"
    assert journal["recommendations_considered"] == ["AAPL", "MSFT"]
    assert {trade["symbol"] for trade in journal["accepted_trades"]} == {
        "AAPL",
        "MSFT",
    }
    assert journal["rejected_trades"] == []
    assert journal["portfolio_changes"]["current_value"] == 101750
    assert journal["learning_summary"]["what_worked"]
    assert journal["execution_time"]["duration_seconds"] == 0
    filled_activity = next(
        entry for entry in fund_status["activity_log"]
        if entry["activity_type"] == "ORDERS_FILLED"
    )
    assert "risk_summary" in filled_activity["details"]
    assert "construction_summary" in filled_activity["details"]

    risk_decisions = get_recent_risk_decisions(limit=10)
    assert len(risk_decisions) == 4
    assert {decision["verdict"] for decision in risk_decisions} == {"APPROVED"}
    assert all(decision["cycle_id"] for decision in risk_decisions)
    assert all(decision["policy"]["paper_only"] is True for decision in risk_decisions)

    # Pause blocks cycles; resume re-enables them.
    paused = paper_fund_pause()
    assert paused["state"]["fund_status"] == "PAUSED"
    try:
        engine.run_cycle(manager=_ValidatedTestPriceManager({"AAPL": 110.0, "MSFT": 200.0}))
        raise AssertionError("cycle must fail while paused")
    except ValueError as error:
        assert "paused" in str(error)
    resumed = paper_fund_resume()
    assert resumed["state"]["fund_status"] == "READY"

    # The live paper fund stays separate from historical replay: fund cycles
    # never write replay tables, and replays never write fund tables.
    assert get_paper_portfolio_history(limit=10) == []
    assert get_paper_trades(limit=10) == []
    fund_orders_before_replay = len(get_paper_fund_orders(limit=100))
    fund_snapshots_before_replay = len(get_paper_fund_snapshots(limit=100))
    replay = PaperTradingEngine().run_historical_price_replay(
        recommendations=[{"ticker": "AAPL", "action": "BUY"}],
        tickers=["AAPL"],
        historical_rows=[
            {"date": "2024-01-02", "ticker": "AAPL", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000},
            {"date": "2024-01-03", "ticker": "AAPL", "open": 110, "high": 111, "low": 109, "close": 110, "volume": 1000},
        ],
        persist=True,
    )
    assert replay["replay_status"] == "COMPLETED"
    assert len(get_paper_portfolio_history(limit=10)) == 2
    assert len(get_paper_fund_orders(limit=100)) == fund_orders_before_replay
    assert len(get_paper_fund_snapshots(limit=100)) == fund_snapshots_before_replay

    # No broker endpoints exist: no order/execute routes, no /paper-broker or
    # /paper-fund POST route that reaches a broker.
    route_paths = [getattr(route, "path", "") for route in app.routes]
    assert all("order" not in path.lower() for path in route_paths)
    assert all("execute" not in path.lower() for path in route_paths)
    assert all("broker" not in path.lower() or path == "/paper-broker/status" for path in route_paths)

    # API cycle endpoint uses the default (mock) manager offline and must fail
    # loudly rather than fill orders from fake prices. The failure is recorded
    # (CYCLE_FAILED + last_error) but no longer latches ERROR: the same
    # recovery pass the scheduler uses re-arms the fund so autonomous
    # operation survives a failed manual cycle.
    api_cycle = paper_fund_cycle()
    assert api_cycle["cycle"]["cycle_status"] == "FAILED"
    assert api_cycle["cycle"]["orders"] == []
    assert api_cycle["recovery"]["status"] == "RECOVERED"
    assert api_cycle["status"]["fund_status"] in {"READY", "RUNNING"}
    assert api_cycle["status"]["last_error"]

    # Stop and reset return the fund to a clean OFF state with no fake data.
    stopped = paper_fund_stop()
    assert stopped["state"]["fund_status"] == "OFF"
    try:
        engine.run_cycle(manager=_ValidatedTestPriceManager({"AAPL": 1, "MSFT": 1}))
        raise AssertionError("cycle must fail when the fund is OFF")
    except ValueError:
        pass
    reset = paper_fund_reset()
    assert reset["status"]["fund_status"] == "OFF"
    assert reset["status"]["virtual_orders"] == []
    assert reset["status"]["snapshots"] == []
    assert reset["status"]["activity_log"] == []

    # Starting with an empty watchlist is rejected loudly.
    try:
        paper_fund_start(payload={"watchlist": []})
        raise AssertionError("empty watchlist must be rejected")
    except HTTPException as error:
        assert error.status_code == 400
finally:
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(database_path)
    for candidate in (database_path, f"{database_path}-wal", f"{database_path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


# ----------------------------------------------------------------------
# Risk management integration rejects unsafe proposals without fills.
# ----------------------------------------------------------------------
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as risk_database_file:
    risk_database_path = risk_database_file.name

try:
    connection.DATABASE_PATH = risk_database_path
    connection._wal_initialized_paths.discard(risk_database_path)
    run_migrations()
    risk_engine = LivePaperFundEngine()
    risk_engine.start(
        watchlist=["AAPL"],
        starting_cash=1000,
        interval_minutes=30,
        now="2026-07-03T10:00:00",
    )

    original_propose = risk_engine._propose_orders

    def unaffordable_proposal(state, prices, provider, moment, cycle_id, construction):
        return [
            {
                "order_id": f"{cycle_id}-BUY-AAPL",
                "cycle_id": cycle_id,
                "ticker": "AAPL",
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": 20,
                "price": 100,
                "fill_price": 100,
                "price_source": provider,
                "created_at": moment.isoformat(),
                "reason": "Forced unaffordable proposal for risk test.",
                "policy": risk_engine.policy(),
            }
        ]

    risk_engine._propose_orders = unaffordable_proposal
    unaffordable = risk_engine.run_cycle(
        manager=_ValidatedTestPriceManager({"AAPL": 100.0}),
        now="2026-07-03T10:00:00",
    )
    assert unaffordable["cycle_status"] == "COMPLETED"
    assert unaffordable["orders"] == []
    assert unaffordable["risk_summary"]["proposed"] == 1
    assert unaffordable["risk_summary"]["approved"] == 0
    assert unaffordable["risk_summary"]["rejected"] == 1
    assert "available cash" in unaffordable["risk_summary"]["rejections"][0]["reasons"][0]
    assert unaffordable["snapshot"]["cash"] == 1000
    assert unaffordable["snapshot"]["positions"] == {}
    unaffordable_learning = unaffordable["learning"]["details"]["learning_summary"]
    assert unaffordable_learning["bought_symbols"] == []
    assert unaffordable_learning["sold_symbols"] == []
    assert unaffordable_learning["rejected_orders"][0]["symbol"] == "AAPL"
    assert unaffordable_learning["rejected_orders"][0]["side"] == "BUY"
    assert unaffordable_learning["rejected_orders"][0]["quantity"] == 20
    assert (
        "Buy order value exceeds available cash; order is rejected without clipping."
        in unaffordable_learning["rejected_orders"][0]["reasons"]
    )
    assert unaffordable_learning["portfolio"]["value_change"] == 0
    assert unaffordable_learning["what_did_not_work"] == [
        "Risk controls blocked proposed orders for AAPL.",
        "No proposed orders passed risk validation.",
    ]
    assert "Review AAPL before the next cycle" in unaffordable_learning["watch_next"][0]
    assert unaffordable_learning["policy"]["does_not_modify_trades"] is True
    assert get_paper_fund_orders(limit=10) == []
    unaffordable_decisions = get_recent_risk_decisions(limit=10)
    assert len(unaffordable_decisions) == 1
    assert unaffordable_decisions[0]["verdict"] == "REJECTED"
    assert unaffordable_decisions[0]["quantity"] == 20

    risk_engine._propose_orders = original_propose
    risk_engine.stop(now="2026-07-03T10:10:00")
    risk_engine.start(
        watchlist=["AAPL"],
        starting_cash=1000,
        interval_minutes=30,
        now="2026-07-03T10:15:00",
    )

    def oversell_proposal(state, prices, provider, moment, cycle_id, construction):
        return [
            {
                "order_id": f"{cycle_id}-SELL-AAPL",
                "cycle_id": cycle_id,
                "ticker": "AAPL",
                "symbol": "AAPL",
                "side": "SELL",
                "quantity": 1,
                "price": 100,
                "fill_price": 100,
                "price_source": provider,
                "created_at": moment.isoformat(),
                "reason": "Forced oversell proposal for risk test.",
                "policy": risk_engine.policy(),
            }
        ]

    risk_engine._propose_orders = oversell_proposal
    oversell = risk_engine.run_cycle(
        manager=_ValidatedTestPriceManager({"AAPL": 100.0}),
        now="2026-07-03T10:15:00",
    )
    assert oversell["cycle_status"] == "COMPLETED"
    assert oversell["orders"] == []
    assert oversell["risk_summary"]["proposed"] == 1
    assert oversell["risk_summary"]["approved"] == 0
    assert oversell["risk_summary"]["rejected"] == 1
    assert "current holdings" in oversell["risk_summary"]["rejections"][0]["reasons"][0]
    assert oversell["snapshot"]["cash"] == 1000
    assert oversell["snapshot"]["positions"] == {}
    oversell_learning = oversell["learning"]["details"]["learning_summary"]
    assert oversell_learning["rejected_orders"] == [
        {
            "symbol": "AAPL",
            "side": "SELL",
            "quantity": 1,
            "reasons": [
                "Sell quantity exceeds current holdings; order is rejected without clipping."
            ],
        }
    ]
    assert oversell_learning["portfolio"]["value_change"] == 0
    assert oversell_learning["policy"] == {
        "descriptive_only": True,
        "does_not_modify_recommendations": True,
        "does_not_modify_trades": True,
        "paper_only": True,
        "real_money": False,
    }
    assert get_paper_fund_orders(limit=10) == []
    risk_decisions = get_recent_risk_decisions(limit=10)
    assert len(risk_decisions) == 2
    assert [decision["verdict"] for decision in risk_decisions] == [
        "REJECTED",
        "REJECTED",
    ]
    assert {decision["quantity"] for decision in risk_decisions} == {1, 20}
finally:
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(risk_database_path)
    for candidate in (
        risk_database_path,
        f"{risk_database_path}-wal",
        f"{risk_database_path}-shm",
    ):
        if os.path.exists(candidate):
            os.remove(candidate)


# ----------------------------------------------------------------------
# Correlation risk gate: highly correlated BUYs are rejected using real,
# price-backed correlation evidence; unavailable history stays NOT_EVALUATED.
# ----------------------------------------------------------------------
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as corr_database_file:
    corr_database_path = corr_database_file.name

try:
    connection.DATABASE_PATH = corr_database_path
    connection._wal_initialized_paths.discard(corr_database_path)
    run_migrations()

    corr_rows = corr_history_rows(["AAPL", "MSFT"])
    corr_manager = _CorrelationPriceManager({"AAPL": 100.0, "MSFT": 200.0}, corr_rows)

    corr_engine = LivePaperFundEngine()
    corr_engine.start(
        watchlist=["AAPL", "MSFT"],
        starting_cash=1_000_000,
        interval_minutes=30,
        now="2026-07-05T10:00:00",
    )

    def correlated_buys(state, prices, provider, moment, cycle_id, construction):
        return [
            {
                "order_id": f"{cycle_id}-BUY-{ticker}",
                "cycle_id": cycle_id,
                "ticker": ticker,
                "symbol": ticker,
                "side": "BUY",
                "quantity": 10,
                "price": prices[ticker],
                "fill_price": prices[ticker],
                "price_source": provider,
                "created_at": moment.isoformat(),
                "reason": "Forced correlated BUY for correlation-gate test.",
                "policy": corr_engine.policy(),
            }
            for ticker in ["AAPL", "MSFT"]
        ]

    corr_engine._propose_orders = correlated_buys
    corr_cycle = corr_engine.run_cycle(manager=corr_manager, now="2026-07-05T10:00:00")

    assert corr_cycle["cycle_status"] == "COMPLETED"
    # Real, price-backed correlation evidence reached the risk gate.
    assert corr_cycle["risk_summary"]["correlation"]["status"] == "EVALUATED"
    assert corr_cycle["risk_summary"]["correlation"]["pairs_evaluated"] == 1
    assert corr_cycle["risk_summary"]["correlation"]["threshold"] == 0.80
    # AAPL (validated first, no peers) is approved; MSFT is rejected because it
    # is perfectly correlated (1.0) with the just-approved AAPL position.
    assert corr_cycle["risk_summary"]["proposed"] == 2
    assert corr_cycle["risk_summary"]["approved"] == 1
    assert corr_cycle["risk_summary"]["rejected"] == 1
    assert {order["ticker"] for order in corr_cycle["orders"]} == {"AAPL"}
    corr_rejection = corr_cycle["risk_summary"]["rejections"][0]
    assert corr_rejection["order"]["ticker"] == "MSFT"
    assert any(
        "correlation" in reason.lower() for reason in corr_rejection["reasons"]
    )
    # Correlation evidence status/reason is surfaced in the activity log.
    corr_status = corr_engine.status()
    corr_activity = next(
        entry for entry in corr_status["activity_log"]
        if entry["activity_type"] == "CORRELATION_EVALUATED"
    )
    assert corr_activity["details"]["status"] == "EVALUATED"
    assert corr_activity["details"]["pairs_evaluated"] == 1

    # New BUY is evaluated against EXISTING holdings: AAPL is now held, so a
    # fresh MSFT BUY is rejected against the held, highly-correlated AAPL.
    def msft_only(state, prices, provider, moment, cycle_id, construction):
        return [
            {
                "order_id": f"{cycle_id}-BUY-MSFT",
                "cycle_id": cycle_id,
                "ticker": "MSFT",
                "symbol": "MSFT",
                "side": "BUY",
                "quantity": 10,
                "price": prices["MSFT"],
                "fill_price": prices["MSFT"],
                "price_source": provider,
                "created_at": moment.isoformat(),
                "reason": "Forced new BUY for held-position correlation test.",
                "policy": corr_engine.policy(),
            }
        ]

    corr_engine._propose_orders = msft_only
    held_cycle = corr_engine.run_cycle(manager=corr_manager, now="2026-07-05T10:30:00")
    assert "AAPL" in held_cycle["snapshot"]["positions"]
    assert held_cycle["risk_summary"]["proposed"] == 1
    assert held_cycle["risk_summary"]["approved"] == 0
    assert held_cycle["risk_summary"]["rejected"] == 1
    held_rejection = held_cycle["risk_summary"]["rejections"][0]
    assert held_rejection["order"]["ticker"] == "MSFT"
    assert any(
        "correlation" in reason.lower() for reason in held_rejection["reasons"]
    )

    # Unavailable history (fixture with no historical_prices) -> NOT_EVALUATED
    # and no correlation block: both proposals pass the correlation check.
    corr_engine.stop(now="2026-07-05T10:40:00")
    corr_engine.start(
        watchlist=["AAPL", "MSFT"],
        starting_cash=1_000_000,
        interval_minutes=30,
        now="2026-07-05T10:45:00",
    )
    corr_engine._propose_orders = correlated_buys
    no_history_cycle = corr_engine.run_cycle(
        manager=_ValidatedTestPriceManager({"AAPL": 100.0, "MSFT": 200.0}),
        now="2026-07-05T10:45:00",
    )
    assert no_history_cycle["risk_summary"]["correlation"]["status"] == "NOT_EVALUATED"
    assert no_history_cycle["risk_summary"]["approved"] == 2
    assert no_history_cycle["risk_summary"]["rejected"] == 0

    # Fallback history -> NOT_EVALUATED (values are never fabricated).
    corr_engine.stop(now="2026-07-05T10:50:00")
    corr_engine.start(
        watchlist=["AAPL", "MSFT"],
        starting_cash=1_000_000,
        interval_minutes=30,
        now="2026-07-05T10:55:00",
    )
    corr_engine._propose_orders = correlated_buys
    fallback_cycle = corr_engine.run_cycle(
        manager=_FallbackHistoryManager({"AAPL": 100.0, "MSFT": 200.0}, corr_rows),
        now="2026-07-05T10:55:00",
    )
    assert fallback_cycle["risk_summary"]["correlation"]["status"] == "NOT_EVALUATED"
    assert fallback_cycle["risk_summary"]["approved"] == 2
    assert fallback_cycle["risk_summary"]["rejected"] == 0
finally:
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(corr_database_path)
    for candidate in (
        corr_database_path,
        f"{corr_database_path}-wal",
        f"{corr_database_path}-shm",
    ):
        if os.path.exists(candidate):
            os.remove(candidate)


# ----------------------------------------------------------------------
# Automatic operation: is_cycle_due / run_due_cycle / POST /paper-fund/tick
# ----------------------------------------------------------------------
import core.settings as settings
from api.main import paper_fund_tick
from database.repository import get_latest_paper_fund_state
from engines.live_paper_fund_engine import _CYCLE_LOCK


class _AutoReadyManager:
    """Test fixture: a real-provider-shaped manager safe for automatic runs."""

    provider_name = "yahoo"

    def __init__(self, prices, is_open=True):
        self._prices = prices
        self._is_open = is_open

    def market_status(self, as_of=None):
        return {
            "is_open": self._is_open,
            "session": "open" if self._is_open else "closed",
            "as_of": str(as_of),
        }

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
            "as_of": "2026-07-02T10:00:00",
        }


class _AutoUnvalidatedManager(_AutoReadyManager):
    """Test fixture: safe provider name but prices that fail validation."""

    def latest_prices(self, tickers, use_cache=True):
        report = super().latest_prices(tickers, use_cache=use_cache)
        report["validated"] = False
        for result in report["results"].values():
            result["validated"] = False
        return report


auto_engine = LivePaperFundEngine()
auto_enabled_original = settings.AUTO_FUND_ENABLED
auto_hours_original = settings.AUTO_FUND_MARKET_HOURS_ONLY

with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as auto_database_file:
    auto_database_path = auto_database_file.name

try:
    connection.DATABASE_PATH = auto_database_path
    connection._wal_initialized_paths.discard(auto_database_path)
    run_migrations()
    settings.AUTO_FUND_ENABLED = True
    settings.AUTO_FUND_MARKET_HOURS_ONLY = True

    ready = _AutoReadyManager({"AAPL": 100.0, "MSFT": 200.0})
    closed = _AutoReadyManager({"AAPL": 100.0, "MSFT": 200.0}, is_open=False)
    unvalidated = _AutoUnvalidatedManager({"AAPL": 100.0, "MSFT": 200.0})

    # OFF: no fund exists yet -> skip without writes.
    off_skip = auto_engine.run_due_cycle(manager=ready, now="2026-07-02T10:00:00")
    assert off_skip == {"status": "SKIPPED", "reason": "fund is off"}
    assert get_paper_fund_snapshots(limit=10) == []

    auto_engine.start(
        watchlist=["AAPL", "MSFT"],
        starting_cash=100000,
        interval_minutes=30,
        now="2026-07-02T10:00:00",
    )

    # Auto disabled: skip without writes even when everything else is ready.
    settings.AUTO_FUND_ENABLED = False
    disabled_skip = auto_engine.run_due_cycle(manager=ready, now="2026-07-02T10:00:00")
    assert disabled_skip == {
        "status": "SKIPPED",
        "reason": "automatic paper fund operation is disabled",
    }
    assert get_paper_fund_snapshots(limit=10) == []
    settings.AUTO_FUND_ENABLED = True

    # Unsafe provider (mock/test/unknown) is rejected for automatic operation.
    unsafe_skip = auto_engine.run_due_cycle(
        manager=_MockPriceManager({"AAPL": 100.0, "MSFT": 200.0}),
        now="2026-07-02T10:00:00",
    )
    assert unsafe_skip["status"] == "SKIPPED"
    assert "unsafe" in unsafe_skip["reason"]
    assert get_paper_fund_snapshots(limit=10) == []

    # DUE: runs exactly one cycle through the unchanged run_cycle, which is the
    # only path that advances next_update.
    due = auto_engine.run_due_cycle(manager=ready, now="2026-07-02T10:00:00")
    assert due["cycle_status"] == "COMPLETED"
    assert due["fund_status"] == "RUNNING"
    assert len(get_paper_fund_snapshots(limit=100)) == 1
    assert get_latest_paper_fund_state()["next_update"] == "2026-07-02T10:30:00"

    # NOT DUE: before next_update -> skip, no write, next_update unchanged.
    not_due = auto_engine.run_due_cycle(manager=ready, now="2026-07-02T10:15:00")
    assert not_due == {"status": "SKIPPED", "reason": "cycle is not due yet"}
    assert len(get_paper_fund_snapshots(limit=100)) == 1
    assert get_latest_paper_fund_state()["next_update"] == "2026-07-02T10:30:00"

    # MARKET CLOSED: due but the market is closed -> skip, next_update unchanged.
    closed_skip = auto_engine.run_due_cycle(manager=closed, now="2026-07-02T10:45:00")
    assert closed_skip == {"status": "SKIPPED", "reason": "market is closed"}
    assert len(get_paper_fund_snapshots(limit=100)) == 1
    assert get_latest_paper_fund_state()["next_update"] == "2026-07-02T10:30:00"

    # PAUSED: skip; resume restores automatic eligibility.
    auto_engine.pause(now="2026-07-02T10:46:00")
    paused_skip = auto_engine.run_due_cycle(manager=ready, now="2026-07-02T10:46:00")
    assert paused_skip == {"status": "SKIPPED", "reason": "fund is paused"}
    assert len(get_paper_fund_snapshots(limit=100)) == 1
    auto_engine.resume(now="2026-07-02T10:47:00")

    # Invalid prices still fail loudly, but automatic operation schedules the
    # next retry instead of requiring manual recovery from a transient market
    # data problem.
    fail_loud = auto_engine.run_due_cycle(manager=unvalidated, now="2026-07-02T11:00:00")
    assert fail_loud["cycle_status"] == "RECOVERING"
    assert fail_loud["fund_status"] == "RUNNING"
    assert fail_loud["orders"] == []
    assert fail_loud["snapshot"] is None
    assert fail_loud["recovery"]["status"] == "scheduled_retry"
    assert fail_loud["next_update"] == "2026-07-02T11:30:00"
    assert len(get_paper_fund_snapshots(limit=100)) == 1

    recovered_state = get_latest_paper_fund_state()
    assert recovered_state["fund_status"] == "RUNNING"
    assert recovered_state["last_error"] == fail_loud["error"]

    # Not yet due after recovery: skip until the scheduled retry.
    error_skip = auto_engine.run_due_cycle(manager=ready, now="2026-07-02T11:05:00")
    assert error_skip == {"status": "SKIPPED", "reason": "cycle is not due yet"}
    assert len(get_paper_fund_snapshots(limit=100)) == 1

    # CONCURRENT tick: with the single-flight guard already held, the tick
    # endpoint returns cycle_in_progress and no extra cycle runs.
    assert _CYCLE_LOCK.acquire(blocking=False) is True
    try:
        concurrent = paper_fund_tick()
        assert concurrent["status"] == "cycle_in_progress"
        assert (
            concurrent["tick"]["reason"]
            == LivePaperFundEngine.CYCLE_IN_PROGRESS_REASON
        )
        assert len(get_paper_fund_snapshots(limit=100)) == 1
    finally:
        _CYCLE_LOCK.release()

    # Tick endpoint honors the disabled flag too.
    settings.AUTO_FUND_ENABLED = False
    tick_disabled = paper_fund_tick()
    assert tick_disabled["tick"]["status"] == "SKIPPED"
    assert (
        tick_disabled["tick"]["reason"]
        == "automatic paper fund operation is disabled"
    )
    assert len(get_paper_fund_snapshots(limit=100)) == 1

    # MANUAL LOCK PARITY: POST /paper-fund/cycle shares the same single-flight
    # lock as autonomous ticks. While a cycle is in progress it returns 409
    # without blocking and without writing orders, snapshots, or state.
    orders_before = len(get_paper_fund_orders(limit=1000))
    snapshots_before = len(get_paper_fund_snapshots(limit=1000))
    state_before = get_latest_paper_fund_state()
    assert _CYCLE_LOCK.acquire(blocking=False) is True
    try:
        try:
            paper_fund_cycle()
            raise AssertionError(
                "manual cycle must be rejected while another cycle runs"
            )
        except HTTPException as error:
            assert error.status_code == 409
            assert LivePaperFundEngine.CYCLE_IN_PROGRESS_REASON in str(error.detail)

        # Engine-level parity: the manual entry point skips immediately too.
        busy = auto_engine.run_manual_cycle(
            manager=ready, now="2026-07-02T12:00:00"
        )
        assert busy == {
            "status": "SKIPPED",
            "reason": LivePaperFundEngine.CYCLE_IN_PROGRESS_REASON,
        }
    finally:
        _CYCLE_LOCK.release()
    assert len(get_paper_fund_orders(limit=1000)) == orders_before
    assert len(get_paper_fund_snapshots(limit=1000)) == snapshots_before
    assert get_latest_paper_fund_state() == state_before

    # With the lock free again, a manual cycle still runs normally. The manual
    # override is independent of the AUTO_FUND_ENABLED gate (still False here),
    # which governs autonomous ticks only; run_cycle's own price-validation and
    # risk gates are unchanged.
    manual = auto_engine.run_manual_cycle(manager=ready, now="2026-07-02T12:00:00")
    assert manual["cycle_status"] == "COMPLETED"
    assert manual["fund_status"] == "RUNNING"
    assert len(get_paper_fund_snapshots(limit=1000)) == snapshots_before + 1
finally:
    settings.AUTO_FUND_ENABLED = auto_enabled_original
    settings.AUTO_FUND_MARKET_HOURS_ONLY = auto_hours_original
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(auto_database_path)
    for candidate in (
        auto_database_path,
        f"{auto_database_path}-wal",
        f"{auto_database_path}-shm",
    ):
        if os.path.exists(candidate):
            os.remove(candidate)

print("LivePaperFund test passed.")
