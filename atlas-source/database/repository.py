import json
from datetime import datetime

from database.connection import get_connection
from engines.paper_trading_engine import PaperTradingEngine


def save_dashboard_run(dashboard):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO atlas_runs (
            run_time,
            market_status,
            average_rsi,
            average_volatility
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            datetime.now().isoformat(),
            dashboard.market_status,
            dashboard.average_rsi,
            dashboard.average_volatility,
        )
    )

    run_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return run_id


def _apply_entry_context(cursor, recommendation_id, ticker, entry_contexts):
    """UPDATE one just-inserted recommendation row with its entry context.

    Additive and deterministic: touches ONLY the entry-context/outcome columns,
    never the recommendation action/confidence/scores/committee fields. A ticker
    with no context is recorded as an honest DEFERRED row with null lineage.
    """
    context = entry_contexts.get(ticker) or entry_contexts.get(str(ticker).upper()) or {}
    cursor.execute(
        """
        UPDATE recommendations SET
            created_at = ?,
            entry_at = ?,
            entry_price = ?,
            entry_price_source = ?,
            entry_validated = ?,
            entry_fallback_used = ?,
            entry_status = ?,
            market_regime = ?,
            sector = ?,
            expected_horizon_days = ?,
            outcome_state = ?,
            outcome_schema_version = ?
        WHERE id = ?
        """,
        (
            context.get("created_at"),
            context.get("entry_at"),
            context.get("entry_price"),
            context.get("entry_price_source"),
            _bool_to_int(context.get("entry_validated")),
            _bool_to_int(context.get("entry_fallback_used")),
            context.get("entry_status", "DEFERRED"),
            context.get("market_regime"),
            context.get("sector"),
            context.get("expected_horizon_days"),
            context.get("outcome_state", "DEFERRED"),
            context.get("outcome_schema_version", 1),
            recommendation_id,
        ),
    )


def save_recommendations(run_id, recommendations, entry_contexts=None):
    """Persist recommendation rows for a run.

    Backward compatible: with entry_contexts=None (every existing caller) behavior
    is unchanged and the new entry-context columns stay NULL. When entry_contexts
    is provided (autonomous generation, Sprint 1B.1) each row additionally gets
    its deterministic persistence timestamp (created_at) and captured entry
    context from the same call. Returns the inserted recommendation ids in
    input order, so callers never need a later ticker-based identity lookup.
    """
    connection = get_connection()
    cursor = connection.cursor()

    recommendation_ids = []

    for recommendation in recommendations:
        cursor.execute(
            """
            INSERT INTO recommendations (
                run_id,
                ticker,
                action,
                confidence,
                reasons,
                risks,
                score,
                technical_score,
                fundamental_score,
                portfolio_score,
                risk_score,
                forecast_score,
                forecast_direction,
                forecast_confidence,
                expected_change,
                overall_score,
                rating,
                news_sentiment,
                news_confidence,
                headline_count,
                news_summary,
                signal_quality_score,
                signal_label,
                false_positive_warnings,
                evidence_breakdown,
                confidence_metadata,
                validation_status,
                overall_conviction,
                bull_case,
                bear_case,
                neutral_case,
                strongest_positive_factor,
                strongest_negative_factor,
                conflicting_signals,
                missing_inputs,
                fusion_summary,
                committee_members,
                committee_bull_case,
                committee_bear_case,
                committee_neutral_case,
                committee_agreement,
                bullish_members,
                bearish_members,
                neutral_members,
                strongest_bull_argument,
                strongest_bear_argument,
                main_disagreement,
                final_committee_summary,
                top_positive_factors,
                top_negative_factors,
                missing_evidence,
                suggested_follow_up_research,
                confidence_explanation,
                evidence_summary,
                assumptions,
                strongest_assumption,
                weakest_assumption,
                counterfactuals,
                recommendation_flip_conditions,
                confidence_drivers,
                executive_review,
                executive_status,
                executive_confidence,
                executive_summary,
                executive_warnings,
                executive_strengths,
                executive_weaknesses,
                required_follow_up_research,
                stability_score,
                stability_level,
                most_sensitive_factor,
                stability_explanation,
                knowledge_score,
                knowledge_level,
                knowledge_explanation,
                research_memory_report
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                recommendation.ticker,
                recommendation.action,
                recommendation.confidence,
                json.dumps(recommendation.reasons),
                json.dumps(recommendation.risks),
                recommendation.score,
                recommendation.technical_score,
                recommendation.fundamental_score,
                recommendation.portfolio_score,
                recommendation.risk_score,
                recommendation.forecast_score,
                recommendation.forecast_direction,
                recommendation.forecast_confidence,
                recommendation.expected_change,
                recommendation.overall_score,
                recommendation.rating,
                recommendation.news_sentiment,
                recommendation.news_confidence,
                recommendation.headline_count,
                recommendation.news_summary,
                recommendation.signal_quality_score,
                recommendation.signal_label,
                json.dumps(recommendation.false_positive_warnings),
                json.dumps(recommendation.evidence_breakdown),
                json.dumps(recommendation.confidence_metadata),
                recommendation.validation_status,
                recommendation.overall_conviction,
                json.dumps(recommendation.fusion.get("bull_case", [])),
                json.dumps(recommendation.fusion.get("bear_case", [])),
                json.dumps(recommendation.fusion.get("neutral_case", [])),
                json.dumps(
                    recommendation.fusion.get(
                        "strongest_positive_factor",
                        {},
                    )
                ),
                json.dumps(
                    recommendation.fusion.get(
                        "strongest_negative_factor",
                        {},
                    )
                ),
                json.dumps(
                    recommendation.fusion.get("conflicting_signals", [])
                ),
                json.dumps(recommendation.fusion.get("missing_inputs", [])),
                recommendation.fusion_summary,
                json.dumps(recommendation.committee_members),
                json.dumps(recommendation.committee_bull_case),
                json.dumps(recommendation.committee_bear_case),
                json.dumps(recommendation.committee_neutral_case),
                recommendation.committee_agreement,
                json.dumps(recommendation.bullish_members),
                json.dumps(recommendation.bearish_members),
                json.dumps(recommendation.neutral_members),
                recommendation.strongest_bull_argument,
                recommendation.strongest_bear_argument,
                recommendation.main_disagreement,
                recommendation.final_committee_summary,
                json.dumps(recommendation.top_positive_factors),
                json.dumps(recommendation.top_negative_factors),
                json.dumps(recommendation.missing_evidence),
                json.dumps(recommendation.suggested_follow_up_research),
                recommendation.confidence_explanation,
                recommendation.evidence_summary,
                json.dumps(recommendation.assumptions),
                recommendation.strongest_assumption,
                recommendation.weakest_assumption,
                json.dumps(recommendation.counterfactuals),
                json.dumps(recommendation.recommendation_flip_conditions),
                json.dumps(recommendation.confidence_drivers),
                json.dumps(recommendation.executive_review),
                recommendation.executive_status,
                recommendation.executive_confidence,
                recommendation.executive_summary,
                json.dumps(recommendation.executive_warnings),
                json.dumps(recommendation.executive_strengths),
                json.dumps(recommendation.executive_weaknesses),
                json.dumps(recommendation.required_follow_up_research),
                recommendation.stability_score,
                recommendation.stability_level,
                recommendation.most_sensitive_factor,
                recommendation.stability_explanation,
                recommendation.knowledge_score,
                recommendation.knowledge_level,
                recommendation.knowledge_explanation,
                json.dumps(
                    getattr(recommendation, "research_memory_report", {})
                ),
            )
        )
        recommendation_id = cursor.lastrowid
        recommendation_ids.append(recommendation_id)

        if entry_contexts is not None:
            _apply_entry_context(
                cursor,
                recommendation_id,
                recommendation.ticker,
                entry_contexts,
            )

    connection.commit()
    connection.close()
    return recommendation_ids


def save_portfolio_snapshot(run_id, portfolio, risk_engine):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO portfolio_snapshots (
            run_id,
            cash,
            portfolio_value,
            position_count,
            risk_level,
            cash_percentage
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            portfolio.cash,
            portfolio.portfolio_value(),
            portfolio.position_count(),
            risk_engine.portfolio_risk(portfolio),
            risk_engine.cash_percentage(portfolio),
        )
    )

    connection.commit()
    connection.close()


def get_recent_runs(limit=5):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            run_time,
            market_status,
            average_rsi,
            average_volatility
        FROM atlas_runs
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = cursor.fetchall()
    connection.close()
    benchmark_summaries = get_latest_benchmark_results(limit=10)
    evidence_summaries = get_latest_evidence_benchmarks(limit=10)

    return [
        {
            "id": row[0],
            "run_time": row[1],
            "market_status": row[2],
            "average_rsi": row[3],
            "average_volatility": row[4],
            "benchmark_summaries": (
                benchmark_summaries + evidence_summaries
            ),
        }
        for row in rows
    ]


def get_intelligence_dashboard_summary():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            ticker,
            action,
            confidence,
            technical_score,
            fundamental_score,
            forecast_score,
            news_confidence,
            portfolio_score,
            risk_score,
            signal_quality_score,
            validation_status
        FROM recommendations
        ORDER BY id DESC
        """
    )

    rows = cursor.fetchall()
    connection.close()

    recommendations = [
        {
            "id": row[0],
            "ticker": row[1],
            "action": row[2],
            "confidence": row[3],
            "technical_score": row[4] or 0,
            "fundamental_score": row[5] or 0,
            "forecast_score": row[6] or 0,
            "news_confidence": row[7] or 0,
            "portfolio_score": row[8] or 0,
            "risk_score": row[9] or 0,
            "signal_quality_score": row[10] or 0,
            "validation_status": row[11] or "Pending",
        }
        for row in rows
    ]
    validation_results = get_validation_results_for_recommendations([
        recommendation["id"] for recommendation in recommendations
    ])

    return {
        "recommendation_metrics": _recommendation_metrics(
            recommendations,
            validation_results,
        ),
        "evidence_metrics": _evidence_metrics(recommendations),
        "latest_recommendation": _latest_recommendation(
            recommendations,
            validation_results,
        ),
    }


def get_latest_recommendation_for_ticker(ticker):
    """Read-only lookup of the NEWEST stored recommendation for one ticker.

    Selects exactly the deterministic signal columns the strategy/committee
    engines consume plus identifying metadata. Returns None when the ticker
    has no stored recommendation; missing signal values stay None so callers
    can report NOT_EVALUATED instead of scoring fabricated defaults.
    """
    symbol = str(ticker or "").strip().upper()
    if not symbol:
        return None

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT
            recommendations.id,
            recommendations.run_id,
            recommendations.ticker,
            recommendations.action,
            recommendations.confidence,
            recommendations.overall_conviction,
            recommendations.overall_score,
            recommendations.technical_score,
            recommendations.fundamental_score,
            recommendations.forecast_score,
            recommendations.news_confidence,
            recommendations.signal_quality_score,
            recommendations.committee_agreement,
            recommendations.stability_score,
            recommendations.knowledge_score,
            atlas_runs.run_time
        FROM recommendations
        LEFT JOIN atlas_runs ON atlas_runs.id = recommendations.run_id
        WHERE UPPER(recommendations.ticker) = ?
        ORDER BY recommendations.id DESC
        LIMIT 1
        """,
        (symbol,),
    )
    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "run_id": row[1],
        "ticker": row[2],
        "action": row[3],
        "confidence": row[4],
        "overall_conviction": row[5],
        "overall_score": row[6],
        "technical_score": row[7],
        "fundamental_score": row[8],
        "forecast_score": row[9],
        "news_confidence": row[10],
        "signal_quality_score": row[11],
        "committee_agreement": row[12],
        "stability_score": row[13],
        "knowledge_score": row[14],
        "run_time": row[15],
    }


def get_recommendations_for_run(run_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            run_id,
            ticker,
            action,
            confidence,
            reasons,
            risks,
            score,
            technical_score,
            fundamental_score,
            portfolio_score,
            risk_score,
            forecast_score,
            forecast_direction,
            forecast_confidence,
            expected_change,
            overall_score,
            rating,
            news_sentiment,
            news_confidence,
            headline_count,
            news_summary,
            signal_quality_score,
            signal_label,
            false_positive_warnings,
            evidence_breakdown,
            confidence_metadata,
            validation_status,
            overall_conviction,
            bull_case,
            bear_case,
            neutral_case,
            strongest_positive_factor,
            strongest_negative_factor,
            conflicting_signals,
            missing_inputs,
            fusion_summary,
            committee_members,
            committee_bull_case,
            committee_bear_case,
            committee_neutral_case,
            committee_agreement,
            bullish_members,
            bearish_members,
            neutral_members,
            strongest_bull_argument,
            strongest_bear_argument,
            main_disagreement,
            final_committee_summary,
            top_positive_factors,
            top_negative_factors,
            missing_evidence,
            suggested_follow_up_research,
            confidence_explanation,
            evidence_summary,
            assumptions,
            strongest_assumption,
            weakest_assumption,
            counterfactuals,
            recommendation_flip_conditions,
            confidence_drivers,
            executive_review,
            executive_status,
            executive_confidence,
            executive_summary,
            executive_warnings,
            executive_strengths,
            executive_weaknesses,
            required_follow_up_research,
            stability_score,
            stability_level,
            most_sensitive_factor,
            stability_explanation,
            knowledge_score,
            knowledge_level,
            knowledge_explanation,
            research_memory_report
        FROM recommendations
        WHERE run_id = ?
        ORDER BY confidence DESC
        """,
        (run_id,)
    )

    rows = cursor.fetchall()
    connection.close()

    recommendations = [
        {
            "id": row[0],
            "run_id": row[1],
            "ticker": row[2],
            "action": row[3],
            "confidence": row[4],
            "reasons": json.loads(row[5]),
            "risks": json.loads(row[6]),
            "score": row[7],
            "technical_score": row[8] or 0,
            "fundamental_score": row[9] or 0,
            "portfolio_score": row[10] or 0,
            "risk_score": row[11] or 0,
            "forecast_score": row[12] or 0,
            "forecast_direction": row[13] or "",
            "forecast_confidence": row[14] or 0,
            "expected_change": row[15] or 0.0,
            "overall_score": row[16] or 0,
            "rating": row[17] or "",
            "news_sentiment": row[18] or "",
            "news_confidence": row[19] or 0,
            "headline_count": row[20] or 0,
            "news_summary": row[21] or "",
            "signal_quality_score": row[22] or 0,
            "signal_label": row[23] or "",
            "false_positive_warnings": json.loads(row[24] or "[]"),
            "evidence_breakdown": json.loads(row[25] or "[]"),
            "confidence_metadata": json.loads(row[26] or "[]"),
            "validation_status": row[27] or "Pending",
            "overall_conviction": row[28] or 0,
            "bull_case": json.loads(row[29] or "[]"),
            "bear_case": json.loads(row[30] or "[]"),
            "neutral_case": json.loads(row[31] or "[]"),
            "strongest_positive_factor": json.loads(row[32] or "{}"),
            "strongest_negative_factor": json.loads(row[33] or "{}"),
            "conflicting_signals": json.loads(row[34] or "[]"),
            "missing_inputs": json.loads(row[35] or "[]"),
            "fusion_summary": row[36] or "",
            "committee_members": json.loads(row[37] or "[]"),
            "committee_bull_case": json.loads(row[38] or "[]"),
            "committee_bear_case": json.loads(row[39] or "[]"),
            "committee_neutral_case": json.loads(row[40] or "[]"),
            "committee_agreement": row[41] or 0,
            "bullish_members": json.loads(row[42] or "[]"),
            "bearish_members": json.loads(row[43] or "[]"),
            "neutral_members": json.loads(row[44] or "[]"),
            "strongest_bull_argument": row[45] or "",
            "strongest_bear_argument": row[46] or "",
            "main_disagreement": row[47] or "",
            "final_committee_summary": row[48] or "",
            "top_positive_factors": json.loads(row[49] or "[]"),
            "top_negative_factors": json.loads(row[50] or "[]"),
            "missing_evidence": json.loads(row[51] or "[]"),
            "suggested_follow_up_research": json.loads(row[52] or "[]"),
            "confidence_explanation": row[53] or "",
            "evidence_summary": row[54] or "",
            "assumptions": json.loads(row[55] or "[]"),
            "strongest_assumption": row[56] or "",
            "weakest_assumption": row[57] or "",
            "counterfactuals": json.loads(row[58] or "[]"),
            "recommendation_flip_conditions": json.loads(row[59] or "[]"),
            "confidence_drivers": json.loads(row[60] or "[]"),
            "executive_review": json.loads(row[61] or "{}"),
            "executive_status": row[62] or "",
            "executive_confidence": row[63] or 0,
            "executive_summary": row[64] or "",
            "executive_warnings": json.loads(row[65] or "[]"),
            "executive_strengths": json.loads(row[66] or "[]"),
            "executive_weaknesses": json.loads(row[67] or "[]"),
            "required_follow_up_research": json.loads(row[68] or "[]"),
            "stability_score": row[69] or 0,
            "stability_level": row[70] or "",
            "most_sensitive_factor": row[71] or "",
            "stability_explanation": row[72] or "",
            "knowledge_score": row[73] or 0,
            "knowledge_level": row[74] or "",
            "knowledge_explanation": row[75] or "",
        }
        for row in rows
    ]

    validation_results = get_validation_results_for_recommendations([
        recommendation["id"] for recommendation in recommendations
    ])

    for recommendation in recommendations:
        validation_result = validation_results.get(recommendation["id"])
        recommendation["validation_result"] = validation_result

        if validation_result is not None:
            recommendation["validation_status"] = validation_result["status"]

    return recommendations


