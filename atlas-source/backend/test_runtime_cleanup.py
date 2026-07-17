"""Runtime cleanup tests for API startup migrations and handler schema repair."""

import asyncio
from pathlib import Path

import api.main as api_main


source = Path("api/main.py").read_text()
assert "setup_database()" not in source
assert "from database.setup import setup_database" not in source


async def startup_runs_migrations_once_before_scheduler():
    events = []
    original_run_migrations = api_main.run_migrations
    original_start = api_main.scheduler_runtime.start
    original_stop = api_main.scheduler_runtime.stop

    def fake_run_migrations():
        events.append("migrations")
        return {
            "code_version": 2,
            "database_version": 2,
            "already_applied": [1, 2],
            "applied_now": [],
        }

    async def fake_start():
        events.append("scheduler_start")

    async def fake_stop():
        events.append("scheduler_stop")

    try:
        api_main.run_migrations = fake_run_migrations
        api_main.scheduler_runtime.start = fake_start
        api_main.scheduler_runtime.stop = fake_stop

        async with api_main.lifespan(api_main.app):
            assert events == ["migrations", "scheduler_start"]

        assert events == ["migrations", "scheduler_start", "scheduler_stop"]
        assert events.count("migrations") == 1
    finally:
        api_main.run_migrations = original_run_migrations
        api_main.scheduler_runtime.start = original_start
        api_main.scheduler_runtime.stop = original_stop


asyncio.run(startup_runs_migrations_once_before_scheduler())

print("Runtime cleanup test passed.")
