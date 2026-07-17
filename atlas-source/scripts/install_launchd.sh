#!/usr/bin/env bash
# Install (or update) the macOS launchd agent that keeps the ATLAS backend
# running 24/7 in autonomous PAPER-ONLY mode — see docs/LOCAL_DEPLOYMENT.md §4.
#
# Safety: this only supervises scripts/start_atlas_backend.sh, which is
# paper-trading only (no broker, no real money). RunAtLoad starts it at login
# and KeepAlive restarts it if it ever exits, so the scheduler never needs a
# manual restart.
#
# Usage:
#   scripts/install_launchd.sh            # install/refresh and start
#   scripts/install_launchd.sh uninstall  # stop and remove
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.atlas.backend"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
START_SCRIPT="$REPO_ROOT/scripts/start_atlas_backend.sh"

if [[ "${1:-}" == "uninstall" ]]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Removed $PLIST and unloaded $LABEL."
  exit 0
fi

if [[ ! -x "$START_SCRIPT" ]]; then
  echo "ERROR: $START_SCRIPT not found or not executable." >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$START_SCRIPT</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/atlas-backend.log</string>
  <key>StandardErrorPath</key><string>/tmp/atlas-backend.err.log</string>
</dict>
</plist>
PLIST

# Reload cleanly whether or not an older version was running.
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "==============================================================="
echo " Installed $LABEL"
echo "   plist:  $PLIST"
echo "   runs:   $START_SCRIPT"
echo "   logs:   /tmp/atlas-backend.log (+ .err.log)"
echo ""
echo " The backend now starts at login and restarts on exit."
echo " Remaining manual step (by design): start the paper fund once"
echo " from the Paper Trading page or POST /paper-fund/start."
echo " Verify: scripts/health_check.sh"
echo "==============================================================="