# ---------------------------------------------------------------------------
# Recommendation outcome tracking (schema/repository foundation, Sprint 1A).
#
# Extends the existing (dormant) recommendation_validations table. No autonomous
# runtime path writes these yet; the outcome evaluator arrives in a later sprint.
# ---------------------------------------------------------------------------

# Current format version stamped on outcome rows written through this module.
OUTCOME_SCHEMA_VERSION = 1

# Terminal outcome statuses (mirror engines.validation_engine.ValidationEngine).
# A completed outcome is immutable and is never silently overwritten.
OUTCOME_COMPLETED_STATUSES = ("Succeeded", "Failed", "Expired")

# Safe upper bound for bounded outcome reads.
OUTCOME_READ_MAX_LIMIT = 2000
RECOMMENDATION_INTELLIGENCE_MAX_LIMIT = 10000
LEARNING_INTELLIGENCE_MAX_LIMIT = 100000

# Stored recommendation_validations columns (excluding the auto id), in a fixed
# order shared by writes and reads so value tuples and row dicts always align.
_VALIDATION_COLUMNS = (
    "recommendation_id",
    "ticker",
    "recommendation",
    "recommendation_timestamp",
    "evaluation_timestamp",
    "holding_period",
    "starting_price",
    "ending_price",
    "percentage_return",
    "predicted_direction",
    "actual_direction",
    "success",
    "status",
    "notes",
    "created_at",
    "horizon_days",
    "cycle_id",
    "paper_order_id",
    "entry_price_source",
    "entry_validated",
    "eval_price_source",
    "eval_validated",
    "eval_fallback_used",
    "evaluation_source",
    "schema_version",
    "deferred_reason",
)
_OUTCOME_ROW_COLUMNS = ("id",) + _VALIDATION_COLUMNS


def _as_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _validation_values(validation_result):
    """Full column->value map for a recommendation_validations row.

    Backward compatible: legacy callers pass only the classic keys and the new
    outcome/lineage fields default to NULL (booleans normalize through
    _bool_to_int so a missing flag stays NULL, not 0). schema_version defaults to
    the current format version.
    """
    return {
        "recommendation_id": validation_result.get("recommendation_id"),
        "ticker": validation_result.get("ticker"),
        "recommendation": validation_result.get("recommendation"),
        "recommendation_timestamp": validation_result.get("recommendation_timestamp"),
        "evaluation_timestamp": validation_result.get("evaluation_timestamp"),
        "holding_period": validation_result.get("holding_period"),
        "starting_price": validation_result.get("starting_price"),
        "ending_price": validation_result.get("ending_price"),
        "percentage_return": validation_result.get("percentage_return"),
        "predicted_direction": validation_result.get("predicted_direction"),
        "actual_direction": validation_result.get("actual_direction"),
        "success": _bool_to_int(validation_result.get("success")),
        "status": validation_result.get("status"),
        "notes": validation_result.get("notes"),
        "created_at": datetime.now().isoformat(),
        "horizon_days": validation_result.get("horizon_days"),
        "cycle_id": validation_result.get("cycle_id"),
        "paper_order_id": validation_result.get("paper_order_id"),
        "entry_price_source": validation_result.get("entry_price_source"),
        "entry_validated": _bool_to_int(validation_result.get("entry_validated")),
        "eval_price_source": validation_result.get("eval_price_source"),
        "eval_validated": _bool_to_int(validation_result.get("eval_validated")),
        "eval_fallback_used": _bool_to_int(validation_result.get("eval_fallback_used")),
        "evaluation_source": validation_result.get("evaluation_source"),
        "schema_version": validation_result.get("schema_version", OUTCOME_SCHEMA_VERSION),
        "deferred_reason": validation_result.get("deferred_reason"),
    }


def _outcome_row_to_dict(row):
    return dict(zip(_OUTCOME_ROW_COLUMNS, row))


def save_validation_result(validation_result, update_recommendation_status=True):
    """Persist one recommendation outcome row, idempotently.

    Backward compatible with the original signature: a legacy call providing only
    the classic fields still inserts a row and updates the recommendation's
    validation_status, exactly as before.

    Idempotency applies only when the row is fully keyed -- both horizon_days AND
    evaluation_source are provided, as every live outcome write must:
      - a COMPLETED outcome (Succeeded/Failed/Expired) for that
        (recommendation_id, horizon_days, evaluation_source) is NEVER overwritten;
      - a non-terminal row (Pending/Deferred) is UPDATED in place -- a retry or a
        deferred evaluation completing, with no duplicate row;
      - otherwise a new row is inserted.
    Unkeyed legacy writes are always inserted (the original behavior).

    ``update_recommendation_status=False`` lets the outcome evaluator record
    evidence without changing even the recommendation's legacy status field;
    the default remains True for every existing caller.

    Returns a small status dict. Never mutates trading, order, or price data.
    """
    values = _validation_values(validation_result)
    recommendation_id = values["recommendation_id"]
    horizon_days = values["horizon_days"]
    evaluation_source = values["evaluation_source"]
    keyed = horizon_days is not None and evaluation_source is not None

    connection = get_connection()
    cursor = connection.cursor()
    try:
        existing = None
        if keyed:
            existing = cursor.execute(
                """
                SELECT id, status FROM recommendation_validations
                WHERE recommendation_id = ?
                  AND horizon_days = ?
                  AND evaluation_source = ?
                """,
                (recommendation_id, horizon_days, evaluation_source),
            ).fetchone()

        if existing is not None and existing[1] in OUTCOME_COMPLETED_STATUSES:
            # A completed outcome is immutable: never silently overwrite it.
            return {
                "written": False,
                "action": "skipped_completed",
                "id": existing[0],
                "status": existing[1],
            }

        if existing is not None:
            # Non-terminal row (Pending/Deferred) -> complete it in place.
            # created_at is preserved (only set on insert).
            update_columns = [c for c in _VALIDATION_COLUMNS if c != "created_at"]
            assignments = ", ".join(f"{column} = ?" for column in update_columns)
            cursor.execute(
                f"UPDATE recommendation_validations SET {assignments} WHERE id = ?",
                tuple(values[column] for column in update_columns) + (existing[0],),
            )
            row_id = existing[0]
            action = "updated"
        else:
            columns = ", ".join(_VALIDATION_COLUMNS)
            placeholders = ", ".join("?" for _ in _VALIDATION_COLUMNS)
            cursor.execute(
                f"INSERT INTO recommendation_validations ({columns}) VALUES ({placeholders})",
                tuple(values[column] for column in _VALIDATION_COLUMNS),
            )
            row_id = cursor.lastrowid
            action = "inserted"

        # Preserve the original recommendation validation-status update.
        if update_recommendation_status and recommendation_id is not None:
            cursor.execute(
                "UPDATE recommendations SET validation_status = ? WHERE id = ?",
                (values["status"], recommendation_id),
            )

        connection.commit()
        return {"written": True, "action": action, "id": row_id, "status": values["status"]}
    finally:
        connection.close()


def get_outcomes_for_recommendation(recommendation_id):
    """All stored outcome rows for one recommendation, newest first. Read-only."""
    connection = get_connection()
    try:
        rows = connection.execute(
            f"SELECT {', '.join(_OUTCOME_ROW_COLUMNS)} "
            "FROM recommendation_validations WHERE recommendation_id = ? "
            "ORDER BY id DESC",
            (recommendation_id,),
        ).fetchall()
    finally:
        connection.close()
    return [_outcome_row_to_dict(row) for row in rows]


def get_outcomes(ticker=None, horizon=None, evaluation_source=None, limit=200):
    """Bounded, newest-first outcome feed with optional filters. Read-only.

    limit is clamped to [1, OUTCOME_READ_MAX_LIMIT]. Non-integer limits raise as
    they would for any bad argument.
    """
    safe_limit = max(1, min(int(limit), OUTCOME_READ_MAX_LIMIT))

    clauses = []
    params = []
    if ticker:
        clauses.append("ticker = ?")
        params.append(ticker)
    if horizon is not None:
        clauses.append("horizon_days = ?")
        params.append(int(horizon))
    if evaluation_source:
        clauses.append("evaluation_source = ?")
        params.append(evaluation_source)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    connection = get_connection()
    try:
        rows = connection.execute(
            f"SELECT {', '.join(_OUTCOME_ROW_COLUMNS)} FROM recommendation_validations "
            f"{where} ORDER BY id DESC LIMIT ?",
            tuple(params) + (safe_limit,),
        ).fetchall()
    finally:
        connection.close()
    return [_outcome_row_to_dict(row) for row in rows]


def count_outcomes(status=None, evaluation_source=None):
    """Exact read-only count for operational outcome status."""
    clauses = []
    params = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if evaluation_source:
        clauses.append("evaluation_source = ?")
        params.append(evaluation_source)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    connection = get_connection()
    try:
        return connection.execute(
            f"SELECT COUNT(*) FROM recommendation_validations {where}",
            tuple(params),
        ).fetchone()[0]
    finally:
        connection.close()


def get_recommendation_intelligence_records(
    ticker=None,
    action=None,
    horizon=None,
    evaluation_source="paper",
    limit=RECOMMENDATION_INTELLIGENCE_MAX_LIMIT,
):
    """Read-only recommendation/outcome rows for deterministic analytics.

    One recommendation may appear once per matching outcome horizon. A LEFT JOIN
    preserves recommendations with no matching outcome so volume and completion
    metrics do not silently exclude unevaluated history.
    """
    result = _get_learning_records(
        ticker=ticker,
        action=action,
        horizon=horizon,
        evaluation_source=evaluation_source,
        limit=limit,
        maximum_limit=RECOMMENDATION_INTELLIGENCE_MAX_LIMIT,
    )
    result["filters"] = {
        key: result["filters"][key]
        for key in ("ticker", "action", "horizon", "evaluation_source")
    }
    return result


def get_learning_intelligence_records(
    ticker=None,
    horizon=None,
    evaluation_source="paper",
    sector=None,
    regime=None,
    limit=10000,
):
    """Bounded read-only evidence projection for Learning Intelligence.

    The projection keeps recommendation identity exact and includes only stored
    recommendation context. JSON evidence is decoded defensively; malformed
    optional context degrades to an empty list instead of failing analytics.
    """
    return _get_learning_records(
        ticker=ticker,
        horizon=horizon,
        evaluation_source=evaluation_source,
        sector=sector,
        regime=regime,
        limit=limit,
        maximum_limit=LEARNING_INTELLIGENCE_MAX_LIMIT,
    )


