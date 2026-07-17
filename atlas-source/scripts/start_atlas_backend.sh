#!/usr/bin/env bash
# Start the ATLAS backend in autonomous PAPER-ONLY mode (24/7 local server).
#
# Safety: this configures simulated paper trading only. There is no broker
# integration anywhere in ATLAS, no real money can move, and no paid APIs are
# used (yahoo market data is the free public feed).
#
# Runs uvicorn in the FOREGROUND (no --reload, for stability) so it works
# cleanly under launchd, tmux, or nohup — see docs/LOCAL_DEPLOYMENT.md.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="$REPO_ROOT/venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: venv not found at $REPO_ROOT/venv." >&2
  echo "Create it first:  python3 -m venv venv && venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

# Autonomous paper-mode configuration. Existing environment values win, so a
# launchd plist or shell profile can override intervals without editing this
# script. The four flags below are the supported 24/7 paper configuration.
export MARKET_DATA_PROVIDER="${MARKET_DATA_PROVIDER:-yahoo}"
export ATLAS_SCHEDULER_ENABLED="${ATLAS_SCHEDULER_ENABLED:-1}"
export AUTO_RESEARCH_ENABLED="${AUTO_RESEARCH_ENABLED:-1}"
export AUTO_FUND_ENABLED="${AUTO_FUND_ENABLED:-1}"

HOST="127.0.0.1"
PORT="8000"

echo "==============================================================="
echo " ATLAS backend — autonomous PAPER mode"
echo "   provider:  $MARKET_DATA_PROVIDER"
echo "   scheduler: ATLAS_SCHEDULER_ENABLED=$ATLAS_SCHEDULER_ENABLED"
echo "   research:  AUTO_RESEARCH_ENABLED=$AUTO_RESEARCH_ENABLED"
echo "   fund:      AUTO_FUND_ENABLED=$AUTO_FUND_ENABLED"
echo "   listen:    http://$HOST:$PORT"
echo "   PAPER TRADING ONLY — no broker, no real money."
echo "==============================================================="

exec "$PYTHON" -m uvicorn api.main:app --host "$HOST" --port "$PORT"
