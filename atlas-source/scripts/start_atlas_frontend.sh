#!/usr/bin/env bash
# Build and serve the ATLAS frontend locally (production build via `vite
# preview`). Serves on http://localhost:5173 — this port matters: the backend
# CORS allowlist permits exactly localhost:5173 / 127.0.0.1:5173.
#
# Runs in the FOREGROUND so it works under launchd, tmux, or nohup — see
# docs/LOCAL_DEPLOYMENT.md.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/frontend"

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm is not installed. Install Node.js first." >&2
  exit 1
fi

if [[ ! -d node_modules ]]; then
  echo "Installing frontend dependencies (first run)..."
  npm install
fi

echo "Building production frontend..."
npm run build

echo "==============================================================="
echo " ATLAS frontend — http://localhost:5173"
echo " Expects the backend at http://127.0.0.1:8000"
echo " PAPER TRADING ONLY — no broker, no real money."
echo "==============================================================="

exec npm run preview -- --host 127.0.0.1 --port 5173 --strictPort
