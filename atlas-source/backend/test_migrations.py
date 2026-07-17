"""Tests for the versioned schema migration framework and migration 001.

Deterministic and offline, against throwaway temporary databases (never
database/atlas.db). Covers: empty-registry no-op, registry validation
(duplicates, non-contiguous versions, ordering), ledger recording, idempotent
re-runs, rollback of failed migrations, incremental upgrades, downgrade
protection when the database is newer than the code, gapped-ledger detection,
the CLI entry point, and migration 001: fresh databases build the full
baseline schema identical to setup_database(), existing databases with data
are stamped without data loss.
"""

import os
import tempfile
from types import SimpleNamespace

import database.connection as connection
from database.connection import get_connection
from database.migrations import (
    migration_001_baseline,
    migration_002_additive_columns,
    migration_003_risk_decisions,
    validate_migrations,
)
from database.migrator import LEDGER_TABLE, main, run_migrations
from database.setup import setup_database


def _migration(version, name, apply_callable):
    return SimpleNamespace(VERSION=version, NAME=name, apply=apply_callable)


def _table_exists(name):
    db = get_connection()
    try:
        row = db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (name,),
        ).fetchone()
        return row is not None
    finally:
        db.close()


def _ledger_rows():
    db = get_connection()
    try:
        return db.execute(
            f"SELECT version, name, applied_at FROM {LEDGER_TABLE} "
            "ORDER BY version"
        ).fetchall()
    finally:
        db.close()


def _create_named_table(table_name):
    def apply(db):
        db.execute(
            f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY, note TEXT)"
        )
        db.execute(f"INSERT INTO {table_name} (note) VALUES ('seeded')")

    return apply


original_database_path = connection.DATABASE_PATH