def _get_learning_records(
    ticker=None,
    action=None,
    horizon=None,
    evaluation_source="paper",
    sector=None,
    regime=None,
    limit=10000,
    maximum_limit=LEARNING_INTELLIGENCE_MAX_LIMIT,
):
    safe_limit = max(1, min(int(limit), int(maximum_limit)))
    clauses = []
    params = [horizon, horizon, evaluation_source, evaluation_source]
    if ticker:
        clauses.append("UPPER(r.ticker) = ?")
        params.append(str(ticker).upper())
    if action:
        clauses.append("UPPER(r.action) = ?")
        params.append(str(action).upper())
    if sector:
        clauses.append("UPPER(r.sector) = ?")
        params.append(str(sector).upper())
    if regime:
        clauses.append("UPPER(r.market_regime) = ?")
        params.append(str(regime).upper())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    join = """
        LEFT JOIN recommendation_validations v
          ON v.recommendation_id = r.id
         AND (? IS NULL OR v.horizon_days = ?)
         AND (? IS NULL OR v.evaluation_source = ?)
        LEFT JOIN atlas_runs ar ON ar.id = r.run_id
    """
    select = """
        SELECT
            r.id, r.run_id, r.ticker, r.action, r.confidence,
            COALESCE(r.created_at, r.entry_at, ar.run_time),
            r.entry_at, r.outcome_state,
            v.id, v.horizon_days, v.evaluation_source, v.status,
            v.success, v.percentage_return, v.evaluation_timestamp,
            v.starting_price, v.ending_price,
            r.committee_members, r.committee_agreement, r.evidence_breakdown,
            r.market_regime, r.sector, r.forecast_direction,
            r.news_sentiment, r.signal_label
        FROM recommendations r
    """
    connection = get_connection()
    try:
        total = connection.execute(
            f"SELECT COUNT(*) FROM recommendations r {join} {where}",
            tuple(params),
        ).fetchone()[0]
        rows = connection.execute(
            f"{select} {join} {where} "
            "ORDER BY COALESCE(v.evaluation_timestamp, r.created_at, r.entry_at, ar.run_time) ASC, "
            "r.id ASC, v.id ASC LIMIT ?",
            tuple(params) + (safe_limit,),
        ).fetchall()
    finally:
        connection.close()

    records = [
        {
            "recommendation_id": row[0],
            "run_id": row[1],
            "ticker": row[2],
            "action": row[3],
            "confidence": row[4],
            "recommendation_at": row[5],
            "entry_at": row[6],
            "outcome_state": row[7],
            "outcome_id": row[8],
            "horizon_days": row[9],
            "evaluation_source": row[10],
            "status": row[11],
            "success": _int_to_bool(row[12]),
            "percentage_return": row[13],
            "evaluation_at": row[14],
            "starting_price": row[15],
            "ending_price": row[16],
            "committee_members": _safe_json_list(row[17]),
            "committee_agreement": row[18],
            "evidence_breakdown": _safe_json_list(row[19]),
            "market_regime": row[20],
            "sector": row[21],
            "forecast_direction": row[22],
            "news_sentiment": row[23],
            "signal_label": row[24],
        }
        for row in rows
    ]
    return {
        "records": records,
        "total": total,
        "limit": safe_limit,
        "truncated": total > len(records),
        "filters": {
            "ticker": str(ticker).upper() if ticker else None,
            "action": str(action).upper() if action else None,
            "horizon": horizon,
            "evaluation_source": evaluation_source,
            "sector": str(sector).upper() if sector else None,
            "regime": str(regime).upper() if regime else None,
        },
    }


def _safe_json_list(value):
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError):
        return []
    return decoded if isinstance(decoded, list) else []


def get_pending_evaluations(now, horizons, evaluation_source="paper"):
    """Recommendations whose entry_at exists and whose horizon is due, and that
    lack a completed outcome for (recommendation, horizon, evaluation_source).

    Pure read: no price fetching, no mutation. Deterministic given `now` (a
    datetime or ISO string; defaults to the wall clock only if unparseable).
    Returns one candidate dict per (recommendation, horizon) still needing
    evaluation. Until live entry-price capture lands (a later sprint), entry_at
    is unset for autonomous recommendations, so this returns [] in practice.
    """
    now_dt = _as_datetime(now) or datetime.now()
    horizon_list = [int(h) for h in horizons]

    connection = get_connection()
    try:
        recommendation_rows = connection.execute(
            """
            SELECT id, run_id, ticker, action, entry_at, entry_price,
                   entry_price_source, entry_validated
            FROM recommendations
            WHERE entry_at IS NOT NULL
            """
        ).fetchall()
        completed_rows = connection.execute(
            """
            SELECT recommendation_id, horizon_days
            FROM recommendation_validations
            WHERE evaluation_source = ? AND status IN (?, ?, ?)
            """,
            (evaluation_source,) + OUTCOME_COMPLETED_STATUSES,
        ).fetchall()
    finally:
        connection.close()

    completed = {(row[0], row[1]) for row in completed_rows}

    pending = []
    for (
        recommendation_id,
        run_id,
        ticker,
        action,
        entry_at,
        entry_price,
        entry_price_source,
        entry_validated,
    ) in recommendation_rows:
        entry_dt = _as_datetime(entry_at)
        if entry_dt is None:
            continue
        elapsed_days = (now_dt - entry_dt).total_seconds() / 86400.0
        for horizon in horizon_list:
            if elapsed_days < horizon:
                continue
            if (recommendation_id, horizon) in completed:
                continue
            pending.append(
                {
                    "recommendation_id": recommendation_id,
                    "run_id": run_id,
                    "ticker": ticker,
                    "action": action,
                    "entry_at": entry_at,
                    "entry_price": entry_price,
                    "entry_price_source": entry_price_source,
                    "entry_validated": entry_validated,
                    "horizon_days": horizon,
                    "evaluation_source": evaluation_source,
                }
            )
    return pending


def link_order_to_recommendation(order_id, recommendation_id):
    """Attach a recommendation_id to an existing paper-fund order (narrow update).

    Sets ONLY recommendation_id -- never touches status, quantity, prices,
    reason, or policy. Reports clearly when either id is missing rather than
    creating rows or failing silently.
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        order = cursor.execute(
            "SELECT order_id FROM paper_fund_orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if order is None:
            return {"linked": False, "reason": "order_not_found", "order_id": order_id}

        if recommendation_id is not None:
            recommendation = cursor.execute(
                "SELECT id FROM recommendations WHERE id = ?",
                (recommendation_id,),
            ).fetchone()
            if recommendation is None:
                return {
                    "linked": False,
                    "reason": "recommendation_not_found",
                    "recommendation_id": recommendation_id,
                }

        cursor.execute(
            "UPDATE paper_fund_orders SET recommendation_id = ? WHERE order_id = ?",
            (recommendation_id, order_id),
        )
        connection.commit()
        return {
            "linked": True,
            "order_id": order_id,
            "recommendation_id": recommendation_id,
        }
    finally:
        connection.close()


def save_benchmark_results(results):
    connection = get_connection()
    cursor = connection.cursor()

    for result in results:
        cursor.execute(
            """
            INSERT INTO benchmark_results (
                engine_name,
                version,
                benchmark_date,
                metric,
                value,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                result.get("engine_name"),
                result.get("version"),
                result.get("benchmark_date"),
                result.get("metric"),
                result.get("value"),
                result.get("notes", ""),
            )
        )

    connection.commit()
    connection.close()


def save_evidence_benchmarks(results):
    connection = get_connection()
    cursor = connection.cursor()

    for result in results:
        cursor.execute(
            """
            INSERT INTO evidence_benchmarks (
                source_name,
                effectiveness_score,
                sample_count,
                last_benchmark_date,
                engine_name,
                version,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.get("source_name"),
                result.get("effectiveness_score"),
                result.get("sample_count"),
                result.get("benchmark_date"),
                result.get("engine_name"),
                result.get("version"),
                result.get("notes", ""),
            )
        )

    connection.commit()
    connection.close()


def get_latest_benchmark_results(limit=20):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                engine_name,
                version,
                benchmark_date,
                metric,
                value,
                notes
            FROM benchmark_results
            ORDER BY benchmark_date DESC, id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        connection.close()

        if "no such table" in str(error).lower():
            return []

        raise

    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "engine_name": row[0],
            "version": row[1],
            "benchmark_date": row[2],
            "metric": row[3],
            "value": row[4],
            "notes": row[5] or "",
        }
        for row in rows
    ]


def get_latest_evidence_benchmarks(limit=20):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                source_name,
                effectiveness_score,
                sample_count,
                last_benchmark_date,
                engine_name,
                version,
                notes
            FROM evidence_benchmarks
            ORDER BY last_benchmark_date DESC, id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        connection.close()

        if "no such table" in str(error).lower():
            return []

        raise

    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "source_name": row[0],
            "effectiveness_score": row[1],
            "sample_count": row[2],
            "last_benchmark_date": row[3],
            "engine_name": row[4],
            "version": row[5],
            "notes": row[6] or "",
        }
        for row in rows
    ]


def save_research_experiment(experiment):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO research_experiments (
            experiment_id,
            title,
            description,
            experiment_date,
            dataset,
            tickers,
            provider_configuration,
            forecast_provider,
            news_provider,
            fundamental_provider,
            validation_window,
            benchmark_snapshot,
            related_discoveries,
            status,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            experiment.get("experiment_id"),
            experiment.get("title"),
            experiment.get("description"),
            experiment.get("date"),
            experiment.get("dataset"),
            json.dumps(experiment.get("ticker_list", [])),
            json.dumps(experiment.get("provider_configuration", {})),
            experiment.get("forecast_provider"),
            experiment.get("news_provider"),
            experiment.get("fundamental_provider"),
            experiment.get("validation_window"),
            json.dumps(experiment.get("benchmark_snapshot", {})),
            json.dumps(experiment.get("related_discoveries", [])),
            experiment.get("status"),
            experiment.get("notes", ""),
        )
    )

    connection.commit()
    connection.close()


def save_research_strategy_results(experiment_id, results):
    connection = get_connection()
    cursor = connection.cursor()

    for result in results:
        cursor.execute(
            """
            INSERT INTO research_strategy_results (
                experiment_id,
                strategy_name,
                components,
                recommendation_count,
                hit_rate,
                average_return,
                average_gain,
                average_loss,
                confidence,
                runtime,
                missing_data
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                experiment_id,
                result.get("strategy_name"),
                json.dumps(result.get("components", [])),
                result.get("recommendation_count"),
                result.get("hit_rate"),
                result.get("average_return"),
                result.get("average_gain"),
                result.get("average_loss"),
                result.get("confidence"),
                result.get("runtime"),
                json.dumps(result.get("missing_data", [])),
            )
        )

    connection.commit()
    connection.close()


def save_research_provider_results(experiment_id, results):
    connection = get_connection()
    cursor = connection.cursor()

    for result in results:
        cursor.execute(
            """
            INSERT INTO research_provider_results (
                experiment_id,
                provider_type,
                provider_name,
                status,
                score,
                rank,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                experiment_id,
                result.get("provider_type"),
                result.get("provider_name"),
                result.get("status"),
                result.get("score"),
                result.get("rank"),
                result.get("notes", ""),
            )
        )

    connection.commit()
    connection.close()


def save_research_attributions(experiment_id, results):
    connection = get_connection()
    cursor = connection.cursor()

    for result in results:
        cursor.execute(
            """
            INSERT INTO research_attributions (
                experiment_id,
                ticker,
                action,
                strongest_engine,
                confidence_drag_engine,
                changed_evidence,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                experiment_id,
                result.get("ticker"),
                result.get("action"),
                result.get("strongest_engine"),
                result.get("confidence_drag_engine"),
                json.dumps(result.get("changed_evidence", [])),
                result.get("notes", ""),
            )
        )

    connection.commit()
    connection.close()


