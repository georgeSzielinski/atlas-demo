"""Migration 003: persist risk management decisions.

Adds an append-only audit table for deterministic risk management decisions.
The table is additive and idempotent. Existing data is never touched.

Runs inside a transaction owned by the migration runner; it must not commit.
"""

VERSION = 3
NAME = "risk decision audit log"


def apply(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_decisions (
            decision_id TEXT PRIMARY KEY,
            cycle_id TEXT,
            run_id INTEGER,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity REAL NOT NULL,
            verdict TEXT NOT NULL,
            checks TEXT NOT NULL,
            policy TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
