"""Tests for the repeating Live Paper Fund scheduler loop.

Covers: disabled creates no loop, enabled creates exactly one loop, the loop
calls the tick once per interval, no overlap while a previous tick is still
running, clean cancel/await shutdown, tick errors are logged loudly, a hung
tick times out (recorded as ERROR) without stopping later ticks while normal
ticks pass the watchdog untouched, and that AUTO_FUND_ENABLED=false makes
ticks skip instead of running cycles (via the real guarded tick path). It
never enables real-money execution or a broker.
"""

import asyncio
import logging
import os
import tempfile

import core.settings as settings
import database.connection as connection
from api.scheduler_runtime import LOOP_TASK_NAME, SchedulerRuntime, logger
from database.repository import get_paper_fund_snapshots
from database.setup import setup_database


def _pending_loop_tasks():
    return [
        task
        for task in asyncio.all_tasks()
        if task.get_name() == LOOP_TASK_NAME and not task.done()
    ]


async def disabled_creates_no_loop():
    settings.ATLAS_SCHEDULER_ENABLED = False
    runtime = SchedulerRuntime(
        tick=_noop_tick, interval_seconds=0.01, tick_recorder=_noop_recorder
    )
    await runtime.start()
    assert runtime.is_owned() is True
    assert runtime.active_task_count() == 0
    await runtime.stop()


async def enabled_creates_exactly_one_loop():
    settings.ATLAS_SCHEDULER_ENABLED = True
    runtime = SchedulerRuntime(
        tick=_noop_tick, interval_seconds=0.01, tick_recorder=_noop_recorder
    )
    try:
        await runtime.start()
        assert runtime.active_task_count() == 1
        # Idempotent single owner: a second start adds no loop.
        await runtime.start()
        assert runtime.active_task_count() == 1
    finally:
        await runtime.stop()
    assert runtime.active_task_count() == 0
    assert _pending_loop_tasks() == []


async def loop_calls_tick_each_interval():
    settings.ATLAS_SCHEDULER_ENABLED = True
    state = {"calls": 0}
    done = asyncio.Event()

    async def counting_tick():
        state["calls"] += 1
        if state["calls"] >= 3:
            done.set()

    runtime = SchedulerRuntime(
        tick=counting_tick, interval_seconds=0.01, tick_recorder=_noop_recorder
    )
    await runtime.start()
    try:
        await asyncio.wait_for(done.wait(), timeout=3)
    finally:
        await runtime.stop()
    # Repeated ticks prove the loop fires once per interval, not just once.
    assert state["calls"] >= 3


async def no_overlap_when_tick_slow():
    settings.ATLAS_SCHEDULER_ENABLED = True
    concurrency = {"current": 0, "max": 0, "calls": 0}
    reached = asyncio.Event()

    async def slow_tick():
        concurrency["calls"] += 1
        concurrency["current"] += 1
        concurrency["max"] = max(concurrency["max"], concurrency["current"])
        if concurrency["calls"] >= 2:
            reached.set()
        await asyncio.sleep(0.05)
        concurrency["current"] -= 1

    # Interval far shorter than tick duration: only a sequential loop keeps
    # concurrency at 1.
    runtime = SchedulerRuntime(
        tick=slow_tick, interval_seconds=0.001, tick_recorder=_noop_recorder
    )
    await runtime.start()
    try:
        await asyncio.wait_for(reached.wait(), timeout=3)
    finally:
        await runtime.stop()
    assert concurrency["max"] == 1
    assert concurrency["calls"] >= 2


async def shutdown_cancels_cleanly():
    settings.ATLAS_SCHEDULER_ENABLED = True
    runtime = SchedulerRuntime(
        tick=_noop_tick, interval_seconds=0.01, tick_recorder=_noop_recorder
    )
    await runtime.start()
    assert runtime.active_task_count() == 1
    await runtime.stop()
    assert runtime.active_task_count() == 0
    assert runtime.is_owned() is False
    assert _pending_loop_tasks() == []


async def tick_errors_are_logged():
    settings.ATLAS_SCHEDULER_ENABLED = True
    records = []

    class _Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = _Capture()
    logger.addHandler(handler)

    state = {"calls": 0}
    done = asyncio.Event()

    async def failing_tick():
        state["calls"] += 1
        if state["calls"] >= 2:
            done.set()
        raise RuntimeError("boom")

    runtime = SchedulerRuntime(
        tick=failing_tick, interval_seconds=0.001, tick_recorder=_noop_recorder
    )
    await runtime.start()
    try:
        await asyncio.wait_for(done.wait(), timeout=3)
    finally:
        await runtime.stop()
        logger.removeHandler(handler)

    # The loop survived the first error and kept ticking...
    assert state["calls"] >= 2
    # ...and the failure was logged loudly at error level with a traceback.
    assert any(record.levelno >= logging.ERROR for record in records)
    assert any(record.exc_info for record in records)