def get_research_dashboard_data(limit=10):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            experiment_id,
            title,
            experiment_date,
            dataset,
            status
        FROM research_experiments
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )
    experiment_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT provider_type, provider_name, score, rank, status
        FROM research_provider_results
        ORDER BY rank ASC, id DESC
        LIMIT ?
        """,
        (limit,)
    )
    provider_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT strategy_name, hit_rate, average_return, confidence
        FROM research_strategy_results
        ORDER BY hit_rate DESC, id DESC
        LIMIT ?
        """,
        (limit,)
    )
    engine_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT metric, value, benchmark_date
        FROM benchmark_results
        ORDER BY benchmark_date DESC, id DESC
        LIMIT ?
        """,
        (limit,)
    )
    benchmark_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT id, title, confidence, importance, support_level
        FROM discoveries
        ORDER BY importance DESC, confidence DESC
        LIMIT ?
        """,
        (limit,)
    )
    discovery_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            model_name,
            model_type,
            provider,
            dataset,
            date_range,
            validation_window,
            sample_size,
            accuracy,
            win_rate,
            average_return,
            sharpe_ratio,
            max_drawdown,
            runtime_placeholder,
            memory_placeholder,
            cost_placeholder,
            integration_difficulty,
            recommendation,
            overall_score,
            evaluation_date,
            status
        FROM model_evaluations
        ORDER BY overall_score DESC, accuracy DESC, id DESC
        LIMIT ?
        """,
        (limit,)
    )
    model_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            case_id,
            ticker,
            recommendation,
            market_regime,
            evidence,
            committee,
            executive_review,
            knowledge_score,
            stability_score,
            outcome,
            return_value,
            holding_period,
            validation,
            benchmark,
            hypotheses,
            counterfactuals,
            lessons_learned,
            catalysts,
            probability_report,
            case_date
        FROM case_studies
        ORDER BY case_date DESC, case_id DESC
        LIMIT ?
        """,
        (limit,)
    )
    case_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            experiment_id,
            report_date,
            feature_tested,
            baseline,
            candidate,
            sample_size,
            metric_comparison,
            cross_regime_validation,
            generalization_tests,
            scientific_result,
            adoption_decision,
            adoption_explanation,
            policy
        FROM scientific_validation_reports
        ORDER BY report_date DESC, id DESC
        LIMIT ?
        """,
        (limit,)
    )
    scientific_validation_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            arena_id,
            run_date,
            dataset,
            tickers,
            date_range,
            validation_window,
            strategy_configs,
            market_regimes_tested,
            results,
            comparison,
            scientific_validation,
            policy
        FROM simulation_arena_runs
        ORDER BY run_date DESC, id DESC
        LIMIT ?
        """,
        (limit,)
    )
    simulation_arena_rows = cursor.fetchall()

    paper_portfolio_rows = _paper_portfolio_rows(cursor, limit)
    paper_trade_rows = _paper_trade_rows(cursor, limit)
    paper_performance_rows = _paper_performance_rows(cursor, limit)
    portfolio_construction_rows = _portfolio_construction_rows(cursor, limit)

    connection.close()

    return {
        "research_experiments": [
            {
                "experiment_id": row[0],
                "title": row[1],
                "date": row[2],
                "dataset": row[3],
                "status": row[4],
            }
            for row in experiment_rows
        ],
        "provider_rankings": [
            {
                "provider_type": row[0],
                "provider_name": row[1],
                "score": row[2],
                "rank": row[3],
                "status": row[4],
            }
            for row in provider_rows
        ],
        "engine_rankings": [
            {
                "strategy_name": row[0],
                "hit_rate": row[1],
                "average_return": row[2],
                "confidence": row[3],
            }
            for row in engine_rows
        ],
        "historical_improvements": benchmark_rows,
        "recommendation_quality": engine_rows,
        "validation_trends": engine_rows,
        "benchmark_trends": benchmark_rows,
        "discoveries": [
            {
                "id": row[0],
                "title": row[1],
                "confidence": row[2],
                "importance": row[3],
                "support_level": row[4],
            }
            for row in discovery_rows
        ],
        "model_evaluations": [
            _model_evaluation_row(row) for row in model_rows
        ],
        "case_studies": [
            _case_study_row(row) for row in case_rows
        ],
        "scientific_validations": [
            _scientific_validation_row(row)
            for row in scientific_validation_rows
        ],
        "simulation_arena_runs": [
            _simulation_arena_row(row) for row in simulation_arena_rows
        ],
        "paper_portfolio_history": (
            [_paper_portfolio_row(row) for row in paper_portfolio_rows]
            or get_demo_paper_portfolio_history(limit)
        ),
        "paper_trades": (
            [_paper_trade_row(row) for row in paper_trade_rows]
            or get_demo_paper_trades(limit)
        ),
        "paper_performance_reports": (
            [_paper_performance_row(row) for row in paper_performance_rows]
            or get_demo_paper_performance_reports(limit)
        ),
        "portfolio_construction_reports": [
            _portfolio_construction_row(row)
            for row in portfolio_construction_rows
        ],
    }


def get_brain_recommendation(ticker):
    """Read-only lookup of the latest saved recommendation for a ticker.

    Reuses get_discovery_source_data; returns None when no recommendation is
    saved so callers can fall back to a deterministic example.
    """
    ticker = (ticker or "").upper()
    source_data = get_discovery_source_data()

    for item in source_data.get("recommendations", []):
        if str(item.get("ticker", "")).upper() == ticker:
            return item

    return None


def get_discovery_source_data():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            ticker,
            action,
            confidence,
            evidence_breakdown,
            committee_agreement,
            main_disagreement,
            final_committee_summary,
            technical_score,
            fundamental_score,
            forecast_score,
            news_confidence,
            portfolio_score,
            risk_score,
            executive_review,
            executive_status,
            executive_confidence,
            executive_warnings,
            executive_strengths,
            executive_weaknesses,
            required_follow_up_research,
            missing_evidence,
            assumptions,
            counterfactuals,
            stability_score,
            stability_level,
            most_sensitive_factor,
            stability_explanation,
            knowledge_score,
            knowledge_level,
            knowledge_explanation,
            research_memory_report
        FROM recommendations
        ORDER BY id ASC
        """
    )
    recommendation_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            recommendation_id,
            percentage_return,
            success,
            status
        FROM recommendation_validations
        ORDER BY id ASC
        """
    )
    validation_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            engine_name,
            version,
            benchmark_date,
            metric,
            value,
            notes
        FROM benchmark_results
        ORDER BY benchmark_date DESC, id DESC
        """
    )
    benchmark_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT provider_type, provider_name, status, score, rank, notes
        FROM research_provider_results
        ORDER BY id ASC
        """
    )
    provider_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT experiment_id, title, status, related_discoveries
        FROM research_experiments
        ORDER BY id ASC
        """
    )
    experiment_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            model_name,
            model_type,
            provider,
            dataset,
            date_range,
            validation_window,
            sample_size,
            accuracy,
            win_rate,
            average_return,
            sharpe_ratio,
            max_drawdown,
            runtime_placeholder,
            memory_placeholder,
            cost_placeholder,
            integration_difficulty,
            recommendation,
            overall_score,
            evaluation_date,
            status
        FROM model_evaluations
        ORDER BY overall_score DESC, accuracy DESC, id DESC
        """
    )
    model_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            case_id,
            ticker,
            recommendation,
            market_regime,
            evidence,
            committee,
            executive_review,
            knowledge_score,
            stability_score,
            outcome,
            return_value,
            holding_period,
            validation,
            benchmark,
            hypotheses,
            counterfactuals,
            lessons_learned,
            catalysts,
            probability_report,
            case_date
        FROM case_studies
        ORDER BY case_date DESC, case_id DESC
        """
    )
    case_rows = cursor.fetchall()

    try:
        cursor.execute(
            """
            SELECT
                recommendation_id,
                ticker,
                recommendation,
                probabilities,
                expected_outcome,
                confidence_quality,
                similar_historical_cases,
                explanation,
                report_date
            FROM probability_reports
            ORDER BY id DESC
            """
        )
        probability_rows = cursor.fetchall()
    except Exception as error:
        if "no such table" not in str(error).lower():
            raise
        probability_rows = []

    try:
        cursor.execute(
            """
            SELECT
                experiment_id,
                report_date,
                feature_tested,
                baseline,
                candidate,
                sample_size,
                metric_comparison,
                cross_regime_validation,
                generalization_tests,
                scientific_result,
                adoption_decision,
                adoption_explanation,
                policy
            FROM scientific_validation_reports
            ORDER BY report_date DESC, id DESC
            """
        )
        scientific_validation_rows = cursor.fetchall()
    except Exception as error:
        if "no such table" not in str(error).lower():
            raise
        scientific_validation_rows = []

    try:
        cursor.execute(
            """
            SELECT
                arena_id,
                run_date,
                dataset,
                tickers,
                date_range,
                validation_window,
                strategy_configs,
                market_regimes_tested,
                results,
                comparison,
                scientific_validation,
                policy
            FROM simulation_arena_runs
            ORDER BY run_date DESC, id DESC
            """
        )
        simulation_arena_rows = cursor.fetchall()
    except Exception as error:
        if "no such table" not in str(error).lower():
            raise
        simulation_arena_rows = []

    paper_portfolio_rows = _paper_portfolio_rows(cursor, 50)
    paper_trade_rows = _paper_trade_rows(cursor, 50)
    paper_performance_rows = _paper_performance_rows(cursor, 50)
    portfolio_construction_rows = _portfolio_construction_rows(cursor, 50)

    connection.close()

    validations = {
        row[0]: {
            "percentage_return": row[1],
            "success": _int_to_bool(row[2]),
            "hit": _int_to_bool(row[2]),
            "status": row[3],
        }
        for row in validation_rows
    }

    return {
        "recommendations": [
            {
                "id": row[0],
                "ticker": row[1],
                "action": row[2],
                "confidence": row[3] or 0,
                "evidence_breakdown": json.loads(row[4] or "[]"),
                "committee_agreement": row[5] or 0,
                "main_disagreement": row[6] or "",
                "final_committee_summary": row[7] or "",
                "technical_score": row[8] or 0,
                "fundamental_score": row[9] or 0,
                "forecast_score": row[10] or 0,
                "news_confidence": row[11] or 0,
                "portfolio_score": row[12] or 0,
                "risk_score": row[13] or 0,
                "executive_review": json.loads(row[14] or "{}"),
                "executive_status": row[15] or "",
                "executive_confidence": row[16] or 0,
                "executive_warnings": json.loads(row[17] or "[]"),
                "executive_strengths": json.loads(row[18] or "[]"),
                "executive_weaknesses": json.loads(row[19] or "[]"),
                "required_follow_up_research": json.loads(row[20] or "[]"),
                "missing_evidence": json.loads(row[21] or "[]"),
                "assumptions": json.loads(row[22] or "[]"),
                "counterfactuals": json.loads(row[23] or "[]"),
                "stability_score": row[24] or 0,
                "stability_level": row[25] or "",
                "most_sensitive_factor": row[26] or "",
                "stability_explanation": row[27] or "",
                "knowledge_score": row[28] or 0,
                "knowledge_level": row[29] or "",
                "knowledge_explanation": row[30] or "",
                "research_memory_report": json.loads(row[31] or "{}"),
                "validation_result": validations.get(row[0]),
            }
            for row in recommendation_rows
        ],
        "benchmark_results": [
            {
                "engine_name": row[0],
                "version": row[1],
                "benchmark_date": row[2],
                "metric": row[3],
                "value": row[4],
                "notes": row[5] or "",
            }
            for row in benchmark_rows
        ],
        "provider_results": [
            {
                "provider_type": row[0],
                "provider_name": row[1],
                "status": row[2],
                "score": row[3],
                "rank": row[4],
                "notes": row[5] or "",
            }
            for row in provider_rows
        ],
        "research_experiments": [
            {
                "experiment_id": row[0],
                "title": row[1],
                "status": row[2],
                "related_discoveries": json.loads(row[3] or "[]"),
            }
            for row in experiment_rows
        ],
        "model_evaluations": [
            _model_evaluation_row(row) for row in model_rows
        ],
        "case_studies": [
            _case_study_row(row) for row in case_rows
        ],
        "probability_reports": [
            _probability_report_row(row) for row in probability_rows
        ],
        "scientific_validations": [
            _scientific_validation_row(row)
            for row in scientific_validation_rows
        ],
        "simulation_arena_runs": [
            _simulation_arena_row(row) for row in simulation_arena_rows
        ],
        "paper_portfolio_history": (
            [_paper_portfolio_row(row) for row in paper_portfolio_rows]
            or get_demo_paper_portfolio_history(50)
        ),
        "paper_trades": (
            [_paper_trade_row(row) for row in paper_trade_rows]
            or get_demo_paper_trades(50)
        ),
        "paper_performance_reports": (
            [_paper_performance_row(row) for row in paper_performance_rows]
            or get_demo_paper_performance_reports(50)
        ),
        "portfolio_construction_reports": [
            _portfolio_construction_row(row)
            for row in portfolio_construction_rows
        ],
    }


def save_case_studies(case_studies):
    connection = get_connection()
    cursor = connection.cursor()

    for case in case_studies:
        cursor.execute(
            """
            INSERT OR REPLACE INTO case_studies (
                case_id,
                ticker,
                recommendation,
                market_regime,
                evidence,
                committee,
                executive_review,
                knowledge_score,
                stability_score,
                outcome,
                return_value,
                holding_period,
                validation,
                benchmark,
                hypotheses,
                counterfactuals,
                lessons_learned,
                catalysts,
                probability_report,
                case_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case.get("case_id"),
                case.get("ticker"),
                case.get("recommendation"),
                case.get("market_regime"),
                json.dumps(case.get("evidence", [])),
                json.dumps(case.get("committee", {})),
                json.dumps(case.get("executive_review", {})),
                case.get("knowledge_score"),
                case.get("stability_score"),
                case.get("outcome"),
                case.get("return"),
                case.get("holding_period"),
                json.dumps(case.get("validation", {})),
                json.dumps(case.get("benchmark", {})),
                json.dumps(case.get("hypotheses", [])),
                json.dumps(case.get("counterfactuals", [])),
                json.dumps(case.get("lessons_learned", {})),
                json.dumps(case.get("catalysts", [])),
                json.dumps(case.get("probability_report", {})),
                case.get("case_date"),
            )
        )

    connection.commit()
    connection.close()


def get_case_studies(limit=50):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                case_id,
                ticker,
                recommendation,
                market_regime,
                evidence,
                committee,
                executive_review,
                knowledge_score,
                stability_score,
                outcome,
                return_value,
                holding_period,
                validation,
                benchmark,
                hypotheses,
                counterfactuals,
                lessons_learned,
                catalysts,
                probability_report,
                case_date
            FROM case_studies
            ORDER BY case_date DESC, case_id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        connection.close()

        if "no such table" in str(error).lower():
            return []

        raise

    rows = cursor.fetchall()
    connection.close()

    return [
        _case_study_row(row) for row in rows
    ]


