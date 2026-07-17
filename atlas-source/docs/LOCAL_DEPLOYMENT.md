# ATLAS Local 24/7 Deployment (Paper Mode)

Run ATLAS continuously on a spare Mac or local server in **autonomous paper
mode**.

> **Safety.** ATLAS has no broker integration and moves no real money — ever.
> This deployment simulates paper trades only, uses the free Yahoo market
> data feed (no paid APIs), and binds to localhost only (nothing is exposed
> to the network).

## 1. One-time setup

```bash
cd /path/to/AI-Investing-Bot

# Backend
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Make the scripts executable (first checkout only)
chmod +x scripts/*.sh
```

Sanity check: `venv/bin/python -m backend.check` should print `PASS`.

## 2. What the scripts do

| Script | Purpose |
|---|---|
| `scripts/start_atlas_backend.sh` | Backend on `http://127.0.0.1:8000` with the autonomous paper-mode flags (below). Foreground, no auto-reload. |
| `scripts/start_atlas_frontend.sh` | Production build + serve on `http://localhost:5173` (the port the backend's CORS allowlist expects). Foreground. |
| `scripts/health_check.sh` | Read-only probe of `/status`, `/dashboard/v2`, `/paper-fund/status`, `/research-cycle/status`; exit 0 only if all healthy. |
| `scripts/backup_atlas_db.sh` | Timestamped `backups/atlas-YYYYMMDD-HHMMSS.db` via WAL-safe `sqlite3 .backup`; keeps the newest 30. |

### Environment flags (set by the backend script; env overrides win)

| Flag | Value | Meaning |
|---|---|---|
| `MARKET_DATA_PROVIDER` | `yahoo` | Real validated prices (free). The mock provider is refused by every autonomous path. |
| `ATLAS_SCHEDULER_ENABLED` | `1` | Background loop ticks every `ATLAS_SCHEDULER_INTERVAL_SECONDS` (default 300). |
| `AUTO_RESEARCH_ENABLED` | `1` | Scheduled ticks generate deterministic recommendation records and run the research-only committee (default: once per day, `AUTO_RESEARCH_INTERVAL_MINUTES`). |
| `AUTO_FUND_ENABLED` | `1` | Scheduled ticks may run guarded paper-fund cycles (simulated fills only, market hours only by default). |

## 3. First start

```bash
# Terminal 1
scripts/start_atlas_backend.sh

# Terminal 2
scripts/start_atlas_frontend.sh

# Terminal 3 — verify
scripts/health_check.sh
```

Then open `http://localhost:5173`, go to **Paper Trading**, and start the
paper fund with your watchlist and virtual cash. The scheduler takes it from
there: research generation → investment committee → guarded paper-fund
cycles, all visible on the Dashboard v2 pipeline meter.

## 4. Keeping it running 24/7 (macOS launchd)

One command installs and starts the supervised backend agent
(RunAtLoad + KeepAlive, logs in `/tmp/atlas-backend*.log`):

```bash
scripts/install_launchd.sh            # install/refresh and start
scripts/install_launchd.sh uninstall  # stop and remove
```

Or create `~/Library/LaunchAgents/com.atlas.backend.plist` by hand:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.atlas.backend</string>
  <key>ProgramArguments</key>
  <array>
    <string>/path/to/AI-Investing-Bot/scripts/start_atlas_backend.sh</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/atlas-backend.log</string>
  <key>StandardErrorPath</key><string>/tmp/atlas-backend.err.log</string>
</dict>
</plist>
```

Duplicate it as `com.atlas.frontend.plist` pointing at
`start_atlas_frontend.sh` (logs to `/tmp/atlas-frontend*.log`), then:

```bash
launchctl load ~/Library/LaunchAgents/com.atlas.backend.plist
launchctl load ~/Library/LaunchAgents/com.atlas.frontend.plist
```

Alternatives: `tmux new -s atlas 'scripts/start_atlas_backend.sh'` or
`nohup scripts/start_atlas_backend.sh > /tmp/atlas-backend.log 2>&1 &`.

Also disable system sleep on the spare Mac:
`sudo pmset -a sleep 0 displaysleep 10 disksleep 0` (or System Settings →
Energy → prevent automatic sleeping).

## 5. Scheduled health checks and backups (cron)

```bash
crontab -e
```

```cron
# Health check every 10 minutes (logs failures)
*/10 * * * * /path/to/AI-Investing-Bot/scripts/health_check.sh >> /tmp/atlas-health.log 2>&1

# Database backup every 6 hours (keeps newest 30)
0 */6 * * * /path/to/AI-Investing-Bot/scripts/backup_atlas_db.sh >> /tmp/atlas-backup.log 2>&1
```

Backups land in `backups/` (git-ignored). Restore = stop the backend, copy a
backup over `database/atlas.db`, start again.

## 6. Monitoring

- **Dashboard**: `http://localhost:5173` — pipeline meter shows
  Scheduler → Research Due Check → Recommendation Generation → Investment
  Committee → Market Data → Portfolio Construction → Risk Gate →
  Paper Orders → Accounting → Learning.
- **API**: `curl http://127.0.0.1:8000/research-cycle/status` (research
  gates/due-ness), `/paper-fund/status`, `/paper-fund/preflight`
  (live-readiness), `/operations`, `/reliability`.
- **Logs**: `/tmp/atlas-backend.log` etc. (per your launchd/cron paths).

## 7. Troubleshooting

| Symptom | Check |
|---|---|
| Cycles never run | `curl :8000/research-cycle/status` — `enabled` flags; fund must be started (not OFF/PAUSED); market-hours gate (`AUTO_FUND_MARKET_HOURS_ONLY=1` by default). |
| `REFUSED ... not a real provider` | `MARKET_DATA_PROVIDER` env reached the process? launchd doesn't read your shell profile — the script sets it, but overrides must live in the plist. |
| Frontend can't reach API | Frontend must be on port **5173** (CORS allowlist); backend on 127.0.0.1:8000. |
| Fund in ERROR | `/paper-fund/status` → `last_error`; usually validated prices unavailable. Resume from the Paper Trading page after the provider recovers. |
| Port already in use | `lsof -i :8000` / `lsof -i :5173` — kill the stale process or stop the launchd job. |

## 8. Updating

```bash
launchctl unload ~/Library/LaunchAgents/com.atlas.*.plist
git pull
venv/bin/pip install -r requirements.txt
venv/bin/python -m backend.check
launchctl load ~/Library/LaunchAgents/com.atlas.backend.plist
launchctl load ~/Library/LaunchAgents/com.atlas.frontend.plist
scripts/health_check.sh
```
