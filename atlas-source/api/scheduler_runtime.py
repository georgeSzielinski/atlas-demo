"""Single-owner lifecycle manager for the backend Live Paper Fund scheduler.

This module owns starting and stopping the background scheduler for exactly one
running process. When enabled it runs one repeating loop that, every
``ATLAS_SCHEDULER_INTERVAL_SECONDS``, calls the guarded combined research/fund
tick and its isolated outcome-evidence stage. It does not duplicate fund,
trading, or evaluation logic: each engine owns its single-flight guard and
configuration/provider checks. Disabled stages report honest skips.

Safety properties:

- One owner per process: ``start`` is idempotent behind a single-owner guard, so
  duplicate imports or lifespan re-entry (e.g. development reload) cannot create
  concurrent loops.
- Off by default: ``start`` runs nothing unless ``ATLAS_SCHEDULER_ENABLED`` is
  set, so tests, CI, and development never spin up a background loop implicitly.
- No overlapping ticks: the loop awaits each tick before scheduling the next.
- Stall watchdog: every tick runs under a deterministic timeout (a multiple of
  the interval, with a floor), so one hung provider or network call can never
  stall all future ticks. A timeout is recorded as an ERROR tick with a clear
  reason and the loop continues.
- Loud errors: a tick failure is logged with a traceback and never treated as
  success; the loop keeps running.
- Clean shutdown: ``stop`` cancels and awaits the loop task and only swallows
  ``CancelledError``.
"""

import asyncio
import inspect
import logging
from datetime import datetime


logger = logging.getLogger("atlas.scheduler")

LOOP_TASK_NAME = "atlas-scheduler-loop"