async def hung_tick_times_out_and_loop_continues():
    settings.ATLAS_SCHEDULER_ENABLED = True
    state = {"calls": 0, "hung_tick_completed": False}
    entries = []
    done = asyncio.Event()

    async def hung_then_ok_tick():
        state["calls"] += 1
        if state["calls"] == 1:
            # A hung provider/network call: far longer than the tick timeout.
            await asyncio.sleep(60)
            state["hung_tick_completed"] = True
            return None
        if state["calls"] >= 2:
            done.set()
        return {"tick": {"status": "SKIPPED", "reason": "cycle is not due yet"}}

    async def capturing_recorder(entry):
        entries.append(entry)

    runtime = SchedulerRuntime(
        tick=hung_then_ok_tick,
        interval_seconds=0.01,
        tick_recorder=capturing_recorder,
        tick_timeout_seconds=0.05,
    )
    await runtime.start()
    try:
        await asyncio.wait_for(done.wait(), timeout=5)
    finally:
        await runtime.stop()

    # The hung tick was abandoned, never treated as completed...
    assert state["hung_tick_completed"] is False
    # ...recorded honestly as an ERROR with a clear timeout reason...
    error_entries = [entry for entry in entries if entry["status"] == "ERROR"]
    assert error_entries, entries
    assert (
        "scheduler tick timed out after 0.05 seconds"
        in error_entries[0]["reason"]
    )
    # ...error telemetry incremented...
    status = runtime.status()
    assert status["error_count"] >= 1
    assert status["last_error_at"] is not None
    # ...and the loop continued to later, non-error ticks.
    assert state["calls"] >= 2
    assert any(entry["status"] == "SKIPPED" for entry in entries)


async def normal_tick_unaffected_by_timeout():
    settings.ATLAS_SCHEDULER_ENABLED = True
    entries = []
    done = asyncio.Event()

    async def quick_tick():
        return {"tick": {"status": "SKIPPED", "reason": "cycle is not due yet"}}

    async def capturing_recorder(entry):
        entries.append(entry)
        if len(entries) >= 2:
            done.set()

    runtime = SchedulerRuntime(
        tick=quick_tick,
        interval_seconds=0.01,
        tick_recorder=capturing_recorder,
        tick_timeout_seconds=5,
    )
    await runtime.start()
    try:
        await asyncio.wait_for(done.wait(), timeout=5)
    finally:
        await runtime.stop()

    # Completed ticks pass through the watchdog untouched: no errors, every
    # outcome recorded normally.
    assert len(entries) >= 2
    assert all(entry["status"] == "SKIPPED" for entry in entries)
    assert runtime.status()["error_count"] == 0


def tick_timeout_derived_from_interval():
    # 4x the interval once above the floor; never below the 30s minimum.
    assert SchedulerRuntime(interval_seconds=60)._tick_timeout() == 240
    assert SchedulerRuntime(interval_seconds=300)._tick_timeout() == 1200
    assert SchedulerRuntime(interval_seconds=1)._tick_timeout() == 30
    # Explicit override (used by tests) wins.
    assert SchedulerRuntime(tick_timeout_seconds=0.05)._tick_timeout() == 0.05
    # The watchdog deadline is part of the observability snapshot.
    assert SchedulerRuntime(interval_seconds=60).status()[
        "tick_timeout_seconds"
    ] == 240


async def auto_fund_disabled_skips_not_cycles():
    # Drive the REAL guarded tick path through the runtime against a temp db.
    settings.ATLAS_SCHEDULER_ENABLED = True
    original_auto = settings.AUTO_FUND_ENABLED
    original_path = connection.DATABASE_PATH

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
        database_path = database_file.name

    try:
        connection.DATABASE_PATH = database_path
        connection._wal_initialized_paths.discard(database_path)
        setup_database()
        settings.AUTO_FUND_ENABLED = False

        runtime = SchedulerRuntime()  # real default tick (paper_fund_tick)
        result = await runtime._invoke_tick()

        assert result["tick"]["status"] == "SKIPPED"
        assert "disabled" in result["tick"]["reason"]
        # No cycle ran: no fund snapshots were written.
        assert get_paper_fund_snapshots(limit=10) == []
    finally:
        settings.AUTO_FUND_ENABLED = original_auto
        connection.DATABASE_PATH = original_path
        connection._wal_initialized_paths.discard(database_path)
        for candidate in (database_path, f"{database_path}-wal", f"{database_path}-shm"):
            if os.path.exists(candidate):
                os.remove(candidate)


async def _noop_tick():
    return None


async def _noop_recorder(entry):
    # Tests never persist tick records to the developer database.
    return None


async def main():
    await disabled_creates_no_loop()
    await enabled_creates_exactly_one_loop()
    await loop_calls_tick_each_interval()
    await no_overlap_when_tick_slow()
    await shutdown_cancels_cleanly()
    await tick_errors_are_logged()
    await hung_tick_times_out_and_loop_continues()
    await normal_tick_unaffected_by_timeout()
    tick_timeout_derived_from_interval()
    await auto_fund_disabled_skips_not_cycles()


original_scheduler_flag = settings.ATLAS_SCHEDULER_ENABLED
try:
    asyncio.run(main())
finally:
    settings.ATLAS_SCHEDULER_ENABLED = original_scheduler_flag


print("Scheduler loop test passed.")
