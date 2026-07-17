"""End-to-end dry-run validation for the automatic scheduler.

Deterministic and offline: drives the real scheduler loop (which calls the real
guarded /paper-fund/tick path) with ATLAS_SCHEDULER_ENABLED=true and
AUTO_FUND_ENABLED=false, and proves that ticks happen while no cycles or trades
occur. Also verifies GET /scheduler/status is read-only (no tick, no writes).
"""

import asyncio
import os
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


async def _wait_for_ticks(runtime, target, timeout):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while runtime.status()["tick_count"] < target:
        if loop.time() > deadline:
            raise AssertionError(
                f"scheduler only ticked {runtime.status()['tick_count']} times"
            )
        await asyncio.sleep(0.01)


async def dry_run():
    runtime = scheduler_runtime_module.scheduler_runtime  # the one the endpoint reads
    settings.ATLAS_SCHEDULER_ENABLED = True
    settings.AUTO_FUND_ENABLED = False
    runtime._interval_seconds = 0.01  # fast ticks for the test

    await runtime.start()
    try:
        await _wait_for_ticks(runtime, 3, timeout=5)
    finally:
        await runtime.stop()

    # --- ticks happened, all skipped because auto fund is disabled ---
    snap = scheduler_status()
    metrics = snap["scheduler"]
    assert snap["auto_fund_enabled"] is False
    assert isinstance(snap["provider"], str)
    assert metrics["tick_count"] >= 3
    assert metrics["last_status"] == "SKIPPED"
    assert "disabled" in metrics["last_reason"]
    assert metrics["error_count"] == 0
    assert metrics["running"] is False  # stopped cleanly

    # --- the endpoint is read-only: repeated calls do not advance ticks ---
    first = scheduler_status()["scheduler"]["tick_count"]
    second = scheduler_status()["scheduler"]["tick_count"]
    assert first == second

    # --- no cycles / no trades: nothing was written to the fund tables ---
    assert get_paper_fund_snapshots(limit=10) == []
    assert get_paper_fund_orders(limit=10) == []
    state = get_latest_paper_fund_state()
    assert state is None or state.get("fund_status") != "RUNNING"


original_scheduler_flag = settings.ATLAS_SCHEDULER_ENABLED
original_auto_flag = settings.AUTO_FUND_ENABLED
original_path = connection.DATABASE_PATH

with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    setup_database()
    asyncio.run(dry_run())
finally:
    settings.ATLAS_SCHEDULER_ENABLED = original_scheduler_flag
    settings.AUTO_FUND_ENABLED = original_auto_flag
    scheduler_runtime_module.scheduler_runtime._interval_seconds = None
    connection.DATABASE_PATH = original_path
    connection._wal_initialized_paths.discard(database_path)
    for candidate in (database_path, f"{database_path}-wal", f"{database_path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


print("Scheduler dry-run test passed.")
