"""Single SQLite connection factory for Atlas.

Every database connection in the app is created here so hardening is applied in
one place. On each connection we set an explicit busy timeout and enable foreign
keys. WAL journal mode is a persistent, file-level property, so it is enabled
once per database path behind a thread-safe guard rather than re-issued on every
connection (which could add unnecessary locking).

Transaction behavior is intentionally left at sqlite3's default
(``isolation_level=""``): implicit transactions with commit on ``.commit()``.
This helper only sets connection PRAGMAs; it never opens or commits a
transaction, so existing atomicity is preserved.
"""

import os
import sqlite3
import threading


DATABASE_PATH = "database/atlas.db"

# Explicit busy timeout (SQLite otherwise relies on the implicit sqlite3 default).
BUSY_TIMEOUT_MS = int(os.environ.get("ATLAS_SQLITE_BUSY_TIMEOUT_MS", "5000"))

# Thread-safe guard so WAL is initialized once per database path. Keyed by the
# resolved path string so tests that monkeypatch DATABASE_PATH to different temp
# files each initialize independently.
_wal_lock = threading.Lock()
_wal_initialized_paths = set()


def get_connection():
    path = DATABASE_PATH
    connection = sqlite3.connect(path, timeout=BUSY_TIMEOUT_MS / 1000)
    _apply_connection_pragmas(connection)
    _ensure_wal_initialized(connection, path)

    return connection


def _apply_connection_pragmas(connection):
    # Per-connection settings: these do not persist in the database file, so
    # they must be set on every connection.
    connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    connection.execute("PRAGMA foreign_keys = ON")


def _ensure_wal_initialized(connection, path):
    # WAL is a persistent, file-level journal mode. Enable it once per path.
    if _is_memory_database(path):
        # WAL is unsupported for in-memory databases; DELETE mode is expected.
        return

    if path in _wal_initialized_paths:
        return

    with _wal_lock:
        if path in _wal_initialized_paths:
            return

        row = connection.execute("PRAGMA journal_mode = WAL").fetchone()
        mode = (row[0] if row else "").lower()
        if mode != "wal":
            # A normal file database must run in WAL for the hardening to hold.
            # Fail loudly instead of silently continuing in DELETE mode.
            raise RuntimeError(
                f"Could not enable WAL journal mode for database {path!r}; "
                f"got journal_mode={mode!r}. Refusing to continue in a "
                "non-WAL mode for a file database."
            )

        _wal_initialized_paths.add(path)


def _is_memory_database(path):
    normalized = str(path).strip().lower()

    return (
        normalized in ("", ":memory:")
        or "mode=memory" in normalized
    )
