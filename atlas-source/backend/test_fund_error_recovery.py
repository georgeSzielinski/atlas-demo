"""Regression tests: the paper fund ERROR state is never a dead end.

Covers: an ERROR fund auto-recovers after the cycle-interval cooldown and the
next due tick runs a real cycle; before the cooldown the tick skips with an
explanatory reason; ANY failed autonomous cycle schedules a retry instead of
latching ERROR; a failed manual cycle is recoverable through the same pass
(recover_after_failure); and OFF/PAUSED funds are NEVER auto-resumed — human
intent stays manual. Paper-only throughout; runs against a throwaway
temporary database.
"""

import os
import tempfile
from datetime import datetime, timedelta

import core.settings as settings
import database.connection as connection
from database.migrator import run_migrations
from database.repository import (
    get_latest_paper_fund_state,
    get_paper_fund_activity,
)
from engines.live_paper_fund_engine import LivePaperFundEngine


def cleanup_database(path):
    connection._wal_initialized_paths.discard(path)
    for candidate in (path, f"{path}-wal", f"{path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


class _ValidatedTestPriceManager:
    # Must not contain mock/test/unknown: run_due_cycle's provider-safety
    # gate refuses those before any recovery logic is reached.
    provider_name = "fixture_live_prices"

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
            "as_of": "2026-07-10T16:00:00",
        }


class _UnvalidatedPriceManager(_ValidatedTestPriceManager):
    def latest_prices(self, tickers, use_cache=True):
        report = super().latest_prices(tickers, use_cache=use_cache)
        report["validated"] = False
        return report


def _latch_error(engine, moment, failure="synthetic non-transient failure"):
    state = get_latest_paper_fund_state()
    result = engine._fail_cycle(
        state, moment, "fund-test-error", {"is_open": True}, failure
    )
    assert result["cycle_status"] == "FAILED"
    assert get_latest_paper_fund_state()["fund_status"] == "ERROR"


def error_state_recovers_after_cooldown():
    engine = LivePaperFundEngine()
    manager = _ValidatedTestPriceManager({"AAPL": 100.0})
    t0 = datetime(2026, 7, 10, 16, 0, 0)

    engine.start(["AAPL"], starting_cash=10000, interval_minutes=30, now=t0)
    _latch_error(engine, t0)

    # Before the cooldown: skip, but with a reason that says recovery is coming.
    early = engine.run_due_cycle(manager=manager, now=t0 + timedelta(minutes=10))
    assert early["status"] == "SKIPPED"
    assert "automatic recovery" in early["reason"]
    assert get_latest_paper_fund_state()["fund_status"] == "ERROR"

    # After the cooldown: the fund re-arms itself and the cycle runs.
    result = engine.run_due_cycle(manager=manager, now=t0 + timedelta(minutes=31))
    assert result["cycle_status"] == "COMPLETED"
    assert get_latest_paper_fund_state()["fund_status"] == "RUNNING"

    activity_types = [
        entry["activity_type"] for entry in get_paper_fund_activity(limit=50)
    ]
    assert "AUTO_RECOVERY_FROM_ERROR" in activity_types


def any_failed_cycle_schedules_retry():
    engine = LivePaperFundEngine()
    manager = _UnvalidatedPriceManager({"AAPL": 100.0})
    now = datetime(2026, 7, 10, 17, 5, 0)

    result = engine.run_due_cycle(manager=manager, now=now)
    assert result["cycle_status"] == "RECOVERING"
    state = get_latest_paper_fund_state()
    assert state["fund_status"] in {"READY", "RUNNING"}  # never latched ERROR
    assert state["next_update"] > now.isoformat()  # retry is scheduled


def manual_cycle_failure_is_recoverable():
    engine = LivePaperFundEngine()
    now = datetime(2026, 7, 10, 18, 0, 0)
    _latch_error(engine, now, failure="manual cycle failed")

    recovery = engine.recover_after_failure(now=now)
    assert recovery["status"] == "RECOVERED"
    assert recovery["previous_error"] == "manual cycle failed"
    state = get_latest_paper_fund_state()
    assert state["fund_status"] in {"READY", "RUNNING"}

    # Idempotent: recovering a healthy fund is a no-op skip.
    again = engine.recover_after_failure(now=now)
    assert again["status"] == "SKIPPED"


def off_and_paused_are_never_auto_resumed():
    engine = LivePaperFundEngine()
    manager = _ValidatedTestPriceManager({"AAPL": 100.0})
    later = datetime(2026, 7, 11, 16, 0, 0)

    engine.pause(now=later)
    paused = engine.run_due_cycle(manager=manager, now=later + timedelta(hours=5))
    assert paused == {"status": "SKIPPED", "reason": "fund is paused"}
    assert get_latest_paper_fund_state()["fund_status"] == "PAUSED"

    engine.stop(now=later)
    off = engine.run_due_cycle(manager=manager, now=later + timedelta(days=2))
    assert off == {"status": "SKIPPED", "reason": "fund is off"}
    assert get_latest_paper_fund_state()["fund_status"] == "OFF"


original_database_path = connection.DATABASE_PATH
original_auto = settings.AUTO_FUND_ENABLED
original_hours = settings.AUTO_FUND_MARKET_HOURS_ONLY
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()
    settings.AUTO_FUND_ENABLED = True
    settings.AUTO_FUND_MARKET_HOURS_ONLY = False

    error_state_recovers_after_cooldown()
    any_failed_cycle_schedules_retry()
    manual_cycle_failure_is_recoverable()
    off_and_paused_are_never_auto_resumed()
finally:
    settings.AUTO_FUND_ENABLED = original_auto
    settings.AUTO_FUND_MARKET_HOURS_ONLY = original_hours
    connection.DATABASE_PATH = original_database_path
    cleanup_database(database_path)

print("Fund error recovery test passed.")
