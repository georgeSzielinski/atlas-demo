"""Migration 005: outcome-tracking foundation (schema only).

Additive, backward-compatible columns + indexes that let a FUTURE outcome
evaluator record how each recommendation actually performed. This migration
changes no runtime behavior and populates no data: every new column is nullable,
so existing rows read as honestly unknown/null.

Additions:
- ``recommendations``: an unambiguous per-row timestamp, entry-context and
  provider-lineage fields, a planned horizon, and outcome bookkeeping.
- ``recommendation_validations``: multi-horizon keying, paper-order linkage,
  entry/eval provider lineage, evaluation source, schema version, and a deferred
  reason -- extending the existing (currently dormant) outcome table.
- ``paper_fund_orders``: a nullable ``recommendation_id`` link.
- ``committee_cycle_evaluations``: a nullable ``schema_version``.

``OUTCOME_COLUMNS`` / ``OUTCOME_INDEXES`` are the single source of truth for the
delta; ``database.setup.setup_database`` reuses them so a fresh setup build and a
migrated database converge to the identical schema.

The UNIQUE index on ``(recommendation_id, horizon_days, evaluation_source)`` lets
a future evaluator write one outcome per recommendation/horizon/source
idempotently. SQLite treats NULLs in a unique index as DISTINCT, so pre-existing
rows (whose new key columns are all NULL) can never violate it; live outcome
rows must always supply ``horizon_days`` AND ``evaluation_source`` for the
guarantee to bind. The composite index also serves ``recommendation_id`` lookups
via its leftmost prefix, so no separate single-column index is added.

Idempotent: columns are added only when missing (``PRAGMA table_info``) and every
index uses ``CREATE ... IF NOT EXISTS``. Runs inside the migration runner's
transaction; it must not commit.
"""

VERSION = 5
NAME = "outcome tracking"

# table -> additive nullable column definitions (single source of truth).
OUTCOME_COLUMNS = {
    "recommendations": [
        "created_at TEXT",
        "entry_at TEXT",
        "entry_price REAL",
        "entry_price_source TEXT",
        "entry_validated INTEGER",
        "entry_fallback_used INTEGER",
        "entry_status TEXT",
        "market_regime TEXT",
        "sector TEXT",
        "expected_horizon_days INTEGER",
        "outcome_state TEXT",
        "outcome_schema_version INTEGER",
    ],
    "recommendation_validations": [
        "horizon_days INTEGER",
        "cycle_id TEXT",
        "paper_order_id TEXT",
        "entry_price_source TEXT",
        "entry_validated INTEGER",
        "eval_price_source TEXT",
        "eval_validated INTEGER",
        "eval_fallback_used INTEGER",
        "evaluation_source TEXT",
        "schema_version INTEGER",
        "deferred_reason TEXT",
    ],
    "paper_fund_orders": [
        "recommendation_id INTEGER",
    ],
    "committee_cycle_evaluations": [
        "schema_version INTEGER",
    ],
}

# (name, sql) pairs, created with IF NOT EXISTS.
OUTCOME_INDEXES = [
    (
        "idx_recommendations_ticker_run",
        "CREATE INDEX IF NOT EXISTS idx_recommendations_ticker_run "
        "ON recommendations (ticker, run_id)",
    ),
    (
        "idx_recval_ticker",
        "CREATE INDEX IF NOT EXISTS idx_recval_ticker "
        "ON recommendation_validations (ticker)",
    ),
    (
        "idx_recval_rec_horizon_source",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_recval_rec_horizon_source "
        "ON recommendation_validations (recommendation_id, horizon_days, evaluation_source)",
    ),
    (
        "idx_pf_orders_recommendation",
        "CREATE INDEX IF NOT EXISTS idx_pf_orders_recommendation "
        "ON paper_fund_orders (recommendation_id)",
    ),
]


def _existing_columns(connection, table):
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def apply(connection):
    # 1) Additive nullable columns, only where missing.
    for table, definitions in OUTCOME_COLUMNS.items():
        existing = _existing_columns(connection, table)
        for definition in definitions:
            column = definition.split()[0]
            if column not in existing:
                connection.execute(
                    f"ALTER TABLE {table} ADD COLUMN {definition}"
                )

    # 2) Prove the UNIQUE index is safe before creating it. Only fully non-null
    #    keys can collide, and every pre-1A row's new key columns are NULL, so a
    #    violation is impossible here -- but if one somehow exists (e.g. hand
    #    backfilled), fail loudly and roll back rather than silently drop the
    #    idempotency guarantee. No data is read destructively or rewritten.
    duplicate = connection.execute(
        """
        SELECT recommendation_id, horizon_days, evaluation_source, COUNT(*) AS c
        FROM recommendation_validations
        WHERE recommendation_id IS NOT NULL
          AND horizon_days IS NOT NULL
          AND evaluation_source IS NOT NULL
        GROUP BY recommendation_id, horizon_days, evaluation_source
        HAVING c > 1
        LIMIT 1
        """
    ).fetchone()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot create the UNIQUE outcome index: recommendation_validations "
            "already contains rows that violate (recommendation_id, horizon_days, "
            f"evaluation_source): {tuple(duplicate[:3])}."
        )

    # 3) Indexes (idempotent).
    for _name, sql in OUTCOME_INDEXES:
        connection.execute(sql)
