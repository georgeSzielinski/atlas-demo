"""Tests for the backend scheduler lifecycle owner.

Covers off-by-default startup, single-owner idempotent start, exactly-one
placeholder task when enabled, clean cancel/await shutdown with no leaked tasks,
reload safety (no concurrent duplicates), safe stop when idle, and that merely
importing the API app starts no scheduler.
"""

import asyncio

import api.main as api_main
import core.settings as settings
from api.main import app, lifespan
from api.scheduler_runtime import SchedulerRuntime, scheduler_runtime


# Importing api.main must not start a scheduler: the lifespan has not run.
assert scheduler_runtime.is_owned() is False
assert scheduler_runtime.active_task_count() == 0
# The app is wired with a lifespan (ownership point exists) but is not entered.
assert app.router.lifespan_context is not None


def _pending_placeholder_tasks():
    return [
        task
        for task in asyncio.all_tasks()
        if task.get_name() == "atlas-scheduler-loop" and not task.done()
    ]


async def disabled_by_default():
    settings.ATLAS_SCHEDULER_ENABLED = False
    runtime = SchedulerRuntime()
    await runtime.start()
    # Ownership is acquired, but no background task runs when disabled.
    assert runtime.is_owned() is True
    assert runtime.active_task_count() == 0
    await runtime.stop()
    assert runtime.is_owned() is False


async def enabled_starts_exactly_one():
    settings.ATLAS_SCHEDULER_ENABLED = True
    runtime = SchedulerRuntime()
    try:
        await runtime.start()
        assert runtime.is_owned() is True
        assert runtime.active_task_count() == 1
        # Idempotent single owner: a second start does not add a task.
        await runtime.start()
        assert runtime.active_task_count() == 1
    finally:
        await runtime.stop()
    # Shutdown cancels and awaits the task cleanly, leaving nothing behind.
    assert runtime.active_task_count() == 0
    assert runtime.is_owned() is False
    assert _pending_placeholder_tasks() == []


async def safe_stop_when_idle():
    runtime = SchedulerRuntime()
    # Stop without a prior start must not raise.
    await runtime.stop()
    assert runtime.is_owned() is False
    assert runtime.active_task_count() == 0


async def reload_never_duplicates():
    # Drive the real app lifespan repeatedly (as development reload would),
    # asserting there is never more than one concurrent placeholder task.
    settings.ATLAS_SCHEDULER_ENABLED = True
    try:
        for _ in range(3):
            async with lifespan(app):
                assert scheduler_runtime.active_task_count() == 1
                assert len(_pending_placeholder_tasks()) == 1
            # After each shutdown the task is cancelled and ownership released.
            assert scheduler_runtime.active_task_count() == 0
            assert scheduler_runtime.is_owned() is False
            assert _pending_placeholder_tasks() == []
    finally:
        settings.ATLAS_SCHEDULER_ENABLED = False


async def lifespan_disabled_is_noop():
    settings.ATLAS_SCHEDULER_ENABLED = False
    async with lifespan(app):
        assert scheduler_runtime.is_owned() is True
        assert scheduler_runtime.active_task_count() == 0
    assert scheduler_runtime.is_owned() is False


async def main():
    await disabled_by_default()
    await enabled_starts_exactly_one()
    await safe_stop_when_idle()
    await reload_never_duplicates()
    await lifespan_disabled_is_noop()


original_flag = settings.ATLAS_SCHEDULER_ENABLED
original_run_migrations = api_main.run_migrations
try:
    api_main.run_migrations = lambda: None
    asyncio.run(main())
finally:
    api_main.run_migrations = original_run_migrations
    settings.ATLAS_SCHEDULER_ENABLED = original_flag


print("Scheduler lifecycle test passed.")
