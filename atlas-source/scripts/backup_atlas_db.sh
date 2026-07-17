#!/usr/bin/env bash
# Timestamped backup of database/atlas.db into backups/.
#
# Uses `sqlite3 .backup` when available — a consistent, READ-ONLY-on-source
# hot backup that is safe while the backend is running (handles WAL
# correctly). Falls back to cp with a warning if the sqlite3 CLI is missing.
# The live database file is never modified. Keeps the newest
# ATLAS_BACKUP_KEEP (default 30) backups and prunes older ones.
# Portable to macOS's default bash 3.2.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="$REPO_ROOT/database/atlas.db"
BACKUP_DIR="${ATLAS_BACKUP_DIR:-$REPO_ROOT/backups}"
KEEP="${ATLAS_BACKUP_KEEP:-30}"

if [ ! -f "$DB_PATH" ]; then
  echo "ERROR: database not found at $DB_PATH" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
STAMP="$(date '+%Y%m%d-%H%M%S')"
TARGET="$BACKUP_DIR/atlas-$STAMP.db"

if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$DB_PATH" ".backup '$TARGET'"
  # Fold the backup's WAL into the file and drop sidecars so each backup is a
  # single self-contained .db (the source database is never touched).
  sqlite3 "$TARGET" "PRAGMA wal_checkpoint(TRUNCATE);" >/dev/null
  rm -f "$TARGET-wal" "$TARGET-shm"
  METHOD="sqlite3 .backup (hot, WAL-safe)"
else
  echo "WARNING: sqlite3 CLI not found; using cp. Prefer stopping the" >&2
  echo "backend first, or install sqlite3 for a WAL-safe hot backup." >&2
  cp "$DB_PATH" "$TARGET"
  METHOD="cp (not WAL-safe while running)"
fi

SIZE="$(du -h "$TARGET" | cut -f1)"
echo "Backup written: $TARGET ($SIZE) via $METHOD"

# Retention: keep the newest $KEEP backups, prune the rest (bash-3.2-safe).
PRUNED=0
for file in $(ls -1t "$BACKUP_DIR"/atlas-*.db 2>/dev/null | tail -n "+$((KEEP + 1))"); do
  rm -f "$file" "$file-wal" "$file-shm"
  PRUNED=$((PRUNED + 1))
done
if [ "$PRUNED" -gt 0 ]; then
  echo "Pruned $PRUNED old backup(s); keeping newest $KEEP."
fi

COUNT="$(ls -1 "$BACKUP_DIR"/atlas-*.db 2>/dev/null | wc -l | tr -d ' ')"
echo "Total backups: $COUNT in $BACKUP_DIR"
