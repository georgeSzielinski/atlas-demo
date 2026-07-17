"""Runnable dry-run verifier for the automatic Live Paper Fund scheduler.

Run:

    venv/bin/python -m backend.scheduler_dryrun

Proves the scheduler loop runs end to end WITHOUT placing any trade: it starts
the real scheduler loop (which calls the real guarded /paper-fund/tick path)
with ATLAS_SCHEDULER_ENABLED=true and AUTO_FUND_ENABLED=false, lets it tick a
few times, and verifies ticks happened while no cycles or trades were written.

Safe by construction: it runs against a throwaway temporary database (never
touches database/atlas.db), keeps auto fund disabled, connects no broker, and
uses no network (the disabled gate short-circuits before any provider call).
Exits 0 on PASS, 1 on FAIL.

Enabling real (still paper-only) trading later
----------------------------------------------
1. Choose a real market data provider:   export MARKET_DATA_PROVIDER=yahoo
   (mock/test/unknown providers are rejected for automatic operation.)
2. Start the fund with a watchlist:       POST /paper-fund/start  {"watchlist": [...]}
   so its state becomes READY.
3. Enable the gates:                       export AUTO_FUND_ENABLED=true
                                           export ATLAS_SCHEDULER_ENABLED=true
4. Launch the API:                         venv/bin/python -m backend.run_api
5. Watch GET /scheduler/status and GET /paper-fund/status.

Even then execution stays simulated only: fills are virtual, the broker is
disabled, real_money is always false, and bad/fallback prices fail the cycle
loudly into ERROR instead of trading.
"""

import asyncio
import os
import sys
import tempfile

import api.scheduler_runtime as scheduler_runtime_module
import core.settings as settings
import database.connection as connection
from api.main import scheduler_status
from database.repository import (
    get_latest_paper_fund_state,
    get_paper_fund_orders,
    get_paper_fund_snapshots,
)
from database.setup import setup_database


TARGET_TICKS = 3
INTERVAL_SECONDS = 0.1
TIMEOUT_SECONDS = 10


async def _wait_for_ticks(runtime, target, timeout):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while runtime.status()["tick_count"] < target:
        if loop.time() > deadline:
            return False
        await asyncio.sleep(0.05)
    return True


async def _run():
    runtime = scheduler_runtime_module.scheduler_runtime
    settings.ATLAS_SCHEDULER_ENABLED = True
    settings.AUTO_FUND_ENABLED = False
    runtime._interval_seconds = INTERVAL_SECONDS

    await runtime.start()
    reached = await _wait_for_ticks(runtime, TARGET_TICKS, TIMEOUT_SECONDS)
    await runtime.stop()

    snap = scheduler_status()
    metrics = snap["scheduler"]
    snapshots = get_paper_fund_snapshots(limit=10)
    orders = get_paper_fund_orders(limit=10)
    state = get_latest_paper_fund_state()
    fund_status = (state or {}).get("fund_status")

    checks = {
        "ticks_reached": reached and metrics["tick_count"] >= TARGET_TICKS,
        "all_skipped": metrics["last_status"] == "SKIPPED",
        "reason_disabled": bool(metrics["last_reason"])
        and "disabled" in metrics["last_reason"],
        "no_tick_errors": metrics["error_count"] == 0,
        "auto_fund_off": snap["auto_fund_enabled"] is False,
        "no_snapshots": snapshots == [],
        "no_orders": orders == [],
        "fund_not_running": fund_status != "RUNNING",
    }
    return snap, checks


def main():
    original_scheduler = settings.ATLAS_SCHEDULER_ENABLED
    original_auto = settings.AUTO_FUND_ENABLED
    original_path = connection.DATABASE_PATH

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
        database_path = database_file.name

    try:
        connection.DATABASE_PATH = database_path
        connection._wal_initialized_paths.discard(database_path)
        setup_database()
        snap, checks = asyncio.run(_run())
    finally:
        settings.ATLAS_SCHEDULER_ENABLED = original_scheduler
        settings.AUTO_FUND_ENABLED = original_auto
        scheduler_runtime_module.scheduler_runtime._interval_seconds = None
        connection.DATABASE_PATH = original_path
        connection._wal_initialized_paths.discard(database_path)
        for candidate in (
            database_path,
            f"{database_path}-wal",
            f"{database_path}-shm",
        ):
            if os.path.exists(candidate):
                os.remove(candidate)

    metrics = snap["scheduler"]
    print("Live Paper Fund scheduler dry run")
    print(f"  provider           : {snap['provider']}")
    print(f"  auto_fund_enabled  : {snap['auto_fund_enabled']}")
    print(f"  ticks              : {metrics['tick_count']}")
    print(f"  last_status        : {metrics['last_status']}")
    print(f"  last_reason        : {metrics['last_reason']}")
    print(f"  tick errors        : {metrics['error_count']}")
    print()
    for name, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    passed = all(checks.values())
    print()
    print("RESULT:", "PASS - scheduler ran, no cycles or trades" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
