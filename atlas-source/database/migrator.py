"""Versioned schema migration runner for Atlas.

Run deliberately (never as a runtime side effect):

    venv/bin/python -m database.migrator

The runner tracks applied schema versions in a ``schema_migrations`` ledger
table inside the database. On each run it validates the migration registry
(`database.migrations.MIGRATIONS`), then applies every pending migration in
version order. Each migration runs in its own transaction together with its
ledger record: on failure the whole migration rolls back, nothing is recorded,
and the runner raises instead of continuing.

Safety properties:

- Fails loudly if the database ledger records a version newer than the code
  knows (downgrade protection) or an inconsistent ledger (gaps in applied
  versions).
- Never drops or recreates existing tables; migrations are additive.
- Uses the shared hardened connection factory (busy timeout, foreign keys,
  WAL), so it never opens a bare sqlite3 connection.
"""

import sys
from datetime import datetime

from database.connection import get_connection
from database.migrations import MIGRATIONS, validate_migrations


LEDGER_TABLE = "schema_migrations"


def run_migrations(migrations=None):
    """Apply pending registered migrations in order and return a summary dict."""
    registry = validate_migrations(
        MIGRATIONS if migrations is None else migrations
    )
    code_version = registry[-1].VERSION if registry else 0

    connection = get_connection()
    try:
        _ensure_ledger(connection)
        already_applied = _applied_versions(connection)
        _check_ledger_state(already_applied, code_version)

        applied_now = []
        for migration in registry:
            if migration.VERSION in already_applied:
                continue
            _apply_one(connection, migration)
            applied_now.append(
                {"version": migration.VERSION, "name": migration.NAME}
            )

        return {
            "code_version": code_version,
            "database_version": max(
                already_applied | {item["version"] for item in applied_now},
                default=0,
            ),
            "already_applied": sorted(already_applied),
            "applied_now": applied_now,
        }
    finally:
        connection.close()


def _ensure_ledger(connection):
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {LEDGER_TABLE} (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    connection.commit()


def _applied_versions(connection):
    rows = connection.execute(f"SELECT version FROM {LEDGER_TABLE}").fetchall()

    return {row[0] for row in rows}


def _check_ledger_state(applied_versions, code_version):
    if not applied_versions:
        return

    database_version = max(applied_versions)
    if database_version > code_version:
        raise RuntimeError(
            f"Database schema version {database_version} is newer than this "
            f"code's latest migration ({code_version}). Refusing to run older "
            "code against a newer database."
        )

    expected = set(range(1, database_version + 1))
    missing = sorted(expected - applied_versions)
    if missing:
        raise RuntimeError(
            f"Migration ledger is inconsistent: version {database_version} is "
            f"recorded as applied but earlier versions {missing} are not. "
            "Refusing to continue with a gapped ledger."
        )


def _apply_one(connection, migration):
    # One transaction per migration: the schema change and its ledger record
    # commit together or roll back together. Explicit BEGIN so DDL inside the
    # migration is covered by the transaction.
    connection.execute("BEGIN")
    try:
        migration.apply(connection)
        connection.execute(
            f"INSERT INTO {LEDGER_TABLE} (version, name, applied_at) "
            "VALUES (?, ?, ?)",
            (migration.VERSION, migration.NAME, datetime.now().isoformat()),
        )
        connection.commit()
    except Exception as error:
        connection.rollback()
        raise RuntimeError(
            f"Migration {migration.VERSION} ({migration.NAME}) failed and was "
            f"rolled back; nothing was recorded. Cause: {error}"
        ) from error


def main():
    import database.connection as connection_module

    try:
        summary = run_migrations()
    except Exception as error:
        print(f"Migration run FAILED: {error}")
        return 1

    print("Atlas schema migrations")
    print(f"  database         : {connection_module.DATABASE_PATH}")
    print(f"  code version     : {summary['code_version']}")
    print(f"  database version : {summary['database_version']}")
    print(f"  already applied  : {summary['already_applied'] or 'none'}")
    if summary["applied_now"]:
        print("  applied now      :")
        for item in summary["applied_now"]:
            print(f"    {item['version']:03d} {item['name']}")
    else:
        print("  applied now      : none (up to date)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
