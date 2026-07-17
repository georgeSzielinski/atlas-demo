"""Regression: preflight and the paper-fund cycle agree on market hours.

The exchange calendar interprets NAIVE datetimes as New York wall-clock, but
the fund tick passes naive LOCAL datetime.now(). On a machine outside Eastern
time that skewed the fund's market-hours gate by the UTC-offset difference:
preflight (which checks the real current instant) said open while
run_due_cycle skipped with "market is closed". The fix routes fund
market-session checks through _market_moment, which attaches the system-local
timezone so both paths evaluate the SAME instant against the SAME calendar.

This test forces TZ=Europe/Warsaw to reproduce the original mismatch.
"""

import os
import tempfile
import time
from datetime import datetime, timedelta, timezone

import database.connection as connection
from core import settings
from database.migrator import run_migrations
from engines.live_paper_fund_engine import LivePaperFundEngine
from market.market_calendar import MarketCalendar


ORIGINAL_TZ = os.environ.get("TZ")
os.environ["TZ"] = "Europe/Warsaw"
time.tzset()

calendar = MarketCalendar()
engine = LivePaperFundEngine()


class _CalendarBackedManager:
    """Validated real-provider-shaped manager whose market_status delegates to
    the REAL exchange calendar — the same source preflight uses."""

    provider_name = "yahoo"

    def __init__(self, prices):
        self._prices = prices

    def market_status(self, as_of=None):
        return calendar.session(as_of)

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
            "as_of": "2026-03-05T20:00:00",
        }


def preflight_view(naive_local_moment):
    """What preflight reports for the same instant: the calendar evaluated at
    the aware (real) moment, exactly like market_status() with no argument."""
    return calendar.session(naive_local_moment.astimezone())


def run_due(naive_local_moment):
    """One guarded fund tick at a simulated local wall-clock moment."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as handle:
        path = handle.name
    original_path = connection.DATABASE_PATH
    original_auto = settings.AUTO_FUND_ENABLED
    original_hours = settings.AUTO_FUND_MARKET_HOURS_ONLY
    try:
        connection.DATABASE_PATH = path
        connection._wal_initialized_paths.discard(path)
        run_migrations()
        settings.AUTO_FUND_ENABLED = True
        settings.AUTO_FUND_MARKET_HOURS_ONLY = True
        fund = LivePaperFundEngine()
        fund.start(
            ["AAA"], starting_cash=100000,
            now=naive_local_moment - timedelta(minutes=1),
        )
        return fund.run_due_cycle(
            manager=_CalendarBackedManager({"AAA": 100.0}),
            now=naive_local_moment,
        )
    finally:
        settings.AUTO_FUND_ENABLED = original_auto
        settings.AUTO_FUND_MARKET_HOURS_ONLY = original_hours
        connection.DATABASE_PATH = original_path
        connection._wal_initialized_paths.discard(path)
        for candidate in (path, f"{path}-wal", f"{path}-shm"):
            if os.path.exists(candidate):
                os.remove(candidate)


try:
    # -----------------------------------------------------------------
    # _market_moment: naive gains the system-local zone; aware unchanged.
    # -----------------------------------------------------------------
    naive = datetime(2026, 3, 5, 20, 0)
    localized = engine._market_moment(naive)
    assert localized.tzinfo is not None
    assert localized.hour == 20  # same wall-clock, now explicitly local
    aware = datetime(2026, 3, 5, 20, 0, tzinfo=timezone.utc)
    assert engine._market_moment(aware) is aware

    # -----------------------------------------------------------------
    # Regression A (the reported bug): preflight OPEN -> cycle RUNS.
    # Thu 2026-03-05 20:00 Warsaw == 14:00 ET, inside a regular session.
    # Before the fix the calendar read 20:00 as ET -> "market is closed".
    # -----------------------------------------------------------------
    open_moment = datetime(2026, 3, 5, 20, 0)
    view = preflight_view(open_moment)
    assert view["available"] is True and view["is_open"] is True, view
    result = run_due(open_moment)
    assert result.get("reason") != "market is closed", result
    assert result.get("cycle_status") == "COMPLETED", result
    assert result["market_status"]["is_open"] is True
    # And the naive-as-ET misreading really was the failure mode:
    assert calendar.session(open_moment)["is_open"] is False

    # Same alignment across the DST boundary (summer: CEST vs EDT).
    summer_open = datetime(2026, 7, 6, 16, 30)  # Mon 16:30 Warsaw == 10:30 ET
    view = preflight_view(summer_open)
    assert view["available"] is True and view["is_open"] is True, view
    result = run_due(summer_open)
    assert result.get("cycle_status") == "COMPLETED", result

    # -----------------------------------------------------------------
    # Regression B: preflight CLOSED -> cycle SKIPS with "market is closed".
    # -----------------------------------------------------------------
    evening = datetime(2026, 3, 5, 23, 30)  # 17:30 ET, after the close
    assert preflight_view(evening)["is_open"] is False
    result = run_due(evening)
    assert result == {"status": "SKIPPED", "reason": "market is closed"}, result

    saturday = datetime(2026, 3, 7, 20, 0)
    assert preflight_view(saturday)["is_open"] is False
    result = run_due(saturday)
    assert result == {"status": "SKIPPED", "reason": "market is closed"}, result

    # -----------------------------------------------------------------
    # Alignment property: for a sweep of moments the gate decision always
    # matches the preflight view of the same instant — one source, one
    # timezone interpretation.
    # -----------------------------------------------------------------
    for moment in (
        datetime(2026, 3, 5, 15, 20),   # 09:20 ET pre-open -> closed
        datetime(2026, 3, 5, 15, 40),   # 09:40 ET -> open
        datetime(2026, 3, 5, 21, 55),   # 15:55 ET -> open
        datetime(2026, 3, 5, 22, 5),    # 16:05 ET -> closed
        datetime(2026, 3, 9, 20, 0),    # Monday 15:00 EDT? (DST week) -> open
    ):
        expected_open = preflight_view(moment)["is_open"]
        result = run_due(moment)
        gate_open = result.get("reason") != "market is closed"
        assert gate_open == expected_open, (moment, expected_open, result)
finally:
    if ORIGINAL_TZ is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = ORIGINAL_TZ
    time.tzset()

print("Market hours alignment test passed.")