def save_probability_reports(reports):
    connection = get_connection()
    cursor = connection.cursor()

    for report in reports:
        cursor.execute(
            """
            INSERT INTO probability_reports (
                recommendation_id,
                ticker,
                recommendation,
                probabilities,
                expected_outcome,
                confidence_quality,
                similar_historical_cases,
                explanation,
                report_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.get("recommendation_id"),
                report.get("ticker"),
                report.get("recommendation"),
                json.dumps(report.get("probabilities", {})),
                json.dumps(report.get("expected_outcome", {})),
                json.dumps(report.get("confidence_quality", {})),
                json.dumps(report.get("similar_historical_cases", [])),
                report.get("explanation", ""),
                report.get("report_date") or datetime.now().isoformat(),
            )
        )

    connection.commit()
    connection.close()


def get_probability_reports(limit=50):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                recommendation_id,
                ticker,
                recommendation,
                probabilities,
                expected_outcome,
                confidence_quality,
                similar_historical_cases,
                explanation,
                report_date
            FROM probability_reports
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        connection.close()

        if "no such table" in str(error).lower():
            return []

        raise

    rows = cursor.fetchall()
    connection.close()

    return [
        _probability_report_row(row) for row in rows
    ]


def save_scientific_validation_report(report):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO scientific_validation_reports (
            experiment_id,
            report_date,
            feature_tested,
            baseline,
            candidate,
            sample_size,
            metric_comparison,
            cross_regime_validation,
            generalization_tests,
            scientific_result,
            adoption_decision,
            adoption_explanation,
            policy
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report.get("experiment_id"),
            report.get("date"),
            report.get("feature_tested"),
            json.dumps(report.get("baseline", {})),
            json.dumps(report.get("candidate", {})),
            report.get("sample_size"),
            json.dumps(report.get("metric_comparison", [])),
            json.dumps(report.get("cross_regime_validation", [])),
            json.dumps(report.get("generalization_tests", [])),
            report.get("scientific_result"),
            report.get("adoption_decision"),
            report.get("adoption_explanation"),
            json.dumps(report.get("policy", {})),
        )
    )

    connection.commit()
    connection.close()


def get_scientific_validation_reports(limit=50):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                experiment_id,
                report_date,
                feature_tested,
                baseline,
                candidate,
                sample_size,
                metric_comparison,
                cross_regime_validation,
                generalization_tests,
                scientific_result,
                adoption_decision,
                adoption_explanation,
                policy
            FROM scientific_validation_reports
            ORDER BY report_date DESC, id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        connection.close()

        if "no such table" in str(error).lower():
            return []

        raise

    rows = cursor.fetchall()
    connection.close()

    return [
        _scientific_validation_row(row) for row in rows
    ]


def save_simulation_arena_run(arena):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO simulation_arena_runs (
            arena_id,
            run_date,
            dataset,
            tickers,
            date_range,
            validation_window,
            strategy_configs,
            market_regimes_tested,
            results,
            comparison,
            scientific_validation,
            policy
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            arena.get("arena_id"),
            arena.get("date"),
            arena.get("dataset"),
            json.dumps(arena.get("tickers", [])),
            json.dumps(arena.get("date_range", {})),
            arena.get("validation_window"),
            json.dumps(arena.get("strategy_configs", [])),
            json.dumps(arena.get("market_regimes_tested", [])),
            json.dumps(arena.get("results", [])),
            json.dumps(arena.get("comparison", {})),
            json.dumps(arena.get("scientific_validation", {})),
            json.dumps(arena.get("policy", {})),
        )
    )

    connection.commit()
    connection.close()


def get_simulation_arena_runs(limit=50):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                arena_id,
                run_date,
                dataset,
                tickers,
                date_range,
                validation_window,
                strategy_configs,
                market_regimes_tested,
                results,
                comparison,
                scientific_validation,
                policy
            FROM simulation_arena_runs
            ORDER BY run_date DESC, id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        connection.close()

        if "no such table" in str(error).lower():
            return []

        raise

    rows = cursor.fetchall()
    connection.close()

    return [
        _simulation_arena_row(row) for row in rows
    ]


def save_registry_experiment(experiment):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO research_experiment_registry (
            experiment_id,
            title,
            description,
            status,
            created_date,
            author,
            feature_being_tested,
            baseline_strategy,
            candidate_strategy,
            validation_state,
            priority,
            notes,
            adoption_decision,
            arena_metrics,
            policy
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            experiment.get("experiment_id"),
            experiment.get("title"),
            experiment.get("description"),
            experiment.get("status"),
            experiment.get("created_date"),
            experiment.get("author"),
            experiment.get("feature_being_tested"),
            experiment.get("baseline_strategy"),
            experiment.get("candidate_strategy"),
            experiment.get("validation_state"),
            experiment.get("priority"),
            experiment.get("notes", ""),
            experiment.get("adoption_decision", "RETEST"),
            json.dumps(experiment.get("arena_metrics", {})),
            json.dumps(experiment.get("policy", {})),
        )
    )

    connection.commit()
    connection.close()


def get_registry_experiments(limit=200):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                experiment_id,
                title,
                description,
                status,
                created_date,
                author,
                feature_being_tested,
                baseline_strategy,
                candidate_strategy,
                validation_state,
                priority,
                notes,
                adoption_decision,
                arena_metrics,
                policy
            FROM research_experiment_registry
            ORDER BY created_date DESC, experiment_id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        connection.close()

        if "no such table" in str(error).lower():
            return []

        raise

    rows = cursor.fetchall()
    connection.close()

    return [_registry_experiment_row(row) for row in rows]


def save_market_data_snapshot(snapshot):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO market_data_snapshots (
            snapshot_date,
            provider,
            requested_provider,
            fallback_used,
            validated,
            ticker_count,
            prices,
            market_status,
            policy
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot.get("snapshot_date"),
            snapshot.get("provider"),
            snapshot.get("requested_provider"),
            _bool_to_int(snapshot.get("fallback_used")),
            _bool_to_int(snapshot.get("validated")),
            snapshot.get("ticker_count"),
            json.dumps(snapshot.get("prices", {})),
            json.dumps(snapshot.get("market_status", {})),
            json.dumps(snapshot.get("policy", {})),
        )
    )

    connection.commit()
    connection.close()


def get_market_data_snapshots(limit=20):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                snapshot_date,
                provider,
                requested_provider,
                fallback_used,
                validated,
                ticker_count,
                prices,
                market_status,
                policy
            FROM market_data_snapshots
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        connection.close()

        if "no such table" in str(error).lower():
            return []

        raise

    rows = cursor.fetchall()
    connection.close()

    return [_market_data_snapshot_row(row) for row in rows]


def get_latest_market_data_snapshot():
    snapshots = get_market_data_snapshots(limit=1)

    return snapshots[0] if snapshots else None


def save_monthly_report(report):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO monthly_reports (
            month,
            report_date,
            performance,
            major_lessons,
            best_decisions,
            largest_mistakes,
            research_progress,
            validation_summary,
            policy
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report.get("month"),
            report.get("report_date", report.get("month")),
            json.dumps(report.get("performance", {})),
            json.dumps(report.get("major_lessons", [])),
            json.dumps(report.get("best_decisions", [])),
            json.dumps(report.get("largest_mistakes", [])),
            json.dumps(report.get("research_progress", {})),
            json.dumps(report.get("validation_summary", {})),
            json.dumps(report.get("policy", {})),
        )
    )

    connection.commit()
    connection.close()


def get_monthly_reports(limit=24):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                month,
                report_date,
                performance,
                major_lessons,
                best_decisions,
                largest_mistakes,
                research_progress,
                validation_summary,
                policy
            FROM monthly_reports
            ORDER BY month DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        connection.close()

        if "no such table" in str(error).lower():
            return []

        raise

    rows = cursor.fetchall()
    connection.close()

    return [_monthly_report_row(row) for row in rows]


def get_latest_monthly_report():
    reports = get_monthly_reports(limit=1)

    return reports[0] if reports else None


def get_latest_paper_replay_audit():
    """Return the most recent persisted historical replay audit, if any."""
    for report in get_paper_performance_reports(limit=50):
        audit = (report.get("performance") or {}).get("replay_audit")
        if audit:
            return audit

    return None


def save_paper_trading_report(report):
    # Paper trading data must be price-backed or absent. Demo/simulated runs
    # (daily cycle demo prices, fake previews) and FAILED replays are never
    # saved as paper P/L, trades, or chart points.
    metadata = report.get("metadata", {})
    price_backed = report.get("price_backed", metadata.get("price_backed"))
    if report.get("replay_status") == "FAILED" or price_backed is not True:
        return {
            "persisted": False,
            "reason": report.get(
                "error",
                "Paper trading reports persist only when price-backed.",
            ) or "Paper trading reports persist only when price-backed.",
            "price_backed": False,
        }

    connection = get_connection()
    cursor = connection.cursor()
    portfolio = report.get("portfolio", {})
    policy = report.get("policy", {})
    metadata = report.get("metadata", {})
    snapshots = report.get("replay_history") or [portfolio]

    for snapshot in snapshots:
        cursor.execute(
            """
            INSERT INTO paper_portfolio_snapshots (
                snapshot_date,
                cash,
                positions,
                current_value,
                realized_pl,
                unrealized_pl,
                portfolio_value,
                daily_return,
                total_return,
                policy
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.get("date"),
                snapshot.get("cash"),
                json.dumps(snapshot.get("positions", {})),
                snapshot.get("current_value"),
                snapshot.get("realized_pl"),
                snapshot.get("unrealized_pl"),
                snapshot.get("portfolio_value"),
                snapshot.get("daily_return"),
                snapshot.get("total_return"),
                json.dumps(policy | {"replay_day": snapshot.get("replay_day")}),
            )
        )

    for trade in report.get("trades", []):
        recommendation_snapshot = trade.get("recommendation_snapshot", {})
        recommendation_snapshot = recommendation_snapshot | {
            "run_metadata": metadata,
            "execution": {
                "transaction_cost": trade.get("transaction_cost", 0),
                "slippage": trade.get("slippage", 0),
            },
        }
        cursor.execute(
            """
            INSERT OR REPLACE INTO paper_trades (
                trade_id,
                ticker,
                action,
                entry_date,
                entry_price,
                exit_date,
                exit_price,
                holding_period,
                quantity,
                profit_loss,
                reason,
                recommendation_snapshot
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade.get("trade_id"),
                trade.get("ticker"),
                trade.get("action"),
                trade.get("entry_date"),
                trade.get("entry_price"),
                trade.get("exit_date"),
                trade.get("exit_price"),
                trade.get("holding_period"),
                trade.get("quantity"),
                trade.get("profit_loss"),
                trade.get("reason", ""),
                json.dumps(recommendation_snapshot),
            )
        )

    cursor.execute(
        """
        INSERT INTO paper_performance_reports (
            report_date,
            performance,
            research,
            policy
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            portfolio.get("date"),
            json.dumps(report.get("performance", {})),
            json.dumps(report.get("research", {})),
            json.dumps(policy),
        )
    )

    connection.commit()
    connection.close()


def get_paper_portfolio_history(limit=50):
    connection = get_connection()
    cursor = connection.cursor()
    rows = _paper_portfolio_rows(cursor, limit)
    connection.close()

    return [_paper_portfolio_row(row) for row in rows]


def get_paper_trades(limit=100):
    connection = get_connection()
    cursor = connection.cursor()
    rows = _paper_trade_rows(cursor, limit)
    connection.close()

    return [_paper_trade_row(row) for row in rows]


def get_paper_performance_reports(limit=50):
    connection = get_connection()
    cursor = connection.cursor()
    rows = _paper_performance_rows(cursor, limit)
    connection.close()

    return [_paper_performance_row(row) for row in rows]


def get_demo_paper_portfolio_history(limit=50):
    if limit <= 0:
        return []

    report = PaperTradingEngine().demo_report()
    portfolio = report["portfolio"] | {
        "policy": report["policy"],
    }

    return [portfolio]


def get_demo_paper_trades(limit=100):
    if limit <= 0:
        return []

    return PaperTradingEngine().demo_report()["trades"][:limit]


def get_demo_paper_performance_reports(limit=50):
    if limit <= 0:
        return []

    report = PaperTradingEngine().demo_report()

    return [
        {
            "id": "SIMULATED-DEMO",
            "date": report["portfolio"]["date"],
            "performance": report["performance"],
            "research": report["research"],
            "policy": report["policy"],
        }
    ]


def reset_paper_simulation_data():
    connection = get_connection()
    cursor = connection.cursor()
    cleared = []

    for table_name in [
        "paper_portfolio_snapshots",
        "paper_trades",
        "paper_performance_reports",
        "daily_cycle_runs",
        "daily_journals",
    ]:
        try:
            cursor.execute(f"DELETE FROM {table_name}")
            cleared.append(table_name)
        except Exception as error:
            if "no such table" not in str(error).lower():
                connection.close()
                raise

    connection.commit()
    connection.close()

    return {
        "status": "RESET",
        "cleared_tables": cleared,
        "policy": {
            "paper_only": True,
            "broker_integration": False,
            "real_money": False,
            "automatic_execution": False,
            "changes_recommendation_behavior": False,
            "status": "SIMULATED",
        },
    }


def save_paper_fund_state(state):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO paper_fund_states (
            updated_at,
            fund_status,
            watchlist,
            starting_cash,
            cash,
            positions,
            realized_pl,
            interval_minutes,
            last_update,
            next_update,
            last_error,
            price_provider,
            policy
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            state.get("updated_at"),
            state.get("fund_status"),
            json.dumps(state.get("watchlist", [])),
            state.get("starting_cash"),
            state.get("cash"),
            json.dumps(state.get("positions", {})),
            state.get("realized_pl"),
            state.get("interval_minutes"),
            state.get("last_update"),
            state.get("next_update"),
            state.get("last_error"),
            state.get("price_provider"),
            json.dumps(state.get("policy", {})),
        )
    )
    connection.commit()
    connection.close()


def get_latest_paper_fund_state():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT updated_at, fund_status, watchlist, starting_cash, cash,
               positions, realized_pl, interval_minutes, last_update,
               next_update, last_error, price_provider, policy
        FROM paper_fund_states
        ORDER BY id DESC
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None

    return {
        "updated_at": row[0],
        "fund_status": row[1],
        "watchlist": json.loads(row[2] or "[]"),
        "starting_cash": row[3],
        "cash": row[4],
        "positions": json.loads(row[5] or "{}"),
        "realized_pl": row[6],
        "interval_minutes": row[7],
        "last_update": row[8],
        "next_update": row[9],
        "last_error": row[10],
        "price_provider": row[11],
        "policy": json.loads(row[12] or "{}"),
    }


