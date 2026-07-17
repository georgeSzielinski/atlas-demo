"""Tests for scripts/health_check.sh against a local stub API.

Covers: a fresh persisted scheduler tick passes, a stale tick fails the check,
the staleness threshold is configurable via ATLAS_HEALTH_MAX_TICK_AGE_INTERVALS,
a disabled scheduler skips the staleness check, a freshly started loop with no
persisted tick yet is judged from its start time, and the pre-existing endpoint
checks still fail the run when an endpoint is unhealthy. Read-only: the stub
serves static JSON; no real backend, database, or network is touched.
"""

import json
import os
import subprocess
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "health_check.sh")

# path -> (status_code, payload); mutated per scenario.
RESPONSES = {}


class _StubHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        status, payload = RESPONSES.get(self.path, (404, {}))
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def scheduler_payload(tick_at=None, enabled=True, interval=60, started_at=None):
    return {
        "scheduler": {
            "enabled": enabled,
            "interval_seconds": interval,
            "started_at": started_at,
        },
        "last_persisted_tick": (
            {"at": tick_at, "status": "SKIPPED", "reason": "cycle is not due yet"}
            if tick_at
            else None
        ),
    }


def set_responses(scheduler):
    RESPONSES.clear()
    RESPONSES["/status"] = (200, {"status": "ok"})
    RESPONSES["/dashboard/v2"] = (200, {})
    RESPONSES["/paper-fund/status"] = (200, {
        "fund_status": "RUNNING",
        "price_provider": "yahoo",
        "next_update": "2026-07-12T12:00:00",
    })
    RESPONSES["/research-cycle/status"] = (200, {"enabled": False})
    RESPONSES["/scheduler/status"] = (200, scheduler)


def run_health_check(extra_env=None):
    env = {
        **os.environ,
        "ATLAS_API_URL": base_url,
        "ATLAS_HEALTH_TIMEOUT": "5",
    }
    env.pop("ATLAS_HEALTH_MAX_TICK_AGE_INTERVALS", None)
    env.update(extra_env or {})
    return subprocess.run(
        ["bash", SCRIPT],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


server = HTTPServer(("127.0.0.1", 0), _StubHandler)
base_url = f"http://127.0.0.1:{server.server_port}"
threading.Thread(target=server.serve_forever, daemon=True).start()

try:
    now = datetime.now()
    stale_at = (now - timedelta(seconds=3600)).isoformat()

    # Fresh persisted tick -> healthy, staleness check reported OK.
    set_responses(scheduler_payload(tick_at=now.isoformat()))
    result = run_health_check()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK   scheduler staleness" in result.stdout
    assert "RESULT: OK" in result.stdout

    # Stale tick (3600s old > default 5 x 60s intervals) -> health check FAILS.
    set_responses(scheduler_payload(tick_at=stale_at))
    result = run_health_check()
    assert result.returncode == 1, result.stdout + result.stderr
    assert "FAIL scheduler staleness" in result.stdout
    assert "RESULT: FAIL" in result.stdout

    # The threshold is configurable: a huge allowance makes the same tick pass.
    result = run_health_check({"ATLAS_HEALTH_MAX_TICK_AGE_INTERVALS": "1000"})
    assert result.returncode == 0, result.stdout + result.stderr

    # Disabled scheduler: staleness check is skipped, run stays healthy.
    set_responses(scheduler_payload(tick_at=None, enabled=False))
    result = run_health_check()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "scheduler disabled" in result.stdout

    # Enabled but no persisted tick yet: judged from the loop start time, so a
    # freshly started scheduler is healthy and a long-silent one is not.
    set_responses(scheduler_payload(tick_at=None, started_at=now.isoformat()))
    result = run_health_check()
    assert result.returncode == 0, result.stdout + result.stderr
    set_responses(scheduler_payload(tick_at=None, started_at=stale_at))
    result = run_health_check()
    assert result.returncode == 1, result.stdout + result.stderr
    assert "FAIL scheduler staleness" in result.stdout

    # Pre-existing endpoint checks are preserved: one unhealthy endpoint fails
    # the run even when scheduler telemetry is fresh.
    set_responses(scheduler_payload(tick_at=now.isoformat()))
    RESPONSES["/dashboard/v2"] = (500, {})
    result = run_health_check()
    assert result.returncode == 1, result.stdout + result.stderr
    assert "FAIL /dashboard/v2" in result.stdout
finally:
    server.shutdown()

print("Health check script test passed.")
