"""Regression tests: every scheduler tick outcome is persisted with its reason.

Covers: ok/skip ticks write scheduler_ticks rows (so a skipped cycle always
records WHY), tick errors write an ERROR row and the loop keeps running, a
timed-out (hung) tick writes an ERROR row with a clear timeout reason and the
loop keeps running, a
recorder failure never stops the loop, pruning bounds the table, and
/scheduler/status exposes the last persisted tick. Runs against a throwaway
temporary database; database/atlas.db is never touched.
"""

import asyncio
import os
import tempfile

import core.settings as settings
import database.connection as connection
import database.repository as repository
from api.scheduler_runtime import SchedulerRuntime
from database.migrator import run_migrations
from database.repository import (
    add_scheduler_tick,
    get_latest_scheduler_tick,
    get_scheduler_ticks,
)


def cleanup_database(path):
    connection._wal_initialized_paths.discard(path)
    for candidate in (path, f"{path}-wal", f"{path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


async def skip_ticks_persist_reason():
    done = asyncio.Event()

    async def skipping_tick():
        if len(get_scheduler_ticks(limit=10)) >= 2:
            done.set()
        return {
            "tick": {"status": "SKIPPED", "reason": "market is closed"},
            "status": "SKIPPED",
        }

    runtime = SchedulerRuntime(tick=skipping_tick, interval_seconds=0.01)
    await runtime.start()
    try:
        await asyncio.wait_for(done.wait(), timeout=5)
    finally:
        await runtime.stop()

    ticks = get_scheduler_ticks(limit=10)
    assert len(ticks) >= 2
    assert all(tick["status"] == "SKIPPED" for tick in ticks)
    assert all(tick["reason"] == "market is closed" for tick in ticks)
    assert all(tick["duration_seconds"] is not None for tick in ticks)


async def error_ticks_persist_and_loop_survives():
    state = {"calls": 0}
    done = asyncio.Event()

    async def failing_then_ok_tick():
        state["calls"] += 1
        if state["calls"] >= 3:
            done.set()
        if state["calls"] == 1:
            raise RuntimeError("provider exploded")
        return {"tick": {"status": "SKIPPED", "reason": "cycle is not due yet"}}

    runtime = SchedulerRuntime(tick=failing_then_ok_tick, interval_seconds=0.01)
    await runtime.start()
    try:
        await asyncio.wait_for(done.wait(), timeout=5)
    finally:
        await runtime.stop()

    ticks = get_scheduler_ticks(limit=50)
    statuses = [tick["status"] for tick in ticks]
    assert "ERROR" in statuses  # the failure itself was recorded WHY included
    error_tick = next(tick for tick in ticks if tick["status"] == "ERROR")
    assert "provider exploded" in error_tick["reason"]
    # The loop survived the error and kept recording later ticks.
    assert statuses.count("SKIPPED") >= 2


async def timeout_ticks_persist_and_loop_survives():
    state = {"calls": 0}
    done = asyncio.Event()

    async def hung_then_ok_tick():
        state["calls"] += 1
        if state["calls"] == 1:
            # Hung provider call: far longer than the injected tick timeout.
            await asyncio.sleep(60)
            return None
        if state["calls"] >= 2:
            done.set()
        return {"tick": {"status": "SKIPPED", "reason": "cycle is not due yet"}}

    runtime = SchedulerRuntime(
        tick=hung_then_ok_tick,
        interval_seconds=0.01,
        tick_timeout_seconds=0.05,
    )
    await runtime.start()
    try:
        await asyncio.wait_for(done.wait(), timeout=5)
    finally:
        await runtime.stop()

    ticks = get_scheduler_ticks(limit=50)
    timeout_tick = next(
        tick for tick in ticks
        if tick["status"] == "ERROR" and "timed out" in (tick["reason"] or "")
    )
    # The timeout is persisted honestly, as ERROR with a clear reason...
    assert (
        "scheduler tick timed out after 0.05 seconds" in timeout_tick["reason"]
    )
    assert timeout_tick["duration_seconds"] is not None
    # ...and the loop went on to record later ticks.
    assert any(tick["status"] == "SKIPPED" for tick in ticks)


async def recorder_failure_never_stops_loop():
    state = {"calls": 0}
    done = asyncio.Event()

    async def counting_tick():
        state["calls"] += 1
        if state["calls"] >= 3:
            done.set()
        return {"tick": {"status": "SKIPPED", "reason": "fund is off"}}

    def broken_recorder(entry):
        raise RuntimeError("disk on fire")

    runtime = SchedulerRuntime(
        tick=counting_tick, interval_seconds=0.01, tick_recorder=broken_recorder
    )
    await runtime.start()
    try:
        await asyncio.wait_for(done.wait(), timeout=5)
    finally:
        await runtime.stop()

    assert state["calls"] >= 3


def pruning_bounds_the_table():
    original_max = repository.SCHEDULER_TICKS_MAX_ROWS
    repository.SCHEDULER_TICKS_MAX_ROWS = 5
    try:
        for index in range(12):
            add_scheduler_tick({
                "at": f"2026-07-12T10:00:{index:02d}",
                "status": "SKIPPED",
                "reason": f"reason-{index}",
                "stages": [],
                "duration_seconds": 0.001,
            })
        ticks = get_scheduler_ticks(limit=100)
        assert len(ticks) == 5
        # Newest rows survive pruning.
        assert ticks[0]["reason"] == "reason-11"
    finally:
        repository.SCHEDULER_TICKS_MAX_ROWS = original_max


def status_reports_last_persisted_tick():
    from api.main import scheduler_status

    add_scheduler_tick({
        "at": "2026-07-12T11:00:00",
        "status": "SKIPPED",
        "reason": "cycle is not due yet",
        "stages": [{"stage": "paper_fund", "status": "SKIPPED"}],
        "duration_seconds": 0.002,
    })
    snap = scheduler_status()
    last = snap["last_persisted_tick"]
    assert last is not None
    assert last["status"] == "SKIPPED"
    assert last["reason"] == "cycle is not due yet"
    assert last == get_latest_scheduler_tick()


original_database_path = connection.DATABASE_PATH
original_scheduler_flag = settings.ATLAS_SCHEDULER_ENABLED
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()
    settings.ATLAS_SCHEDULER_ENABLED = True

    asyncio.run(skip_ticks_persist_reason())
    asyncio.run(error_ticks_persist_and_loop_survives())
    asyncio.run(timeout_ticks_persist_and_loop_survives())
    asyncio.run(recorder_failure_never_stops_loop())
    pruning_bounds_the_table()
    status_reports_last_persisted_tick()
finally:
    settings.ATLAS_SCHEDULER_ENABLED = original_scheduler_flag
    connection.DATABASE_PATH = original_database_path
    cleanup_database(database_path)

print("Scheduler persistence test passed.")