def save_paper_fund_order(order):
    connection = get_connection()
    cursor = connection.cursor()

    order_id = order.get("order_id")
    # Preserve an existing recommendation link when this (re)save omits it, so an
    # INSERT OR REPLACE that rewrites the row never silently erases the linkage.
    # Order execution fields (side/quantity/price/status/...) are untouched.
    recommendation_id = order.get("recommendation_id")
    if recommendation_id is None and order_id is not None:
        existing = cursor.execute(
            "SELECT recommendation_id FROM paper_fund_orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if existing is not None:
            recommendation_id = existing[0]

    if recommendation_id is not None:
        recommendation = cursor.execute(
            "SELECT id FROM recommendations WHERE id = ?",
            (recommendation_id,),
        ).fetchone()
        if recommendation is None:
            connection.close()
            raise ValueError(
                f"Recommendation {recommendation_id!r} does not exist; "
                "paper order was not saved."
            )

    cursor.execute(
        """
        INSERT OR REPLACE INTO paper_fund_orders (
            order_id,
            cycle_id,
            ticker,
            side,
            quantity,
            status,
            created_at,
            filled_at,
            fill_price,
            price_source,
            validated,
            simulated,
            reason,
            policy,
            recommendation_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order.get("order_id"),
            order.get("cycle_id"),
            order.get("ticker"),
            order.get("side"),
            order.get("quantity"),
            order.get("status"),
            order.get("created_at"),
            order.get("filled_at"),
            order.get("fill_price"),
            order.get("price_source"),
            1 if order.get("validated") else 0,
            1 if order.get("simulated", True) else 0,
            order.get("reason", ""),
            json.dumps(order.get("policy", {})),
            recommendation_id,
        )
    )
    connection.commit()
    connection.close()


def get_paper_fund_orders(limit=100):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT order_id, cycle_id, ticker, side, quantity, status, created_at,
               filled_at, fill_price, price_source, validated, simulated,
               reason, policy
        FROM paper_fund_orders
        ORDER BY created_at DESC, order_id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "order_id": row[0],
            "cycle_id": row[1],
            "ticker": row[2],
            "side": row[3],
            "quantity": row[4],
            "status": row[5],
            "created_at": row[6],
            "filled_at": row[7],
            "fill_price": row[8],
            "price_source": row[9],
            "validated": bool(row[10]),
            "simulated": bool(row[11]),
            "reason": row[12],
            "policy": json.loads(row[13] or "{}"),
        }
        for row in rows
    ]


def save_risk_decision(decision):
    decision_id = decision.get("decision_id")
    if not decision_id:
        raise ValueError("risk decision_id is required")

    order = decision.get("order", {}) or {}
    symbol = decision.get("symbol") or order.get("symbol") or order.get("ticker")
    side = decision.get("side") or order.get("side") or order.get("action")
    quantity = decision.get("quantity", order.get("quantity"))
    verdict = decision.get("verdict") or decision.get("status")

    if not symbol:
        raise ValueError("risk decision symbol is required")
    if not side:
        raise ValueError("risk decision side is required")
    if quantity is None:
        raise ValueError("risk decision quantity is required")
    if not verdict:
        raise ValueError("risk decision verdict is required")

    checks = decision.get("checks")
    if checks is None:
        checks = {
            "checks": decision.get("check_report", []),
            "rejections": decision.get("rejections", []),
            "reasons": decision.get("reasons", []),
        }

    policy = decision.get("policy")
    if policy is None:
        policy = {
            "paper_only": decision.get("paper_only"),
            "broker_integration": decision.get("broker_integration"),
            "real_money": decision.get("real_money"),
            "human_approval_required_for_real_trading": decision.get(
                "human_approval_required_for_real_trading"
            ),
        }

    created_at = decision.get("created_at") or datetime.now().isoformat()

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO risk_decisions (
            decision_id,
            cycle_id,
            run_id,
            symbol,
            side,
            quantity,
            verdict,
            checks,
            policy,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            decision_id,
            decision.get("cycle_id"),
            decision.get("run_id"),
            symbol,
            side,
            quantity,
            verdict,
            json.dumps(checks),
            json.dumps(policy),
            created_at,
        ),
    )
    connection.commit()
    connection.close()

    return decision_id


def get_recent_risk_decisions(limit=100):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT decision_id, cycle_id, run_id, symbol, side, quantity, verdict,
               checks, policy, created_at
        FROM risk_decisions
        ORDER BY created_at DESC, decision_id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    connection.close()

    return [_risk_decision_row(row) for row in rows]


def _risk_decision_row(row):
    return {
        "decision_id": row[0],
        "cycle_id": row[1],
        "run_id": row[2],
        "symbol": row[3],
        "side": row[4],
        "quantity": row[5],
        "verdict": row[6],
        "checks": json.loads(row[7] or "{}"),
        "policy": json.loads(row[8] or "{}"),
        "created_at": row[9],
    }


def save_paper_fund_snapshot(snapshot):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO paper_fund_snapshots (
            as_of,
            cycle_id,
            cash,
            positions,
            current_value,
            realized_pl,
            unrealized_pl,
            portfolio_value,
            daily_return,
            total_return,
            price_source,
            policy
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot.get("as_of"),
            snapshot.get("cycle_id"),
            snapshot.get("cash"),
            json.dumps(snapshot.get("positions", {})),
            snapshot.get("current_value"),
            snapshot.get("realized_pl"),
            snapshot.get("unrealized_pl"),
            snapshot.get("portfolio_value"),
            snapshot.get("daily_return"),
            snapshot.get("total_return"),
            snapshot.get("price_source"),
            json.dumps(snapshot.get("policy", {})),
        )
    )
    connection.commit()
    connection.close()


def get_paper_fund_snapshots(limit=100):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT as_of, cycle_id, cash, positions, current_value, realized_pl,
               unrealized_pl, portfolio_value, daily_return, total_return,
               price_source, policy
        FROM paper_fund_snapshots
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "as_of": row[0],
            "date": row[0],
            "cycle_id": row[1],
            "cash": row[2],
            "positions": json.loads(row[3] or "{}"),
            "current_value": row[4],
            "realized_pl": row[5],
            "unrealized_pl": row[6],
            "portfolio_value": row[7],
            "daily_return": row[8],
            "total_return": row[9],
            "price_source": row[10],
            "policy": json.loads(row[11] or "{}"),
        }
        for row in rows
    ]


def add_paper_fund_activity(entry):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO paper_fund_activity (at, cycle_id, activity_type, message, details)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            entry.get("at"),
            entry.get("cycle_id"),
            entry.get("activity_type"),
            entry.get("message"),
            json.dumps(entry.get("details", {})),
        )
    )
    connection.commit()
    connection.close()


def get_paper_fund_activity(limit=100):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT at, cycle_id, activity_type, message, details
        FROM paper_fund_activity
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "at": row[0],
            "cycle_id": row[1],
            "activity_type": row[2],
            "message": row[3],
            "details": json.loads(row[4] or "{}"),
        }
        for row in rows
    ]


def get_latest_paper_fund_activity(activity_type=None):
    """Newest activity row, optionally restricted to one exact type."""
    connection = get_connection()
    try:
        if activity_type:
            row = connection.execute(
                "SELECT at, cycle_id, activity_type, message, details "
                "FROM paper_fund_activity WHERE activity_type = ? "
                "ORDER BY id DESC LIMIT 1",
                (activity_type,),
            ).fetchone()
        else:
            row = connection.execute(
                "SELECT at, cycle_id, activity_type, message, details "
                "FROM paper_fund_activity ORDER BY id DESC LIMIT 1"
            ).fetchone()
    finally:
        connection.close()
    if row is None:
        return None
    return {
        "at": row[0],
        "cycle_id": row[1],
        "activity_type": row[2],
        "message": row[3],
        "details": json.loads(row[4] or "{}"),
    }


def add_paper_fund_learning(entry):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO paper_fund_learning (at, cycle_id, lesson, details)
        VALUES (?, ?, ?, ?)
        """,
        (
            entry.get("at"),
            entry.get("cycle_id"),
            entry.get("lesson"),
            json.dumps(entry.get("details", {})),
        )
    )
    connection.commit()
    connection.close()


def get_paper_fund_learning(limit=100):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT at, cycle_id, lesson, details
        FROM paper_fund_learning
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "at": row[0],
            "cycle_id": row[1],
            "lesson": row[2],
            "details": json.loads(row[3] or "{}"),
        }
        for row in rows
    ]


SCHEDULER_TICKS_MAX_ROWS = 2000


def add_scheduler_tick(entry):
    """Append one scheduler tick outcome and prune the table to a bounded size.

    Every tick is recorded — ran, skipped, or errored — so a skipped cycle
    always persists WHY. Pruning keeps the newest SCHEDULER_TICKS_MAX_ROWS
    rows (about one week at the default 5-minute interval).
    """
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO scheduler_ticks (at, status, reason, stages, duration_seconds)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            entry.get("at"),
            entry.get("status"),
            entry.get("reason"),
            json.dumps(entry.get("stages", [])),
            entry.get("duration_seconds"),
        )
    )
    cursor.execute(
        """
        DELETE FROM scheduler_ticks
        WHERE id NOT IN (
            SELECT id FROM scheduler_ticks ORDER BY id DESC LIMIT ?
        )
        """,
        (SCHEDULER_TICKS_MAX_ROWS,),
    )
    connection.commit()
    connection.close()


def get_scheduler_ticks(limit=100):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT at, status, reason, stages, duration_seconds
            FROM scheduler_ticks
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
    except Exception as error:
        connection.close()
        if "no such table" in str(error).lower():
            return []
        raise
    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "at": row[0],
            "status": row[1],
            "reason": row[2],
            "stages": json.loads(row[3] or "[]"),
            "duration_seconds": row[4],
        }
        for row in rows
    ]


def get_latest_scheduler_tick():
    ticks = get_scheduler_ticks(limit=1)

    return ticks[0] if ticks else None


def save_research_cycle_record(record):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO research_cycle_records (
            cycle_id, generated_at, status, reason, stages, fund_cycle_id, policy
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.get("cycle_id"),
            record.get("generated_at"),
            record.get("status"),
            record.get("reason"),
            json.dumps(record.get("stages", [])),
            record.get("fund_cycle_id"),
            json.dumps(record.get("policy", {})),
        )
    )
    connection.commit()
    connection.close()


def get_research_cycle_records(limit=50):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT cycle_id, generated_at, status, reason, stages,
                   fund_cycle_id, policy
            FROM research_cycle_records
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
    except Exception as error:
        connection.close()
        if "no such table" in str(error).lower():
            return []
        raise
    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "cycle_id": row[0],
            "generated_at": row[1],
            "status": row[2],
            "reason": row[3],
            "stages": json.loads(row[4] or "[]"),
            "fund_cycle_id": row[5],
            "policy": json.loads(row[6] or "{}"),
        }
        for row in rows
    ]


def save_committee_cycle_evaluations(entry):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO committee_cycle_evaluations (
            cycle_id, run_id, evaluated_at, evaluations, duration_seconds
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            entry.get("cycle_id"),
            entry.get("run_id"),
            entry.get("evaluated_at"),
            json.dumps(entry.get("evaluations", [])),
            entry.get("duration_seconds"),
        )
    )
    connection.commit()
    connection.close()


def get_committee_cycle_evaluations(limit=50):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT cycle_id, run_id, evaluated_at, evaluations, duration_seconds
            FROM committee_cycle_evaluations
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
    except Exception as error:
        connection.close()
        if "no such table" in str(error).lower():
            return []
        raise
    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "cycle_id": row[0],
            "run_id": row[1],
            "evaluated_at": row[2],
            "evaluations": json.loads(row[3] or "[]"),
            "duration_seconds": row[4],
        }
        for row in rows
    ]


