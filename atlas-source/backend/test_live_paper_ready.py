"""Offline safety tests for opt-in live paper mode.

Deterministic and offline. Proves, with fake real-provider managers, that a
real cycle only runs during market hours, that fake/fallback prices fail loudly
instead of trading, that a validated real-provider cycle produces simulated
paper orders (no broker, no real money), and that the read-only preflight
returns NO-GO by default and GO only when every precondition holds.
"""

import os
import tempfile

import core.settings as settings
import database.connection as connection
from backend.live_paper_preflight import build_preflight_report
from database.repository import (
    get_paper_fund_orders,
    get_paper_fund_snapshots,
)
from database.migrator import run_migrations
from engines.live_paper_fund_engine import LivePaperFundEngine


class _RealProviderManager:
    """Fake manager shaped like a real (yahoo) provider with validated prices."""

    provider_name = "yahoo"

    def __init__(self, prices, is_open=True):
        self._prices = prices
        self._is_open = is_open

    def market_status(self, as_of=None):
        return {
            "is_open": self._is_open,
            "session": "open" if self._is_open else "closed",
            "is_holiday": False,
            "is_early_close": False,
            "as_of": str(as_of),
        }

    def health(self):
        return {
            "active_provider": self.provider_name,
            "healthy": True,
            "fallback_used": False,
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
            "as_of": "2026-07-06T14:00:00",
        }


class _FallbackManager(_RealProviderManager):
    """Requested yahoo, but the price actually came from a mock fallback."""

    def health(self):
        report = super().health()
        report["active_provider"] = "mock"
        report["fallback_used"] = True
        return report

    def latest_prices(self, tickers, use_cache=True):
        report = super().latest_prices(tickers, use_cache=use_cache)
        report["fallback_used"] = True
        for result in report["results"].values():
            result["provider"] = "mock"
        return report


original_database_path = connection.DATABASE_PATH
original_auto = settings.AUTO_FUND_ENABLED
original_scheduler = settings.ATLAS_SCHEDULER_ENABLED

with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()
    engine = LivePaperFundEngine()
    settings.AUTO_FUND_ENABLED = True
    settings.AUTO_FUND_MARKET_HOURS_ONLY = True

    engine.start(
        watchlist=["AAPL", "MSFT"],
        starting_cash=100000,
        interval_minutes=30,
        now="2026-07-06T10:00:00",
    )

    # --- market closed: real provider, but no cycle runs and nothing is written ---
    closed = engine.run_due_cycle(
        manager=_RealProviderManager({"AAPL": 100.0, "MSFT": 200.0}, is_open=False),
        now="2026-07-06T10:00:00",
    )
    assert closed == {"status": "SKIPPED", "reason": "market is closed"}
    assert get_paper_fund_snapshots(limit=10) == []
    assert get_paper_fund_orders(limit=10) == []

    # --- fake/fallback prices fail loudly, schedule retry, and never trade ---
    fallback = engine.run_due_cycle(
        manager=_FallbackManager({"AAPL": 100.0, "MSFT": 200.0}),
        now="2026-07-06T10:00:00",
    )
    assert fallback["cycle_status"] == "RECOVERING"
    assert fallback["fund_status"] == "READY"
    assert fallback["orders"] == []
    assert fallback["snapshot"] is None
    assert fallback["recovery"]["status"] == "scheduled_retry"
    assert get_paper_fund_snapshots(limit=10) == []

    # Recover for the happy path.
    engine.stop(now="2026-07-06T10:05:00")
    engine.start(
        watchlist=["AAPL", "MSFT"],
        starting_cash=100000,
        interval_minutes=30,
        now="2026-07-06T10:06:00",
    )

    # --- real provider, market open, validated prices: simulated paper cycle ---
    completed = engine.run_due_cycle(
        manager=_RealProviderManager({"AAPL": 100.0, "MSFT": 200.0}, is_open=True),
        now="2026-07-06T10:06:00",
    )
    assert completed["cycle_status"] == "COMPLETED"
    assert completed["price_provider"] == "yahoo"
    assert len(completed["orders"]) == 2
    for order in completed["orders"]:
        assert order["price_source"] == "yahoo"
        assert order["simulated"] is True
        assert order["status"] == "FILLED_SIMULATED"
        assert order["policy"]["broker_disabled"] is True
        assert order["policy"]["real_money"] is False
        assert order["policy"]["execution"] == "simulated_only"

    # --- preflight GO only when every precondition holds ---
    settings.ATLAS_SCHEDULER_ENABLED = True
    go = build_preflight_report(
        manager=_RealProviderManager({"AAPL": 100.0, "MSFT": 200.0}),
        fund_state_reader=lambda: ({"fund_status": "READY"}, None),
    )
    assert go["ready"] is True
    assert go["verdict"] == "GO"
    assert go["safety"]["real_money"] is False
    assert go["safety"]["human_approval_required_for_real_trading"] is True
    assert go["read_only"] is True

    # A fallback provider is NOT ready even with flags on and fund READY.
    no_go_fallback = build_preflight_report(
        manager=_FallbackManager({"AAPL": 100.0, "MSFT": 200.0}),
        fund_state_reader=lambda: ({"fund_status": "READY"}, None),
    )
    assert no_go_fallback["ready"] is False
    assert no_go_fallback["checks"]["provider_active_real"] is False

    # --- default is NO-GO: disabled flags + mock provider (real manager) ---
    settings.AUTO_FUND_ENABLED = False
    settings.ATLAS_SCHEDULER_ENABLED = False
    default_report = build_preflight_report(
        fund_state_reader=lambda: (None, None),
    )
    assert default_report["ready"] is False
    assert default_report["verdict"] == "NO-GO"
    assert default_report["checks"]["auto_fund_enabled"] is False
    assert default_report["checks"]["provider_configured_real"] is False
finally:
    settings.AUTO_FUND_ENABLED = original_auto
    settings.ATLAS_SCHEDULER_ENABLED = original_scheduler
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(database_path)
    for candidate in (database_path, f"{database_path}-wal", f"{database_path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


print("Live paper ready test passed.")
