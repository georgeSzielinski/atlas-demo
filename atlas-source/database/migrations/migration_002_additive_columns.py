"""Migration 002: additive column reconciliation for legacy databases.

Databases created before some columns existed have older table shapes than
migration 001 builds on a fresh database (CREATE TABLE IF NOT EXISTS cannot
add columns to an existing table). This migration moves setup_database()'s
additive ALTER TABLE reconciliation, verbatim, into a versioned migration.

It uses PRAGMA table_info introspection to add only genuinely missing
columns -- no exception swallowing. Purely additive and idempotent: existing
columns and rows are never touched, and on a database built fresh by
migration 001 it is a no-op.

Runs inside a transaction owned by the migration runner; it must not commit.
"""

VERSION = 2
NAME = "additive column reconciliation"

# table name -> column definitions that may be missing on legacy databases.
COLUMNS = {
    "recommendations": [
        "technical_score INTEGER",
        "fundamental_score INTEGER",
        "portfolio_score INTEGER",
        "risk_score INTEGER",
        "forecast_score INTEGER",
        "forecast_direction TEXT",
        "forecast_confidence INTEGER",
        "expected_change REAL",
        "overall_score INTEGER",
        "rating TEXT",
        "news_sentiment TEXT",
        "news_confidence INTEGER",
        "headline_count INTEGER",
        "news_summary TEXT",
        "signal_quality_score INTEGER",
        "signal_label TEXT",
        "false_positive_warnings TEXT",
        "evidence_breakdown TEXT",
        "confidence_metadata TEXT",
        "validation_status TEXT",
        "overall_conviction REAL",
        "bull_case TEXT",
        "bear_case TEXT",
        "neutral_case TEXT",
        "strongest_positive_factor TEXT",
        "strongest_negative_factor TEXT",
        "conflicting_signals TEXT",
        "missing_inputs TEXT",
        "fusion_summary TEXT",
        "committee_members TEXT",
        "committee_bull_case TEXT",
        "committee_bear_case TEXT",
        "committee_neutral_case TEXT",
        "committee_agreement REAL",
        "bullish_members TEXT",
        "bearish_members TEXT",
        "neutral_members TEXT",
        "strongest_bull_argument TEXT",
        "strongest_bear_argument TEXT",
        "main_disagreement TEXT",
        "final_committee_summary TEXT",
        "top_positive_factors TEXT",
        "top_negative_factors TEXT",
        "missing_evidence TEXT",
        "suggested_follow_up_research TEXT",
        "confidence_explanation TEXT",
        "evidence_summary TEXT",
        "assumptions TEXT",
        "strongest_assumption TEXT",
        "weakest_assumption TEXT",
        "counterfactuals TEXT",
        "recommendation_flip_conditions TEXT",
        "confidence_drivers TEXT",
        "executive_review TEXT",
        "executive_status TEXT",
        "executive_confidence INTEGER",
        "executive_summary TEXT",
        "executive_warnings TEXT",
        "executive_strengths TEXT",
        "executive_weaknesses TEXT",
        "required_follow_up_research TEXT",
        "stability_score INTEGER",
        "stability_level TEXT",
        "most_sensitive_factor TEXT",
        "stability_explanation TEXT",
        "knowledge_score INTEGER",
        "knowledge_level TEXT",
        "knowledge_explanation TEXT",
        "research_memory_report TEXT",
    ],
    "research_experiments": [
        "related_discoveries TEXT",
    ],
    "case_studies": [
        "catalysts TEXT",
        "probability_report TEXT",
    ],
}


def apply(connection):
    for table, definitions in COLUMNS.items():
        existing_columns = {
            row[1]
            for row in connection.execute(f"PRAGMA table_info({table})")
        }
        for definition in definitions:
            column_name = definition.split()[0]
            if column_name not in existing_columns:
                connection.execute(
                    f"ALTER TABLE {table} ADD COLUMN {definition}"
                )
