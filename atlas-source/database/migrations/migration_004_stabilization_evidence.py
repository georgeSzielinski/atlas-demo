"""Migration 004: autonomous-cycle evidence persistence.

Adds the append-only tables that make the autonomous loop observable and its
learning evidence durable:

- ``scheduler_ticks``: one row per scheduler tick (ran, skipped, or errored)
  so every skipped cycle records WHY, surviving process restarts.
- ``research_cycle_records``: one row per research-cycle tick that did work,
  with per-stage status, reason, and duration.
- ``committee_cycle_evaluations``: the committee verdicts produced for each
  autonomous research generation run.
- ``cycle_performance_records``: the per-cycle read-only performance snapshot
  computed from live paper-fund evidence.
- ``self_improvement_reports``: persisted Self-Improvement findings —
  advisory research evidence only; nothing reads them to change trading.

All tables are additive and idempotent. Existing data is never touched.

Runs inside a transaction owned by the migration runner; it must not commit.
"""

VERSION = 4
NAME = "autonomous cycle evidence"


def apply(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS scheduler_ticks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            at TEXT,
            status TEXT,
            reason TEXT,
            stages TEXT,
            duration_seconds REAL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS research_cycle_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT,
            generated_at TEXT,
            status TEXT,
            reason TEXT,
            stages TEXT,
            fund_cycle_id TEXT,
            policy TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS committee_cycle_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT,
            run_id INTEGER,
            evaluated_at TEXT,
            evaluations TEXT,
            duration_seconds REAL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS cycle_performance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT,
            as_of TEXT,
            report TEXT,
            policy TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS self_improvement_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT,
            generated_at TEXT,
            status TEXT,
            headline TEXT,
            findings TEXT,
            opportunities TEXT,
            not_evaluated TEXT,
            source_counts TEXT,
            policy TEXT
        )
        """
    )
