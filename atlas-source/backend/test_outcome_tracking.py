"""Tests for the outcome-tracking foundation (Sprint 1A): migration 005 and the
repository read/write functions.

Deterministic and offline, against throwaway temporary databases (never
database/atlas.db). Covers migration 005 on a fresh database, upgrading a
version-4 database, idempotence through the normal migrator, all new columns and
indexes, preservation of existing rows, legacy vs multi-horizon validation
writes, retry/idempotency, uniqueness (incl. SQLite NULL semantics), the
defensive pre-index integrity guard, bounded reads, pending-evaluation
selection, and narrow paper-order linkage that never touches order state.
"""

import os
import tempfile
from contextlib import contextmanager

import database.connection as connection
from database.connection import get_connection
from database.migrator import run_migrations
from database.migrations import MIGRATIONS
from database.migrations import migration_005_outcome_tracking as m005
from database import repository


EXPECTED_COLUMNS = {
    "recommendations": {
        "created_at", "entry_at", "entry_price", "entry_price_source",
        "entry_validated", "entry_fallback_used", "entry_status", "market_regime",
        "sector", "expected_horizon_days", "outcome_state", "outcome_schema_version",
    },
    "recommendation_validations": {
        "horizon_days", "cycle_id", "paper_order_id", "entry_price_source",
        "entry_validated", "eval_price_source", "eval_validated",
        "eval_fallback_used", "evaluation_source", "schema_version", "deferred_reason",
    },
    "paper_fund_orders": {"recommendation_id"},
    "committee_cycle_evaluations": {"schema_version"},
}

EXPECTED_INDEXES = {
    "idx_recommendations_ticker_run",
    "idx_recval_ticker",
    "idx_recval_rec_horizon_source",
    "idx_pf_orders_recommendation",
}


@contextmanager
def temp_database():
    original = connection.DATABASE_PATH
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as handle:
        path = handle.name
    connection.DATABASE_PATH = path
    connection._wal_initialized_paths.discard(path)
    try:
        yield path
    finally:
        connection.DATABASE_PATH = original
        connection._wal_initialized_paths.discard(path)
        for candidate in (path, f"{path}-wal", f"{path}-shm"):
            if os.path.exists(candidate):
                os.remove(candidate)