def save_cycle_performance_record(record):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO cycle_performance_records (cycle_id, as_of, report, policy)
        VALUES (?, ?, ?, ?)
        """,
        (
            record.get("cycle_id"),
            record.get("as_of"),
            json.dumps(record.get("report", {})),
            json.dumps(record.get("policy", {})),
        )
    )
    connection.commit()
    connection.close()


def get_cycle_performance_records(limit=50):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT cycle_id, as_of, report, policy
            FROM cycle_performance_records
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
    except Exception as error:
        connection.close()
        if "no such table" in str(error).lower():
            return []
        raise
    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "cycle_id": row[0],
            "as_of": row[1],
            "report": json.loads(row[2] or "{}"),
            "policy": json.loads(row[3] or "{}"),
        }
        for row in rows
    ]


def save_self_improvement_report(report, cycle_id=None):
    """Persist a Self-Improvement report as advisory research evidence.

    Findings are research opportunities only; nothing reads them back to
    change strategies, weights, risk limits, or trading behavior.
    """
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO self_improvement_reports (
            cycle_id, generated_at, status, headline, findings,
            opportunities, not_evaluated, source_counts, policy
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cycle_id,
            report.get("generated_at"),
            report.get("status"),
            report.get("headline"),
            json.dumps(report.get("findings", [])),
            json.dumps(report.get("opportunities", [])),
            json.dumps(report.get("not_evaluated", [])),
            json.dumps(report.get("source_counts", {})),
            json.dumps(report.get("policy", {})),
        )
    )
    connection.commit()
    connection.close()


def get_self_improvement_reports(limit=50):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT cycle_id, generated_at, status, headline, findings,
                   opportunities, not_evaluated, source_counts, policy
            FROM self_improvement_reports
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
    except Exception as error:
        connection.close()
        if "no such table" in str(error).lower():
            return []
        raise
    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "cycle_id": row[0],
            "generated_at": row[1],
            "status": row[2],
            "headline": row[3],
            "findings": json.loads(row[4] or "[]"),
            "opportunities": json.loads(row[5] or "[]"),
            "not_evaluated": json.loads(row[6] or "[]"),
            "source_counts": json.loads(row[7] or "{}"),
            "policy": json.loads(row[8] or "{}"),
        }
        for row in rows
    ]


def get_latest_self_improvement_report():
    reports = get_self_improvement_reports(limit=1)

    return reports[0] if reports else None


def reset_paper_fund_data():
    connection = get_connection()
    cursor = connection.cursor()
    cleared = []

    for table_name in [
        "paper_fund_states",
        "paper_fund_orders",
        "paper_fund_snapshots",
        "paper_fund_activity",
        "paper_fund_learning",
    ]:
        try:
            cursor.execute(f"DELETE FROM {table_name}")
            cleared.append(table_name)
        except Exception as error:
            if "no such table" not in str(error).lower():
                connection.close()
                raise

    connection.commit()
    connection.close()

    return {"status": "RESET", "cleared_tables": cleared}


def save_daily_cycle_run(cycle):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO daily_cycle_runs (
            cycle_id,
            cycle_date,
            phase,
            status,
            recommendations_count,
            paper_portfolio_value,
            daily_return,
            alpha_vs_sp500,
            warnings,
            summary,
            details,
            policy
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cycle.get("cycle_id"),
            cycle.get("date"),
            cycle.get("phase"),
            cycle.get("status"),
            cycle.get("recommendations_count"),
            cycle.get("paper_portfolio_value"),
            cycle.get("daily_return"),
            cycle.get("alpha_vs_sp500"),
            json.dumps(cycle.get("warnings", [])),
            cycle.get("summary", ""),
            json.dumps(cycle.get("details", {})),
            json.dumps(cycle.get("policy", {})),
        )
    )

    connection.commit()
    connection.close()


def get_daily_cycle_runs(limit=50):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                cycle_id,
                cycle_date,
                phase,
                status,
                recommendations_count,
                paper_portfolio_value,
                daily_return,
                alpha_vs_sp500,
                warnings,
                summary,
                details,
                policy
            FROM daily_cycle_runs
            ORDER BY cycle_date DESC, id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        connection.close()

        if "no such table" in str(error).lower():
            return []

        raise

    rows = cursor.fetchall()
    connection.close()

    return [_daily_cycle_row(row) for row in rows]


def get_latest_daily_cycle_run():
    runs = get_daily_cycle_runs(limit=1)

    return runs[0] if runs else None


def save_daily_journal(journal):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO daily_journals (
            journal_id,
            journal_date,
            market_regime,
            runtime_state,
            paper_portfolio_summary,
            benchmark_comparison,
            provider_health,
            macro_summary,
            catalyst_summary,
            recommendation_summary,
            performance_summary,
            lessons_learned,
            research_tasks,
            policy
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            journal.get("journal_id"),
            journal.get("date"),
            journal.get("market_regime"),
            json.dumps(journal.get("runtime_state", {})),
            json.dumps(journal.get("paper_portfolio_summary", {})),
            json.dumps(journal.get("benchmark_comparison", [])),
            json.dumps(journal.get("provider_health", {})),
            json.dumps(journal.get("macro_summary", {})),
            json.dumps(journal.get("catalyst_summary", {})),
            json.dumps(journal.get("recommendation_summary", {})),
            json.dumps(journal.get("performance_summary", {})),
            json.dumps(journal.get("lessons_learned", {})),
            json.dumps(journal.get("research_tasks", [])),
            json.dumps(journal.get("policy", {})),
        )
    )

    connection.commit()
    connection.close()


def get_daily_journals(limit=50):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                journal_id,
                journal_date,
                market_regime,
                runtime_state,
                paper_portfolio_summary,
                benchmark_comparison,
                provider_health,
                macro_summary,
                catalyst_summary,
                recommendation_summary,
                performance_summary,
                lessons_learned,
                research_tasks,
                policy
            FROM daily_journals
            ORDER BY journal_date DESC, journal_id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        connection.close()

        if "no such table" in str(error).lower():
            return []

        raise

    rows = cursor.fetchall()
    connection.close()

    return [_daily_journal_row(row) for row in rows]


def get_latest_daily_journal():
    journals = get_daily_journals(limit=1)

    return journals[0] if journals else None


def save_portfolio_construction_report(report):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO portfolio_construction_reports (
            report_date,
            recommended_allocations,
            portfolio_actions,
            risk_summary,
            risk_budget,
            diversification,
            constraints_json,
            scenario_analysis,
            scientific_validation,
            operations_summary,
            policy
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().date().isoformat(),
            json.dumps(report.get("recommended_allocations", [])),
            json.dumps(report.get("portfolio_actions", [])),
            json.dumps(report.get("risk_summary", {})),
            json.dumps(report.get("risk_budget", {})),
            json.dumps(report.get("diversification", {})),
            json.dumps(report.get("constraints", {})),
            json.dumps(report.get("scenario_analysis", [])),
            json.dumps(report.get("scientific_validation", {})),
            json.dumps(report.get("operations_summary", {})),
            json.dumps(report.get("policy", {})),
        )
    )

    connection.commit()
    connection.close()


def get_portfolio_construction_reports(limit=50):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                report_date,
                recommended_allocations,
                portfolio_actions,
                risk_summary,
                risk_budget,
                diversification,
                constraints_json,
                scenario_analysis,
                scientific_validation,
                operations_summary,
                policy
            FROM portfolio_construction_reports
            ORDER BY report_date DESC, id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        connection.close()

        if "no such table" in str(error).lower():
            return []

        raise

    rows = cursor.fetchall()
    connection.close()

    return [_portfolio_construction_row(row) for row in rows]


def get_latest_portfolio_construction_report():
    reports = get_portfolio_construction_reports(limit=1)

    return reports[0] if reports else None


def save_runtime_state(state):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO runtime_states (
            runtime_id,
            current_state,
            market_date,
            market_phase,
            last_cycle_time,
            next_cycle,
            provider_health,
            paper_portfolio_value,
            active_watchlist_size,
            open_positions,
            recommendations_today,
            alerts,
            tasks,
            operations_summary,
            health,
            policy
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            state.get("runtime_id"),
            state.get("current_state"),
            state.get("market_date"),
            state.get("market_phase"),
            state.get("last_cycle_time"),
            json.dumps(state.get("next_cycle", {})),
            json.dumps(state.get("provider_health", {})),
            state.get("paper_portfolio_value"),
            state.get("active_watchlist_size"),
            state.get("open_positions"),
            state.get("recommendations_today"),
            json.dumps(state.get("alerts", [])),
            json.dumps(state.get("tasks", {})),
            json.dumps(state.get("operations_summary", {})),
            json.dumps(state.get("health", {})),
            json.dumps(state.get("policy", {})),
        )
    )

    connection.commit()
    connection.close()


def get_runtime_states(limit=20):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                runtime_id,
                current_state,
                market_date,
                market_phase,
                last_cycle_time,
                next_cycle,
                provider_health,
                paper_portfolio_value,
                active_watchlist_size,
                open_positions,
                recommendations_today,
                alerts,
                tasks,
                operations_summary,
                health,
                policy
            FROM runtime_states
            ORDER BY market_date DESC, id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        connection.close()

        if "no such table" in str(error).lower():
            return []

        raise

    rows = cursor.fetchall()
    connection.close()

    return [_runtime_state_row(row) for row in rows]


def get_latest_runtime_state():
    states = get_runtime_states(limit=1)

    return states[0] if states else None


def save_model_evaluations(evaluations):
    connection = get_connection()
    cursor = connection.cursor()

    for evaluation in evaluations:
        cursor.execute(
            """
            INSERT INTO model_evaluations (
                model_name,
                model_type,
                provider,
                dataset,
                date_range,
                validation_window,
                sample_size,
                accuracy,
                win_rate,
                average_return,
                sharpe_ratio,
                max_drawdown,
                runtime_placeholder,
                memory_placeholder,
                cost_placeholder,
                integration_difficulty,
                recommendation,
                overall_score,
                evaluation_date,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evaluation.get("model_name"),
                evaluation.get("model_type"),
                evaluation.get("provider"),
                evaluation.get("dataset"),
                json.dumps(evaluation.get("date_range", {})),
                evaluation.get("validation_window"),
                evaluation.get("sample_size"),
                evaluation.get("accuracy"),
                evaluation.get("win_rate"),
                evaluation.get("average_return"),
                evaluation.get("sharpe_ratio"),
                evaluation.get("max_drawdown"),
                evaluation.get("runtime_placeholder"),
                evaluation.get("memory_placeholder"),
                evaluation.get("cost_placeholder"),
                evaluation.get("integration_difficulty"),
                evaluation.get("recommendation"),
                evaluation.get("overall_score"),
                evaluation.get("evaluation_date"),
                evaluation.get("status"),
            )
        )

    connection.commit()
    connection.close()


def get_model_evaluations(limit=20):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                model_name,
                model_type,
                provider,
                dataset,
                date_range,
                validation_window,
                sample_size,
                accuracy,
                win_rate,
                average_return,
                sharpe_ratio,
                max_drawdown,
                runtime_placeholder,
                memory_placeholder,
                cost_placeholder,
                integration_difficulty,
                recommendation,
                overall_score,
                evaluation_date,
                status
            FROM model_evaluations
            ORDER BY overall_score DESC, accuracy DESC, id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        connection.close()

        if "no such table" in str(error).lower():
            return []

        raise

    rows = cursor.fetchall()
    connection.close()

    return [
        _model_evaluation_row(row) for row in rows
    ]


def save_discoveries(discoveries):
    connection = get_connection()
    cursor = connection.cursor()

    for discovery in discoveries:
        cursor.execute(
            """
            INSERT OR REPLACE INTO discoveries (
                id,
                title,
                description,
                supporting_data,
                sample_size,
                confidence,
                importance,
                discovery_date,
                related_engines,
                related_providers,
                status,
                support_level,
                warnings,
                suggestions
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                discovery.get("id"),
                discovery.get("title"),
                discovery.get("description"),
                json.dumps(discovery.get("supporting_data", {})),
                discovery.get("sample_size"),
                discovery.get("confidence"),
                discovery.get("importance"),
                discovery.get("date"),
                json.dumps(discovery.get("related_engines", [])),
                json.dumps(discovery.get("related_providers", [])),
                discovery.get("status"),
                discovery.get("support_level"),
                json.dumps(discovery.get("warnings", [])),
                json.dumps(discovery.get("suggestions", [])),
            )
        )

    connection.commit()
    connection.close()


def get_discovery_dashboard_data(limit=10):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            title,
            description,
            supporting_data,
            sample_size,
            confidence,
            importance,
            discovery_date,
            related_engines,
            related_providers,
            status,
            support_level,
            warnings,
            suggestions
        FROM discoveries
        ORDER BY discovery_date DESC, importance DESC, confidence DESC
        LIMIT ?
        """,
        (limit,)
    )
    recent_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            id,
            title,
            confidence,
            importance,
            support_level,
            suggestions
        FROM discoveries
        ORDER BY importance DESC, confidence DESC
        LIMIT ?
        """,
        (limit,)
    )
    top_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            id,
            title,
            confidence,
            importance,
            support_level,
            suggestions
        FROM discoveries
        ORDER BY confidence DESC, importance DESC
        LIMIT ?
        """,
        (limit,)
    )
    confidence_rows = cursor.fetchall()
    connection.close()

    return {
        "recent_discoveries": [
            _discovery_row(row) for row in recent_rows
        ],
        "top_discoveries": [
            _compact_discovery_row(row) for row in top_rows
        ],
        "highest_confidence_discoveries": [
            _compact_discovery_row(row) for row in confidence_rows
        ],
        "discovery_history": [
            _discovery_row(row) for row in recent_rows
        ],
    }


def save_historical_validation_run(result):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO historical_validation_runs (
            experiment_id,
            run_date,
            configuration,
            metrics,
            comparison,
            statistics,
            report
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result.get("experiment_id"),
            result.get("run_date"),
            json.dumps(result.get("configuration", {})),
            json.dumps(result.get("metrics", {})),
            json.dumps(result.get("comparison", [])),
            json.dumps(result.get("statistics", {})),
            result.get("report", ""),
        )
    )

    connection.commit()
    connection.close()


def get_historical_validation_runs(limit=10):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                experiment_id,
                run_date,
                configuration,
                metrics,
                comparison,
                statistics,
                report
            FROM historical_validation_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        connection.close()

        if "no such table" in str(error).lower():
            return []

        raise

    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "id": row[0],
            "experiment_id": row[1],
            "run_date": row[2],
            "configuration": json.loads(row[3] or "{}"),
            "metrics": json.loads(row[4] or "{}"),
            "comparison": json.loads(row[5] or "[]"),
            "statistics": json.loads(row[6] or "{}"),
            "report": row[7] or "",
        }
        for row in rows
    ]


def get_validation_results_for_recommendations(recommendation_ids):
    if not recommendation_ids:
        return {}

    connection = get_connection()
    cursor = connection.cursor()
    placeholders = ", ".join(["?"] * len(recommendation_ids))

    cursor.execute(
        f"""
        SELECT
            id,
            recommendation_id,
            ticker,
            recommendation,
            recommendation_timestamp,
            evaluation_timestamp,
            holding_period,
            starting_price,
            ending_price,
            percentage_return,
            predicted_direction,
            actual_direction,
            success,
            status,
            notes
        FROM recommendation_validations
        WHERE recommendation_id IN ({placeholders})
        ORDER BY id ASC
        """,
        recommendation_ids
    )

    rows = cursor.fetchall()
    connection.close()
    results = {}

    for row in rows:
        results[row[1]] = {
            "id": row[0],
            "recommendation_id": row[1],
            "ticker": row[2],
            "recommendation": row[3],
            "recommendation_timestamp": row[4],
            "evaluation_timestamp": row[5],
            "holding_period": row[6],
            "starting_price": row[7],
            "ending_price": row[8],
            "percentage_return": row[9],
            "predicted_direction": row[10],
            "actual_direction": row[11],
            "success": _int_to_bool(row[12]),
            "hit": _int_to_bool(row[12]),
            "status": row[13] or "Pending",
            "notes": row[14] or "",
        }

    return results


def _bool_to_int(value):
    if value is None:
        return None

    return 1 if value else 0


def _int_to_bool(value):
    if value is None:
        return None

    return bool(value)


def _discovery_row(row):
    return {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "supporting_data": json.loads(row[3] or "{}"),
        "sample_size": row[4],
        "confidence": row[5],
        "importance": row[6],
        "date": row[7],
        "related_engines": json.loads(row[8] or "[]"),
        "related_providers": json.loads(row[9] or "[]"),
        "status": row[10],
        "support_level": row[11],
        "warnings": json.loads(row[12] or "[]"),
        "suggestions": json.loads(row[13] or "[]"),
    }