with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)

    # --- empty registry: ledger is created, nothing applied, version 0 ---
    summary = run_migrations(migrations=[])
    assert summary == {
        "code_version": 0,
        "database_version": 0,
        "already_applied": [],
        "applied_now": [],
    }
    assert _table_exists(LEDGER_TABLE)
    assert _ledger_rows() == []

    # --- registry validation: duplicate versions are rejected ---
    try:
        validate_migrations(
            [
                _migration(1, "one", lambda db: None),
                _migration(1, "one again", lambda db: None),
            ]
        )
        raise AssertionError("duplicate versions were not rejected")
    except ValueError as error:
        assert "unique" in str(error).lower()

    # --- registry validation: non-contiguous versions are rejected ---
    try:
        validate_migrations(
            [
                _migration(1, "one", lambda db: None),
                _migration(3, "three", lambda db: None),
            ]
        )
        raise AssertionError("non-contiguous versions were not rejected")
    except ValueError as error:
        assert "contiguous" in str(error).lower()

    # --- registry validation: versions must start at 1 ---
    try:
        validate_migrations([_migration(2, "two", lambda db: None)])
        raise AssertionError("registry not starting at 1 was not rejected")
    except ValueError as error:
        assert "contiguous" in str(error).lower()

    # --- registry validation: shape errors fail loudly ---
    try:
        validate_migrations([SimpleNamespace(VERSION="1", NAME="bad")])
        raise AssertionError("non-integer VERSION was not rejected")
    except ValueError:
        pass

    # --- ordering: an out-of-order registry is applied in version order ---
    applied_order = []
    ordering_registry = [
        _migration(2, "second", lambda db: applied_order.append(2)),
        _migration(1, "first", lambda db: applied_order.append(1)),
    ]
    summary = run_migrations(migrations=ordering_registry)
    assert applied_order == [1, 2]
    assert [item["version"] for item in summary["applied_now"]] == [1, 2]

    # --- ledger recorded both migrations with names and timestamps ---
    rows = _ledger_rows()
    assert [(row[0], row[1]) for row in rows] == [(1, "first"), (2, "second")]
    assert all(row[2] for row in rows)

    # --- second run is idempotent: nothing re-applies, ledger unchanged ---
    summary = run_migrations(migrations=ordering_registry)
    assert summary["applied_now"] == []
    assert summary["already_applied"] == [1, 2]
    assert summary["database_version"] == 2
    assert applied_order == [1, 2]
    assert _ledger_rows() == rows

    # --- incremental upgrade: only the new pending migration applies ---
    incremental_registry = ordering_registry + [
        _migration(3, "adds m3_table", _create_named_table("m3_table"))
    ]
    summary = run_migrations(migrations=incremental_registry)
    assert [item["version"] for item in summary["applied_now"]] == [3]
    assert summary["database_version"] == 3
    assert _table_exists("m3_table")

    # --- failed migration rolls back atomically and is not recorded ---
    def failing_apply(db):
        db.execute("CREATE TABLE m4_table (id INTEGER PRIMARY KEY)")
        db.execute("INSERT INTO m4_table (id) VALUES (1)")
        raise RuntimeError("simulated migration failure")

    failing_registry = incremental_registry + [
        _migration(4, "broken", failing_apply)
    ]
    try:
        run_migrations(migrations=failing_registry)
        raise AssertionError("failed migration did not raise")
    except RuntimeError as error:
        assert "Migration 4 (broken) failed" in str(error)
        assert "rolled back" in str(error)
    assert not _table_exists("m4_table")  # DDL + DML rolled back together
    assert [row[0] for row in _ledger_rows()] == [1, 2, 3]  # not recorded
    assert _table_exists("m3_table")  # earlier migrations untouched

    # --- database newer than code fails loudly (downgrade protection) ---
    db = get_connection()
    db.execute(
        f"INSERT INTO {LEDGER_TABLE} (version, name, applied_at) "
        "VALUES (99, 'from the future', 'sometime')"
    )
    db.commit()
    db.close()
    try:
        run_migrations(migrations=incremental_registry)
        raise AssertionError("newer database version was not rejected")
    except RuntimeError as error:
        assert "newer than this code" in str(error)
    db = get_connection()
    db.execute(f"DELETE FROM {LEDGER_TABLE} WHERE version = 99")
    db.commit()
    db.close()

    # --- gapped ledger fails loudly ---
    db = get_connection()
    db.execute(f"DELETE FROM {LEDGER_TABLE} WHERE version = 2")
    db.commit()
    db.close()
    try:
        run_migrations(migrations=incremental_registry)
        raise AssertionError("gapped ledger was not rejected")
    except RuntimeError as error:
        assert "inconsistent" in str(error)