def _columns(table):
    db = get_connection()
    try:
        return {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
    finally:
        db.close()


def _index_names():
    db = get_connection()
    try:
        return {
            row[0]
            for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
        }
    finally:
        db.close()


def _execute(sql, params=()):
    db = get_connection()
    try:
        db.execute(sql, params)
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Migration 005: fresh database builds columns + indexes; idempotent re-run.
# ---------------------------------------------------------------------------
with temp_database():
    summary = run_migrations()
    assert summary["database_version"] == 5, summary
    for table, expected in EXPECTED_COLUMNS.items():
        assert expected.issubset(_columns(table)), (table, expected - _columns(table))
    assert EXPECTED_INDEXES.issubset(_index_names()), EXPECTED_INDEXES - _index_names()

    # Idempotent through the normal migrator.
    again = run_migrations()
    assert again["applied_now"] == []
    assert again["database_version"] == 5


# ---------------------------------------------------------------------------
# Migration 005 upgrades a version-4 database additively, preserving rows.
# ---------------------------------------------------------------------------
with temp_database():
    run_migrations(migrations=MIGRATIONS[:4])  # build a real v4 database
    assert "entry_at" not in _columns("recommendations")
    assert "horizon_days" not in _columns("recommendation_validations")
    assert "recommendation_id" not in _columns("paper_fund_orders")

    # A pre-1A validation row (classic columns only) must survive untouched.
    _execute(
        "INSERT INTO recommendation_validations "
        "(recommendation_id, ticker, recommendation, status, percentage_return, success) "
        "VALUES (1, 'AAPL', 'BUY', 'Succeeded', 5.0, 1)"
    )

    upgrade = run_migrations()  # only 005 pending
    assert [item["version"] for item in upgrade["applied_now"]] == [5]
    for table, expected in EXPECTED_COLUMNS.items():
        assert expected.issubset(_columns(table)), table
    assert EXPECTED_INDEXES.issubset(_index_names())

    db = get_connection()
    try:
        row = db.execute(
            "SELECT recommendation_id, ticker, status, percentage_return, success, "
            "horizon_days, evaluation_source FROM recommendation_validations "
            "WHERE recommendation_id = 1"
        ).fetchone()
    finally:
        db.close()
    # Existing values preserved; new columns backfill as NULL.
    assert row == (1, "AAPL", "Succeeded", 5.0, 1, None, None), row


# ---------------------------------------------------------------------------
# Defensive guard: the UNIQUE index is refused if existing rows would violate it.
# ---------------------------------------------------------------------------
with temp_database():
    run_migrations(migrations=MIGRATIONS[:4])
    db = get_connection()
    try:
        db.execute("ALTER TABLE recommendation_validations ADD COLUMN horizon_days INTEGER")
        db.execute("ALTER TABLE recommendation_validations ADD COLUMN evaluation_source TEXT")
        db.execute(
            "INSERT INTO recommendation_validations "
            "(recommendation_id, horizon_days, evaluation_source, status) "
            "VALUES (1, 7, 'paper', 'Pending')"
        )
        db.execute(
            "INSERT INTO recommendation_validations "
            "(recommendation_id, horizon_days, evaluation_source, status) "
            "VALUES (1, 7, 'paper', 'Pending')"
        )
        db.commit()
        raised = False
        try:
            m005.apply(db)  # must detect the duplicate and refuse the unique index
        except RuntimeError as error:
            raised = True
            assert "UNIQUE" in str(error)
        assert raised, "migration 005 did not guard against a violating unique key"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Repository: legacy write, multi-horizon writes, idempotency, uniqueness.
# ---------------------------------------------------------------------------
with temp_database():
    run_migrations()

    # Seed recommendations so validation-status propagation has a target.
    for rec_id, ticker in ((1, "AAPL"), (2, "MSFT"), (3, "TSLA")):
        _execute(
            "INSERT INTO recommendations (id, run_id, ticker, action) VALUES (?, 1, ?, 'BUY')",
            (rec_id, ticker),
        )

    # --- legacy (unkeyed) write: inserts, defaults new fields, updates status ---
    result = repository.save_validation_result(
        {
            "recommendation_id": 1,
            "ticker": "AAPL",
            "recommendation": "BUY",
            "status": "Succeeded",
            "success": True,
            "percentage_return": 5.0,
        }
    )
    assert result["written"] is True and result["action"] == "inserted"
    aapl = repository.get_outcomes(ticker="AAPL")
    assert len(aapl) == 1
    assert aapl[0]["status"] == "Succeeded"
    assert aapl[0]["horizon_days"] is None  # legacy unkeyed
    assert aapl[0]["schema_version"] == 1  # stamped current format version
    db = get_connection()
    try:
        status = db.execute(
            "SELECT validation_status FROM recommendations WHERE id = 1"
        ).fetchone()[0]
    finally:
        db.close()
    assert status == "Succeeded"  # original validation-status update preserved

    # --- multi-horizon keyed writes for one recommendation ---
    for horizon in (7, 30):
        repository.save_validation_result(
            {
                "recommendation_id": 2,
                "ticker": "MSFT",
                "recommendation": "HOLD",
                "status": "Pending",
                "horizon_days": horizon,
                "evaluation_source": "paper",
            }
        )
    msft = repository.get_outcomes_for_recommendation(2)
    assert len(msft) == 2
    assert {row["horizon_days"] for row in msft} == {7, 30}

    # --- retry completes a pending row in place (no duplicate) ---
    retry = repository.save_validation_result(
        {
            "recommendation_id": 2,
            "ticker": "MSFT",
            "recommendation": "HOLD",
            "status": "Succeeded",
            "percentage_return": 3.0,
            "horizon_days": 7,
            "evaluation_source": "paper",
        }
    )
    assert retry["action"] == "updated"
    horizon7 = [r for r in repository.get_outcomes_for_recommendation(2) if r["horizon_days"] == 7]
    assert len(horizon7) == 1 and horizon7[0]["status"] == "Succeeded"

    # --- a completed outcome is never overwritten ---
    blocked = repository.save_validation_result(
        {
            "recommendation_id": 2,
            "ticker": "MSFT",
            "recommendation": "HOLD",
            "status": "Failed",
            "horizon_days": 7,
            "evaluation_source": "paper",
        }
    )
    assert blocked["written"] is False and blocked["action"] == "skipped_completed"
    horizon7_after = [r for r in repository.get_outcomes_for_recommendation(2) if r["horizon_days"] == 7]
    assert horizon7_after[0]["status"] == "Succeeded"  # unchanged

    # --- SQLite NULL semantics: unkeyed rows never collide ---
    repository.save_validation_result({"recommendation_id": 3, "ticker": "TSLA", "recommendation": "BUY", "status": "Succeeded"})
    repository.save_validation_result({"recommendation_id": 3, "ticker": "TSLA", "recommendation": "BUY", "status": "Failed"})
    assert len(repository.get_outcomes(ticker="TSLA")) == 2  # NULL keys are distinct

    # --- the UNIQUE index enforces on fully non-null keys ---
    _execute(
        "INSERT INTO recommendation_validations (recommendation_id, horizon_days, evaluation_source, status) "
        "VALUES (99, 7, 'paper', 'Pending')"
    )
    raised = False
    try:
        _execute(
            "INSERT INTO recommendation_validations (recommendation_id, horizon_days, evaluation_source, status) "
            "VALUES (99, 7, 'paper', 'Pending')"
        )
    except Exception as error:  # sqlite3.IntegrityError
        raised = True
        assert "unique" in str(error).lower()
    assert raised

    # --- bounded, newest-first reads ---
    assert len(repository.get_outcomes(limit=1)) == 1
    everything = repository.get_outcomes(limit=10_000)  # clamped to the safe max
    assert len(everything) <= repository.OUTCOME_READ_MAX_LIMIT
    ids = [row["id"] for row in everything]
    assert ids == sorted(ids, reverse=True)  # newest first
    assert repository.get_outcomes(horizon=30, evaluation_source="paper")[0]["horizon_days"] == 30


# ---------------------------------------------------------------------------
# Repository: pending-evaluation selection (pure read, no price fetch).
# ---------------------------------------------------------------------------
with temp_database():
    run_migrations()
    # Recommendation WITH a past entry_at is a candidate; one WITHOUT is not.
    _execute(
        "INSERT INTO recommendations (id, run_id, ticker, action, entry_at, entry_price) "
        "VALUES (500, 1, 'PEND', 'BUY', '2020-01-01T00:00:00', 100.0)"
    )
    _execute(
        "INSERT INTO recommendations (id, run_id, ticker, action) VALUES (501, 1, 'NOEN', 'HOLD')"
    )

    pending = repository.get_pending_evaluations("2020-01-15T00:00:00", [7, 30], evaluation_source="paper")
    due = sorted(p["horizon_days"] for p in pending if p["recommendation_id"] == 500)
    assert due == [7]  # 14 days elapsed: 7 due, 30 not
    assert all(p["recommendation_id"] != 501 for p in pending)  # no entry_at -> never pending

    # A completed outcome removes that (recommendation, horizon) from pending.
    repository.save_validation_result(
        {"recommendation_id": 500, "ticker": "PEND", "recommendation": "BUY",
         "status": "Succeeded", "horizon_days": 7, "evaluation_source": "paper"}
    )
    pending_after = repository.get_pending_evaluations("2020-01-15T00:00:00", [7, 30], evaluation_source="paper")
    assert not any(p["recommendation_id"] == 500 for p in pending_after)


# ---------------------------------------------------------------------------
# Repository: narrow paper-order linkage never touches order state.
# ---------------------------------------------------------------------------
with temp_database():
    run_migrations()
    _execute("INSERT INTO recommendations (id, run_id, ticker, action) VALUES (700, 1, 'AAPL', 'BUY')")
    repository.save_paper_fund_order(
        {
            "order_id": "o-1",
            "cycle_id": "c1",
            "ticker": "AAPL",
            "side": "BUY",
            "quantity": 10,
            "status": "FILLED_SIMULATED",
            "fill_price": 150.0,
            "validated": True,
            "simulated": True,
        }
    )

    linked = repository.link_order_to_recommendation("o-1", 700)
    assert linked == {"linked": True, "order_id": "o-1", "recommendation_id": 700}

    db = get_connection()
    try:
        row = db.execute(
            "SELECT recommendation_id, status, quantity, fill_price, side "
            "FROM paper_fund_orders WHERE order_id = 'o-1'"
        ).fetchone()
    finally:
        db.close()
    # Only recommendation_id changed; status/quantity/price/side untouched.
    assert row == (700, "FILLED_SIMULATED", 10, 150.0, "BUY"), row

    # Missing ids are reported clearly, not applied.
    assert repository.link_order_to_recommendation("missing", 700) == {
        "linked": False, "reason": "order_not_found", "order_id": "missing",
    }
    missing_rec = repository.link_order_to_recommendation("o-1", 999999)
    assert missing_rec["linked"] is False and missing_rec["reason"] == "recommendation_not_found"

    # The failed recommendation link left the order's link intact.
    db = get_connection()
    try:
        still = db.execute(
            "SELECT recommendation_id FROM paper_fund_orders WHERE order_id = 'o-1'"
        ).fetchone()[0]
    finally:
        db.close()
    assert still == 700


print("Outcome tracking foundation tests passed.")
