"""Tests for the hardened shared SQLite connection factory.

Covers the explicit busy timeout, foreign-key enforcement, WAL journal mode for
file databases, independent per-path WAL initialization under monkeypatched
DATABASE_PATH, transaction atomicity (commit persists / rollback discards),
foreign-key violations raising, error propagation (no silent swallowing), and
concurrent WAL reads while another connection holds an uncommitted write.
"""

import os
import sqlite3
import tempfile

import database.connection as connection
from database.connection import BUSY_TIMEOUT_MS, get_connection


original_database_path = connection.DATABASE_PATH

with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as second_database_file:
    second_database_path = second_database_file.name


def _sidecars(path):
    return [f"{path}-wal", f"{path}-shm"]


try:
    connection.DATABASE_PATH = database_path
    # A fresh path starts uninitialized.
    connection._wal_initialized_paths.discard(database_path)
    connection._wal_initialized_paths.discard(second_database_path)

    # --- explicit busy timeout ---
    conn = get_connection()
    busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    assert busy_timeout == BUSY_TIMEOUT_MS, busy_timeout
    assert BUSY_TIMEOUT_MS > 0

    # --- foreign keys enabled on every connection ---
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    # --- WAL enabled for a temporary file database ---
    assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert database_path in connection._wal_initialized_paths
    conn.close()

    # --- monkeypatched database paths initialize independently ---
    connection.DATABASE_PATH = second_database_path
    conn2 = get_connection()
    assert conn2.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert conn2.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert second_database_path in connection._wal_initialized_paths
    # The first path stays independently tracked.
    assert database_path in connection._wal_initialized_paths
    conn2.close()

    # Back to the primary test database for the remaining cases.
    connection.DATABASE_PATH = database_path

    setup = get_connection()
    setup.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, value TEXT)")
    setup.commit()
    setup.close()

    # --- committed writes persist ---
    writer = get_connection()
    writer.execute("INSERT INTO t (id, value) VALUES (1, 'kept')")
    writer.commit()
    writer.close()
    reader = get_connection()
    assert reader.execute("SELECT value FROM t WHERE id = 1").fetchone()[0] == "kept"
    reader.close()

    # --- rolled-back writes do not persist ---
    rollback_conn = get_connection()
    rollback_conn.execute("INSERT INTO t (id, value) VALUES (2, 'discarded')")
    rollback_conn.rollback()
    rollback_conn.close()
    check = get_connection()
    assert check.execute("SELECT COUNT(*) FROM t WHERE id = 2").fetchone()[0] == 0
    check.close()

    # --- foreign-key violations raise IntegrityError ---
    fk = get_connection()
    fk.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
    fk.execute(
        "CREATE TABLE child ("
        "id INTEGER PRIMARY KEY, "
        "parent_id INTEGER REFERENCES parent(id))"
    )
    fk.commit()
    raised = False
    try:
        fk.execute("INSERT INTO child (id, parent_id) VALUES (1, 999)")
        fk.commit()
    except sqlite3.IntegrityError:
        raised = True
    assert raised, "orphan child insert must raise IntegrityError"
    fk.close()

    # --- SQL/write errors propagate rather than being swallowed ---
    err = get_connection()
    propagated = False
    try:
        err.execute("SELECT * FROM table_that_does_not_exist")
    except sqlite3.OperationalError:
        propagated = True
    assert propagated, "operational errors must propagate"
    err.close()

    # --- multiple connections can read while another holds an uncommitted
    #     write under WAL ---
    baseline = get_connection()
    baseline.execute("CREATE TABLE wal_t (id INTEGER PRIMARY KEY)")
    baseline.execute("INSERT INTO wal_t (id) VALUES (1)")
    baseline.commit()
    baseline.close()

    writer_open = get_connection()
    writer_open.execute("INSERT INTO wal_t (id) VALUES (2)")  # opens a transaction
    # Another connection reads concurrently without a lock error and sees only
    # the committed snapshot (not the writer's uncommitted row).
    concurrent_reader = get_connection()
    assert concurrent_reader.execute("SELECT COUNT(*) FROM wal_t").fetchone()[0] == 1
    concurrent_reader.close()
    writer_open.commit()
    after_commit = get_connection()
    assert after_commit.execute("SELECT COUNT(*) FROM wal_t").fetchone()[0] == 2
    after_commit.close()
    writer_open.close()
finally:
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(database_path)
    connection._wal_initialized_paths.discard(second_database_path)
    for path in (database_path, second_database_path):
        for candidate in [path, *_sidecars(path)]:
            if os.path.exists(candidate):
                os.remove(candidate)


print("Connection test passed.")