finally:
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(database_path)
    for candidate in (database_path, f"{database_path}-wal", f"{database_path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


def _column_names(table):
    db = get_connection()
    try:
        return {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
    finally:
        db.close()


def _schema_dump():
    """Map of table name -> stored CREATE statement for the baseline tables."""
    db = get_connection()
    try:
        rows = db.execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    finally:
        db.close()

    return {
        name: sql
        for name, sql in rows
        if name in migration_001_baseline.TABLES
    }


# --- migrations on a fresh database build baseline schema and risk audit table ---
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    fresh_path = database_file.name

try:
    connection.DATABASE_PATH = fresh_path
    connection._wal_initialized_paths.discard(fresh_path)

    summary = run_migrations()  # production registry
    assert summary["code_version"] == 5
    assert summary["database_version"] == 5
    assert [
        (item["version"], item["name"]) for item in summary["applied_now"]
    ] == [
        (1, "baseline schema"),
        (2, "additive column reconciliation"),
        (3, "risk decision audit log"),
        (4, "autonomous cycle evidence"),
        (5, "outcome tracking"),
    ]

    assert len(migration_001_baseline.TABLES) == 32
    for table in migration_001_baseline.TABLES:
        assert _table_exists(table), f"missing baseline table: {table}"
    assert _table_exists("risk_decisions")
    assert _column_names("risk_decisions") == {
        "decision_id",
        "cycle_id",
        "run_id",
        "symbol",
        "side",
        "quantity",
        "verdict",
        "checks",
        "policy",
        "created_at",
    }
    assert migration_003_risk_decisions.VERSION == 3
    for table in (
        "scheduler_ticks",
        "research_cycle_records",
        "committee_cycle_evaluations",
        "cycle_performance_records",
        "self_improvement_reports",
    ):
        assert _table_exists(table), f"missing evidence table: {table}"

    # --- ledger records migrations 001 through 005 ---
    rows = _ledger_rows()
    assert [(row[0], row[1]) for row in rows] == [
        (1, "baseline schema"),
        (2, "additive column reconciliation"),
        (3, "risk decision audit log"),
        (4, "autonomous cycle evidence"),
        (5, "outcome tracking"),
    ]
    assert all(row[2] for row in rows)

    # --- second run is idempotent ---
    summary = run_migrations()
    assert summary["applied_now"] == []
    assert summary["already_applied"] == [1, 2, 3, 4, 5]
    assert _ledger_rows() == rows

    # --- CLI is a clean up-to-date run ---
    assert main() == 0

    migrated_schema = _schema_dump()
    assert set(migrated_schema) == set(migration_001_baseline.TABLES)
    # Remember the fresh column shapes so the legacy-upgrade section can
    # prove an upgraded old database converges on the same shape.
    fresh_columns = {
        table: _column_names(table)
        for table in migration_002_additive_columns.COLUMNS
    }
finally:
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(fresh_path)
    for candidate in (fresh_path, f"{fresh_path}-wal", f"{fresh_path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


# --- an existing database (built by setup_database, with data) is stamped
#     without data loss, and its schema matches the migrated schema ---
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    existing_path = database_file.name

try:
    connection.DATABASE_PATH = existing_path
    connection._wal_initialized_paths.discard(existing_path)

    setup_database()  # legacy path builds the schema with no ledger
    db = get_connection()
    db.execute(
        "INSERT INTO atlas_runs (run_time, market_status, average_rsi, "
        "average_volatility) VALUES ('2026-07-04T10:00:00', 'OPEN', 55.0, 1.2)"
    )
    db.execute(
        "INSERT INTO recommendations (run_id, ticker, action, confidence) "
        "VALUES (1, 'AAPL', 'BUY', 80)"
    )
    db.commit()
    db.close()
    legacy_schema = _schema_dump()

    assert not _table_exists(LEDGER_TABLE)
    summary = run_migrations()
    assert [item["version"] for item in summary["applied_now"]] == [1, 2, 3, 4, 5]
    assert summary["database_version"] == 5
    assert _table_exists("risk_decisions")
    assert _table_exists("scheduler_ticks")

    # --- data preserved exactly ---
    db = get_connection()
    try:
        run_row = db.execute(
            "SELECT run_time, market_status, average_rsi, average_volatility "
            "FROM atlas_runs"
        ).fetchone()
        recommendation_row = db.execute(
            "SELECT run_id, ticker, action, confidence FROM recommendations"
        ).fetchone()
    finally:
        db.close()
    assert run_row == ("2026-07-04T10:00:00", "OPEN", 55.0, 1.2)
    assert recommendation_row == (1, "AAPL", "BUY", 80)

    # --- schema untouched by stamping, and identical to setup_database's ---
    assert _schema_dump() == legacy_schema
    assert legacy_schema == migrated_schema
finally:
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(existing_path)
    for candidate in (
        existing_path,
        f"{existing_path}-wal",
        f"{existing_path}-shm",
    ):
        if os.path.exists(candidate):
            os.remove(candidate)


# --- a legacy database missing newer columns is upgraded additively:
#     migration 002 adds only the missing columns, preserving rows ---
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    legacy_path = database_file.name

try:
    connection.DATABASE_PATH = legacy_path
    connection._wal_initialized_paths.discard(legacy_path)

    # Old-shape tables from before the additive columns existed.
    db = get_connection()
    db.execute(
        """
        CREATE TABLE recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            ticker TEXT,
            action TEXT,
            confidence INTEGER,
            reasons TEXT,
            risks TEXT,
            score INTEGER
        )
        """
    )
    # Realistic legacy shapes: the original CREATE TABLE columns, minus only
    # the columns that were introduced later via ALTER reconciliation.
    db.execute(
        """
        CREATE TABLE research_experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT UNIQUE,
            title TEXT,
            description TEXT,
            experiment_date TEXT,
            dataset TEXT,
            tickers TEXT,
            provider_configuration TEXT,
            forecast_provider TEXT,
            news_provider TEXT,
            fundamental_provider TEXT,
            validation_window INTEGER,
            benchmark_snapshot TEXT,
            status TEXT,
            notes TEXT
        )
        """
    )
    db.execute(
        """
        CREATE TABLE case_studies (
            case_id TEXT PRIMARY KEY,
            ticker TEXT,
            recommendation TEXT,
            market_regime TEXT,
            evidence TEXT,
            committee TEXT,
            executive_review TEXT,
            knowledge_score REAL,
            stability_score REAL,
            outcome TEXT,
            return_value REAL,
            holding_period INTEGER,
            validation TEXT,
            benchmark TEXT,
            hypotheses TEXT,
            counterfactuals TEXT,
            lessons_learned TEXT,
            case_date TEXT
        )
        """
    )
    db.execute(
        "INSERT INTO recommendations (run_id, ticker, action, confidence, "
        "reasons, risks, score) VALUES (7, 'MSFT', 'HOLD', 64, 'r', 'k', 55)"
    )
    db.execute(
        "INSERT INTO research_experiments (experiment_id, title) "
        "VALUES ('exp-1', 'legacy experiment')"
    )
    db.execute(
        "INSERT INTO case_studies (case_id, ticker) VALUES ('case-1', 'AAPL')"
    )
    db.commit()
    db.close()

    assert "overall_score" not in _column_names("recommendations")
    assert "related_discoveries" not in _column_names("research_experiments")
    assert "catalysts" not in _column_names("case_studies")

    summary = run_migrations()
    assert [item["version"] for item in summary["applied_now"]] == [1, 2, 3, 4, 5]

    # --- upgraded legacy shape converges on the fresh migrated shape ---
    for table, expected in fresh_columns.items():
        assert _column_names(table) == expected, f"column mismatch: {table}"

    # --- existing rows preserved; new columns backfill as NULL ---
    db = get_connection()
    try:
        recommendation_row = db.execute(
            "SELECT run_id, ticker, action, confidence, reasons, risks, "
            "score, overall_score, research_memory_report FROM recommendations"
        ).fetchone()
        experiment_row = db.execute(
            "SELECT experiment_id, title, related_discoveries "
            "FROM research_experiments"
        ).fetchone()
        case_row = db.execute(
            "SELECT case_id, ticker, catalysts, probability_report "
            "FROM case_studies"
        ).fetchone()
    finally:
        db.close()
    assert recommendation_row == (7, "MSFT", "HOLD", 64, "r", "k", 55, None, None)
    assert experiment_row == ("exp-1", "legacy experiment", None)
    assert case_row == ("case-1", "AAPL", None, None)

    # --- ledger records all migrations; second run is idempotent ---
    assert [(row[0], row[1]) for row in _ledger_rows()] == [
        (1, "baseline schema"),
        (2, "additive column reconciliation"),
        (3, "risk decision audit log"),
        (4, "autonomous cycle evidence"),
        (5, "outcome tracking"),
    ]
    summary = run_migrations()
    assert summary["applied_now"] == []
    assert summary["database_version"] == 5
finally:
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(legacy_path)
    for candidate in (legacy_path, f"{legacy_path}-wal", f"{legacy_path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


print("Migration framework and baseline migration tests passed.")