class SchedulerRuntime:
    """Owns the lifecycle of the backend scheduler loop."""

    # Stall watchdog: a tick may run for at most TICK_TIMEOUT_MULTIPLIER
    # intervals (never less than MIN_TICK_TIMEOUT_SECONDS) before it is
    # abandoned, recorded as ERROR, and the loop moves on.
    TICK_TIMEOUT_MULTIPLIER = 4
    MIN_TICK_TIMEOUT_SECONDS = 30.0

    def __init__(
        self,
        tick=None,
        interval_seconds=None,
        tick_recorder=None,
        tick_timeout_seconds=None,
    ):
        self._owned = False
        self._tasks = set()
        # Injectable for tests; defaults to the real guarded tick and the
        # configured interval, both resolved at call time.
        self._tick = tick or self._default_tick
        self._interval_seconds = interval_seconds
        # Injectable for tests; defaults to a multiple of the interval.
        self._tick_timeout_seconds = tick_timeout_seconds
        # Persists every tick outcome (ran, skipped, errored) so a skipped
        # cycle always records WHY, surviving restarts. Injectable for tests.
        self._tick_recorder = tick_recorder or self._default_tick_recorder
        # Best-effort observability. Written only by the single loop coroutine
        # in _run_one_tick; read (as a plain snapshot) by the read-only
        # /scheduler/status endpoint.
        self._started_at = None
        self._tick_count = 0
        self._last_tick_at = None
        self._last_status = None
        self._last_reason = None
        self._error_count = 0
        self._last_error_at = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def start(self):
        """Acquire ownership and, if enabled, launch the single loop task.

        Idempotent: a second call while already owned is a no-op, so the process
        can only ever run one scheduler loop.
        """
        if self._owned:
            return

        self._owned = True

        if not self._enabled():
            return

        self._started_at = datetime.now().isoformat()
        task = asyncio.create_task(self._run_loop(), name=LOOP_TASK_NAME)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def stop(self):
        """Cancel and await every tracked task, then release ownership."""
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()

        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks.clear()
        self._owned = False

    # ------------------------------------------------------------------
    # Introspection (used by tests)
    # ------------------------------------------------------------------
    def is_owned(self):
        return self._owned

    def active_task_count(self):
        return len(self._tasks)

    def status(self):
        """Read-only metrics snapshot for observability.

        Pure reads only: it never runs a tick, calls run_due_cycle, touches the
        database, or writes anything.
        """
        return {
            "enabled": self._enabled(),
            "owned": self._owned,
            "running": self.active_task_count() > 0,
            "interval_seconds": self._interval(),
            "tick_timeout_seconds": self._tick_timeout(),
            "started_at": self._started_at,
            "tick_count": self._tick_count,
            "last_tick_at": self._last_tick_at,
            "last_status": self._last_status,
            "last_reason": self._last_reason,
            "error_count": self._error_count,
            "last_error_at": self._last_error_at,
        }

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------
    async def _run_loop(self):
        # Await each tick before the next sleep: a slow tick cannot overlap the
        # next one. Cancellation propagates out of sleep/await for clean stop.
        while True:
            await asyncio.sleep(self._interval())
            await self._run_one_tick()

    async def _run_one_tick(self):
        started_at = datetime.now()
        timeout = self._tick_timeout()
        try:
            # Stall watchdog: a completed tick returns normally; only a tick
            # still running at the deadline is cancelled and recorded as
            # ERROR. The loop always continues to the next tick.
            result = await asyncio.wait_for(self._invoke_tick(), timeout=timeout)
        except asyncio.CancelledError:
            raise
        except asyncio.TimeoutError:
            self._error_count += 1
            self._last_error_at = datetime.now().isoformat()
            reason = f"scheduler tick timed out after {timeout:g} seconds"
            logger.error("Live Paper Fund scheduler tick stalled: %s", reason)
            await self._persist_tick(started_at, "ERROR", reason, [])
            return
        except Exception as error:
            # Log loudly with a traceback; never treat a failed tick as success.
            self._error_count += 1
            self._last_error_at = datetime.now().isoformat()
            logger.exception("Live Paper Fund scheduler tick failed")
            await self._persist_tick(
                started_at, "ERROR", f"{type(error).__name__}: {error}", []
            )
            return

        await self._record_tick(result, started_at)

    async def _record_tick(self, result, started_at):
        status, reason = self._summarize(result)
        self._tick_count += 1
        self._last_tick_at = datetime.now().isoformat()
        self._last_status = status
        self._last_reason = reason
        logger.info(
            "Live Paper Fund scheduler tick #%d: %s%s",
            self._tick_count,
            status,
            f" ({reason})" if reason else "",
        )
        await self._persist_tick(started_at, status, reason, self._stages(result))

    async def _persist_tick(self, started_at, status, reason, stages):
        """Best-effort durable tick record; a write failure never stops the loop."""
        entry = {
            "at": started_at.isoformat(),
            "status": status,
            "reason": reason,
            "stages": stages,
            "duration_seconds": round(
                max(0.0, (datetime.now() - started_at).total_seconds()), 3
            ),
        }
        try:
            recorder = self._tick_recorder
            result = recorder(entry)
            if inspect.isawaitable(result):
                await result
        except Exception:
            logger.exception("Failed to persist scheduler tick record")

    def _stages(self, result):
        """Compact per-stage summary from a research-cycle tick result."""
        if not isinstance(result, dict):
            return []
        inner = result.get("tick")
        inner = inner if isinstance(inner, dict) else {}
        stages = inner.get("stages")
        if not isinstance(stages, list):
            return []
        return [
            {
                "stage": stage.get("stage"),
                "status": stage.get("status"),
                "reason": stage.get("reason"),
                "duration_seconds": stage.get("duration_seconds"),
            }
            for stage in stages
            if isinstance(stage, dict)
        ]

    def _summarize(self, result):
        if not isinstance(result, dict):
            return "ok", None

        inner = result.get("tick")
        inner = inner if isinstance(inner, dict) else {}
        status = (
            inner.get("cycle_status")
            or inner.get("status")
            or result.get("status")
            or "ok"
        )
        reason = inner.get("reason") or inner.get("error")

        return status, reason

    async def _invoke_tick(self):
        result = self._tick()
        if inspect.isawaitable(result):
            return await result

        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _enabled(self):
        # Read at call time so tests and env can toggle it deterministically.
        from core import settings

        return settings.ATLAS_SCHEDULER_ENABLED

    def _interval(self):
        if self._interval_seconds is not None:
            return max(0.0, float(self._interval_seconds))

        from core import settings

        return max(0.0, float(settings.ATLAS_SCHEDULER_INTERVAL_SECONDS))

    def _tick_timeout(self):
        if self._tick_timeout_seconds is not None:
            return max(0.0, float(self._tick_timeout_seconds))

        return max(
            self.MIN_TICK_TIMEOUT_SECONDS,
            self._interval() * self.TICK_TIMEOUT_MULTIPLIER,
        )

    async def _default_tick(self):
        # Call the guarded combined tick (research -> committee -> unchanged
        # paper fund -> isolated outcome evidence). Every disabled stage is a
        # safe skip. It is synchronous and does blocking DB I/O, so run it in a
        # worker thread. Imported lazily to avoid a circular import with main.
        from api.main import scheduled_cycle_tick

        return await asyncio.to_thread(scheduled_cycle_tick)

    async def _default_tick_recorder(self, entry):
        # Single blocking sqlite insert; run off the event loop.
        from database.repository import add_scheduler_tick

        return await asyncio.to_thread(add_scheduler_tick, entry)


# Process-wide single owner.
scheduler_runtime = SchedulerRuntime()