def _compact_discovery_row(row):
    return {
        "id": row[0],
        "title": row[1],
        "confidence": row[2],
        "importance": row[3],
        "support_level": row[4],
        "suggestions": json.loads(row[5] or "[]"),
    }


def _model_evaluation_row(row):
    return {
        "model_name": row[0],
        "model_type": row[1],
        "provider": row[2],
        "dataset": row[3],
        "date_range": json.loads(row[4] or "{}"),
        "validation_window": row[5],
        "sample_size": row[6],
        "accuracy": row[7],
        "win_rate": row[8],
        "average_return": row[9],
        "sharpe_ratio": row[10],
        "max_drawdown": row[11],
        "runtime_placeholder": row[12],
        "memory_placeholder": row[13],
        "cost_placeholder": row[14],
        "integration_difficulty": row[15],
        "recommendation": row[16],
        "overall_score": row[17],
        "evaluation_date": row[18],
        "status": row[19],
    }


def _case_study_row(row):
    return {
        "case_id": row[0],
        "ticker": row[1],
        "recommendation": row[2],
        "market_regime": row[3],
        "evidence": json.loads(row[4] or "[]"),
        "committee": json.loads(row[5] or "{}"),
        "executive_review": json.loads(row[6] or "{}"),
        "knowledge_score": row[7] or 0,
        "stability_score": row[8] or 0,
        "outcome": row[9],
        "return": row[10] or 0,
        "holding_period": row[11] or 0,
        "validation": json.loads(row[12] or "{}"),
        "benchmark": json.loads(row[13] or "{}"),
        "hypotheses": json.loads(row[14] or "[]"),
        "counterfactuals": json.loads(row[15] or "[]"),
        "lessons_learned": json.loads(row[16] or "{}"),
        "catalysts": json.loads(row[17] or "[]") if len(row) > 19 else [],
        "probability_report": (
            json.loads(row[18] or "{}") if len(row) > 19 else {}
        ),
        "case_date": row[19] if len(row) > 19 else row[17],
    }


def _probability_report_row(row):
    return {
        "recommendation_id": row[0],
        "ticker": row[1],
        "recommendation": row[2],
        "probabilities": json.loads(row[3] or "{}"),
        "expected_outcome": json.loads(row[4] or "{}"),
        "confidence_quality": json.loads(row[5] or "{}"),
        "similar_historical_cases": json.loads(row[6] or "[]"),
        "explanation": row[7] or "",
        "report_date": row[8],
    }


def _scientific_validation_row(row):
    return {
        "experiment_id": row[0],
        "date": row[1],
        "feature_tested": row[2],
        "baseline": json.loads(row[3] or "{}"),
        "candidate": json.loads(row[4] or "{}"),
        "sample_size": row[5] or 0,
        "metric_comparison": json.loads(row[6] or "[]"),
        "cross_regime_validation": json.loads(row[7] or "[]"),
        "generalization_tests": json.loads(row[8] or "[]"),
        "scientific_result": row[9],
        "adoption_decision": row[10],
        "adoption_explanation": row[11] or "",
        "policy": json.loads(row[12] or "{}"),
    }


def _simulation_arena_row(row):
    return {
        "arena_id": row[0],
        "date": row[1],
        "dataset": row[2],
        "tickers": json.loads(row[3] or "[]"),
        "date_range": json.loads(row[4] or "{}"),
        "validation_window": row[5],
        "strategy_configs": json.loads(row[6] or "[]"),
        "market_regimes_tested": json.loads(row[7] or "[]"),
        "results": json.loads(row[8] or "[]"),
        "comparison": json.loads(row[9] or "{}"),
        "scientific_validation": json.loads(row[10] or "{}"),
        "policy": json.loads(row[11] or "{}"),
    }


def _market_data_snapshot_row(row):
    return {
        "snapshot_date": row[0],
        "provider": row[1],
        "requested_provider": row[2],
        "fallback_used": _int_to_bool(row[3]),
        "validated": _int_to_bool(row[4]),
        "ticker_count": row[5] or 0,
        "prices": json.loads(row[6] or "{}"),
        "market_status": json.loads(row[7] or "{}"),
        "policy": json.loads(row[8] or "{}"),
    }


def _monthly_report_row(row):
    return {
        "month": row[0],
        "report_date": row[1],
        "performance": json.loads(row[2] or "{}"),
        "major_lessons": json.loads(row[3] or "[]"),
        "best_decisions": json.loads(row[4] or "[]"),
        "largest_mistakes": json.loads(row[5] or "[]"),
        "research_progress": json.loads(row[6] or "{}"),
        "validation_summary": json.loads(row[7] or "{}"),
        "policy": json.loads(row[8] or "{}"),
    }


def _registry_experiment_row(row):
    return {
        "experiment_id": row[0],
        "title": row[1],
        "description": row[2],
        "status": row[3],
        "created_date": row[4],
        "author": row[5],
        "feature_being_tested": row[6],
        "baseline_strategy": row[7],
        "candidate_strategy": row[8],
        "validation_state": row[9],
        "priority": row[10],
        "notes": row[11] or "",
        "adoption_decision": row[12] or "RETEST",
        "arena_metrics": json.loads(row[13] or "{}"),
        "policy": json.loads(row[14] or "{}"),
    }


def _paper_portfolio_row(row):
    policy = json.loads(row[10] or "{}")
    return {
        "id": row[0],
        "date": row[1],
        "cash": row[2] or 0,
        "positions": json.loads(row[3] or "{}"),
        "current_value": row[4] or 0,
        "realized_pl": row[5] or 0,
        "unrealized_pl": row[6] or 0,
        "portfolio_value": row[7] or 0,
        "daily_return": row[8] or 0,
        "total_return": row[9] or 0,
        "run_id": policy.get("run_id"),
        "run_number": policy.get("run_number"),
        "replay_day": policy.get("replay_day"),
        "simulated_at": policy.get("simulated_at"),
        "mode": policy.get("mode"),
        "data_source": policy.get("data_source"),
        "policy": policy,
    }


def _paper_trade_row(row):
    recommendation_snapshot = json.loads(row[11] or "{}")
    metadata = recommendation_snapshot.get("run_metadata", {})
    execution = recommendation_snapshot.get("execution", {})
    return {
        "trade_id": row[0],
        "ticker": row[1],
        "action": row[2],
        "entry_date": row[3],
        "entry_price": row[4],
        "exit_date": row[5],
        "exit_price": row[6],
        "holding_period": row[7],
        "quantity": row[8],
        "profit_loss": row[9] or 0,
        "transaction_cost": execution.get("transaction_cost", 0),
        "slippage": execution.get("slippage", 0),
        "reason": row[10] or "",
        "run_id": metadata.get("run_id"),
        "run_number": metadata.get("run_number"),
        "simulated_at": metadata.get("simulated_at"),
        "mode": metadata.get("mode"),
        "data_source": metadata.get("data_source"),
        "recommendation_snapshot": recommendation_snapshot,
    }


def _paper_performance_row(row):
    policy = json.loads(row[4] or "{}")
    return {
        "id": row[0],
        "date": row[1],
        "performance": json.loads(row[2] or "{}"),
        "research": json.loads(row[3] or "{}"),
        "run_id": policy.get("run_id"),
        "run_number": policy.get("run_number"),
        "simulated_at": policy.get("simulated_at"),
        "mode": policy.get("mode"),
        "data_source": policy.get("data_source"),
        "policy": policy,
    }


def _daily_cycle_row(row):
    return {
        "cycle_id": row[0],
        "date": row[1],
        "phase": row[2],
        "status": row[3],
        "recommendations_count": row[4] or 0,
        "paper_portfolio_value": row[5] or 0,
        "daily_return": row[6] or 0,
        "alpha_vs_sp500": row[7] or 0,
        "warnings": json.loads(row[8] or "[]"),
        "summary": row[9] or "",
        "details": json.loads(row[10] or "{}"),
        "policy": json.loads(row[11] or "{}"),
    }


def _daily_journal_row(row):
    return {
        "journal_id": row[0],
        "date": row[1],
        "market_regime": row[2],
        "runtime_state": json.loads(row[3] or "{}"),
        "paper_portfolio_summary": json.loads(row[4] or "{}"),
        "benchmark_comparison": json.loads(row[5] or "[]"),
        "provider_health": json.loads(row[6] or "{}"),
        "macro_summary": json.loads(row[7] or "{}"),
        "catalyst_summary": json.loads(row[8] or "{}"),
        "recommendation_summary": json.loads(row[9] or "{}"),
        "performance_summary": json.loads(row[10] or "{}"),
        "lessons_learned": json.loads(row[11] or "{}"),
        "research_tasks": json.loads(row[12] or "[]"),
        "policy": json.loads(row[13] or "{}"),
    }


def _portfolio_construction_row(row):
    return {
        "id": row[0],
        "date": row[1],
        "recommended_allocations": json.loads(row[2] or "[]"),
        "portfolio_actions": json.loads(row[3] or "[]"),
        "risk_summary": json.loads(row[4] or "{}"),
        "risk_budget": json.loads(row[5] or "{}"),
        "diversification": json.loads(row[6] or "{}"),
        "constraints": json.loads(row[7] or "{}"),
        "scenario_analysis": json.loads(row[8] or "[]"),
        "scientific_validation": json.loads(row[9] or "{}"),
        "operations_summary": json.loads(row[10] or "{}"),
        "policy": json.loads(row[11] or "{}"),
    }


def _runtime_state_row(row):
    return {
        "runtime_id": row[0],
        "current_state": row[1],
        "market_date": row[2],
        "market_phase": row[3],
        "last_cycle_time": row[4],
        "next_cycle": json.loads(row[5] or "{}"),
        "provider_health": json.loads(row[6] or "{}"),
        "paper_portfolio_value": row[7] or 0,
        "active_watchlist_size": row[8] or 0,
        "open_positions": row[9] or 0,
        "recommendations_today": row[10] or 0,
        "alerts": json.loads(row[11] or "[]"),
        "tasks": json.loads(row[12] or "{}"),
        "operations_summary": json.loads(row[13] or "{}"),
        "health": json.loads(row[14] or "{}"),
        "policy": json.loads(row[15] or "{}"),
    }


def _paper_portfolio_rows(cursor, limit):
    try:
        cursor.execute(
            """
            SELECT
                id,
                snapshot_date,
                cash,
                positions,
                current_value,
                realized_pl,
                unrealized_pl,
                portfolio_value,
                daily_return,
                total_return,
                policy
            FROM paper_portfolio_snapshots
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        if "no such table" in str(error).lower():
            return []
        raise

    return cursor.fetchall()


def _paper_trade_rows(cursor, limit):
    try:
        cursor.execute(
            """
            SELECT
                trade_id,
                ticker,
                action,
                entry_date,
                entry_price,
                exit_date,
                exit_price,
                holding_period,
                quantity,
                profit_loss,
                reason,
                recommendation_snapshot
            FROM paper_trades
            ORDER BY COALESCE(exit_date, entry_date) DESC, trade_id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        if "no such table" in str(error).lower():
            return []
        raise

    return cursor.fetchall()


def _paper_performance_rows(cursor, limit):
    try:
        cursor.execute(
            """
            SELECT
                id,
                report_date,
                performance,
                research,
                policy
            FROM paper_performance_reports
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        if "no such table" in str(error).lower():
            return []
        raise

    return cursor.fetchall()


def _portfolio_construction_rows(cursor, limit):
    try:
        cursor.execute(
            """
            SELECT
                id,
                report_date,
                recommended_allocations,
                portfolio_actions,
                risk_summary,
                risk_budget,
                diversification,
                constraints_json,
                scenario_analysis,
                scientific_validation,
                operations_summary,
                policy
            FROM portfolio_construction_reports
            ORDER BY report_date DESC, id DESC
            LIMIT ?
            """,
            (limit,)
        )
    except Exception as error:
        if "no such table" in str(error).lower():
            return []
        raise

    return cursor.fetchall()


def _recommendation_metrics(recommendations, validation_results):
    total = len(recommendations)
    successful = 0
    failed = 0
    pending = 0
    returns = []

    for recommendation in recommendations:
        validation = validation_results.get(recommendation["id"])
        status = recommendation["validation_status"]

        if validation is not None:
            status = validation["status"]

            if validation["percentage_return"] is not None:
                returns.append(validation["percentage_return"])

        if status == "Succeeded":
            successful += 1
        elif status == "Failed":
            failed += 1
        else:
            pending += 1

    completed = successful + failed
    hit_rate = round(successful / completed * 100, 2) if completed else 0

    return {
        "total": total,
        "pending": pending,
        "successful": successful,
        "failed": failed,
        "hit_rate": hit_rate,
        "average_return": _average(returns),
    }


def _evidence_metrics(recommendations):
    return {
        "technical": _average_score(recommendations, "technical_score"),
        "fundamentals": _average_score(recommendations, "fundamental_score"),
        "forecast": _average_score(recommendations, "forecast_score"),
        "news": _average_score(recommendations, "news_confidence"),
        "portfolio": _average_score(recommendations, "portfolio_score"),
        "risk": _average_score(recommendations, "risk_score"),
    }


def _latest_recommendation(recommendations, validation_results):
    if not recommendations:
        return None

    recommendation = recommendations[0]
    validation = validation_results.get(recommendation["id"])
    status = recommendation["validation_status"]

    if validation is not None:
        status = validation["status"]

    return {
        "ticker": recommendation["ticker"],
        "action": recommendation["action"],
        "confidence": recommendation["confidence"],
        "signal_quality_score": recommendation["signal_quality_score"],
        "validation_status": status,
    }


def _average_score(items, key):
    return _average([item[key] for item in items])


def _average(values):
    if not values:
        return 0

    return round(sum(values) / len(values), 2)


def get_portfolio_snapshot(run_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            cash,
            portfolio_value,
            position_count,
            risk_level,
            cash_percentage
        FROM portfolio_snapshots
        WHERE run_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (run_id,)
    )

    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None

    return {
        "cash": row[0],
        "portfolio_value": row[1],
        "position_count": row[2],
        "risk_level": row[3],
        "cash_percentage": row[4],
    }
