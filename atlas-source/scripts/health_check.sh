#!/usr/bin/env bash
# ATLAS health check: probes the read-only status endpoints and reports
# OK/FAIL per endpoint, then verifies the scheduler's persisted tick telemetry
# is not stale. Exit code 0 only when every check passes, so it can drive
# cron alerts or launchd KeepAlive decisions.
#
# Read-only: only GET requests; never triggers a tick, cycle, or write.
# Portable to macOS's default bash 3.2.
#
# Configuration:
#   ATLAS_API_URL                        base URL (default http://127.0.0.1:8000)
#   ATLAS_HEALTH_TIMEOUT                 per-request curl timeout in seconds
#   ATLAS_HEALTH_MAX_TICK_AGE_INTERVALS  scheduler staleness threshold: fail when
#                                        the last persisted tick is older than
#                                        this many scheduler intervals (default 5)
set -uo pipefail

BASE_URL="${ATLAS_API_URL:-http://127.0.0.1:8000}"
TIMEOUT="${ATLAS_HEALTH_TIMEOUT:-15}"
MAX_TICK_AGE_INTERVALS="${ATLAS_HEALTH_MAX_TICK_AGE_INTERVALS:-5}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$REPO_ROOT/venv/bin/python"

ENDPOINTS="/status /dashboard/v2 /paper-fund/status /research-cycle/status"

failures=0
total=0
echo "ATLAS health check against $BASE_URL ($(date '+%Y-%m-%d %H:%M:%S'))"

for endpoint in $ENDPOINTS; do
  total=$((total + 1))
  code="$(curl -s -o /dev/null -w '%{http_code}' \
    --max-time "$TIMEOUT" "$BASE_URL$endpoint" 2>/dev/null || true)"
  code="${code:-000}"
  if [ "$code" = "200" ]; then
    echo "  OK   $endpoint (200)"
  else
    echo "  FAIL $endpoint (HTTP $code)"
    failures=$((failures + 1))
  fi
done

# Scheduler staleness: when the scheduler is enabled, the last persisted tick
# (from /scheduler/status) must be newer than MAX_TICK_AGE_INTERVALS scheduler
# intervals; otherwise the loop is presumed stalled and the check fails. When
# the scheduler is disabled the check passes with a note. Read-only.
if [ -x "$PYTHON" ]; then
  total=$((total + 1))
  if curl -s --max-time "$TIMEOUT" "$BASE_URL/scheduler/status" 2>/dev/null \
    | ATLAS_HEALTH_MAX_TICK_AGE_INTERVALS="$MAX_TICK_AGE_INTERVALS" "$PYTHON" -c '
import json, os, sys
from datetime import datetime

try:
    data = json.load(sys.stdin)
except Exception:
    print("  FAIL scheduler staleness (/scheduler/status unreadable)")
    raise SystemExit(1)

scheduler = data.get("scheduler") or {}
if not scheduler.get("enabled"):
    print("  OK   scheduler staleness (scheduler disabled; check skipped)")
    raise SystemExit(0)

try:
    interval = float(scheduler.get("interval_seconds") or 0)
    max_intervals = float(
        os.environ.get("ATLAS_HEALTH_MAX_TICK_AGE_INTERVALS", "5")
    )
except ValueError:
    print("  FAIL scheduler staleness (unreadable interval configuration)")
    raise SystemExit(1)
if interval <= 0 or max_intervals <= 0:
    print("  OK   scheduler staleness (no positive interval; check skipped)")
    raise SystemExit(0)

# Prefer the durable tick record; a freshly started loop that has not yet
# persisted a tick is judged from its start time instead of failing instantly.
tick = data.get("last_persisted_tick") or {}
reference = tick.get("at") or scheduler.get("started_at")
label = "last tick" if tick.get("at") else "scheduler start"
if not reference:
    print("  FAIL scheduler staleness (enabled but no tick or start time)")
    raise SystemExit(1)

try:
    reference_at = datetime.fromisoformat(str(reference))
except ValueError:
    print("  FAIL scheduler staleness (unreadable timestamp: %r)" % reference)
    raise SystemExit(1)

age = (datetime.now() - reference_at).total_seconds()
limit = interval * max_intervals
if age > limit:
    print(
        "  FAIL scheduler staleness (%s %.0fs ago > limit %.0fs = %g x %gs interval)"
        % (label, age, limit, max_intervals, interval)
    )
    raise SystemExit(1)
print(
    "  OK   scheduler staleness (%s %.0fs ago, limit %.0fs)"
    % (label, age, limit)
)
'; then
    :
  else
    failures=$((failures + 1))
  fi
else
  echo "  ---- scheduler staleness check skipped (no venv python)"
fi

# Best-effort operational summary (read-only; skipped if anything failed).
if [ "$failures" -eq 0 ] && [ -x "$PYTHON" ]; then
  curl -s --max-time "$TIMEOUT" "$BASE_URL/paper-fund/status" \
    | "$PYTHON" -c '
import json, sys
try:
    data = json.load(sys.stdin)
    print(
        "  ---- fund=%s provider=%s next_cycle=%s"
        % (
            data.get("fund_status", "?"),
            data.get("price_provider", "?"),
            data.get("next_update", "?"),
        )
    )
except Exception:
    print("  ---- fund summary unavailable")
' || true
  curl -s --max-time "$TIMEOUT" "$BASE_URL/research-cycle/status" \
    | "$PYTHON" -c '
import json, sys
try:
    data = json.load(sys.stdin)
    print(
        "  ---- research_enabled=%s research_due=%s last_run=%s"
        % (
            data.get("enabled"),
            data.get("research_due"),
            data.get("last_recommendation_run_time"),
        )
    )
except Exception:
    print("  ---- research summary unavailable")
' || true
fi

if [ "$failures" -gt 0 ]; then
  echo "RESULT: FAIL ($failures of $total checks unhealthy)"
  exit 1
fi
echo "RESULT: OK (all $total checks healthy) — paper mode only"
exit 0
