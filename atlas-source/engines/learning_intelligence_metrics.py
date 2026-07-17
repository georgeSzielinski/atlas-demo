"""Pure, deterministic metrics shared by Learning Intelligence surfaces."""

from collections import Counter, OrderedDict
from statistics import median
import math

from engines.recommendation_intelligence_engine import normalize_confidence


COMPLETED_STATUSES = {"Succeeded", "Failed", "Expired"}
SCORED_STATUSES = {"Succeeded", "Failed"}
HORIZONS = (7, 30, 90, 180, 365)
CONFIDENCE_BUCKETS = ((0, 49), (50, 59), (60, 69), (70, 79), (80, 89), (90, 100))
MINIMUM_SAMPLE = 20

_STATUS_MAP = {
    "succeeded": "Succeeded",
    "correct": "Succeeded",
    "failed": "Failed",
    "incorrect": "Failed",
    "pending": "Pending",
    "deferred": "Deferred",
    "expired": "Expired",
}


def rate(numerator, denominator):
    return None if denominator == 0 else round(numerator / denominator * 100, 2)


def average(values):
    values = list(values)
    return None if not values else round(sum(values) / len(values), 2)


def finite_number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def normalized_status(value):
    if not isinstance(value, str):
        return None
    return _STATUS_MAP.get(value.strip().lower())


def normalized_horizon(value):
    if isinstance(value, bool):
        return None
    try:
        horizon = int(value)
    except (TypeError, ValueError):
        return None
    return horizon if horizon > 0 else None


def _text(value):
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _evidence_context(value):
    if not isinstance(value, list):
        return (), {}, None
    names = []
    confidences = {}
    weighted = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _text(item.get("category") or item.get("engine") or item.get("name"))
        if not name or name in names:
            continue
        names.append(name)
        confidence = normalize_confidence(item.get("confidence"))
        if confidence is not None:
            confidences[name] = confidence
        weight = finite_number(item.get("weight"))
        if weight is not None:
            weighted.append((weight, name))
    primary = sorted(weighted, key=lambda item: (-item[0], item[1]))[0][1] if weighted else None
    return tuple(names), confidences, primary


def normalize_records(records):
    """Normalize and de-duplicate a joined projection without mutating input."""
    recommendations = OrderedDict()
    outcomes = []
    seen_outcomes = set()

    for raw in records if isinstance(records, list) else []:
        if not isinstance(raw, dict):
            continue
        recommendation_id = raw.get("recommendation_id")
        if recommendation_id is None or isinstance(recommendation_id, bool):
            continue
        engines, engine_confidence, primary_engine = _evidence_context(
            raw.get("evidence_breakdown")
        )
        members = raw.get("committee_members")
        committee_proven = bool(isinstance(members, list) and members) or finite_number(
            raw.get("committee_agreement")
        ) is not None
        recommendation = recommendations.setdefault(
            recommendation_id,
            {
                "recommendation_id": recommendation_id,
                "run_id": raw.get("run_id"),
                "ticker": _text(raw.get("ticker")),
                "action": _text(raw.get("action")),
                "confidence": normalize_confidence(raw.get("confidence")),
                "recommendation_at": _text(raw.get("recommendation_at")),
                "entry_at": _text(raw.get("entry_at")),
                "outcome_state": normalized_status(raw.get("outcome_state")),
                "committee_names": ("Investment Committee",) if committee_proven else (),
                "committee_agreement": finite_number(raw.get("committee_agreement")),
                "engine_names": engines,
                "engine_confidence": engine_confidence,
                "primary_engine": primary_engine,
                "market_regime": _text(raw.get("market_regime")),
                "sector": _text(raw.get("sector")),
                "signals": {
                    "Forecast direction": _text(raw.get("forecast_direction")),
                    "News sentiment": _text(raw.get("news_sentiment")),
                    "Signal label": _text(raw.get("signal_label")),
                },
            },
        )
        # Later joined horizons can fill optional context missing on the first row.
        if not recommendation["engine_names"] and engines:
            recommendation["engine_names"] = engines
            recommendation["engine_confidence"] = engine_confidence
            recommendation["primary_engine"] = primary_engine
        if not recommendation["committee_names"] and committee_proven:
            recommendation["committee_names"] = ("Investment Committee",)

        outcome_id = raw.get("outcome_id")
        if outcome_id is None:
            continue
        status = normalized_status(raw.get("status"))
        horizon = normalized_horizon(raw.get("horizon_days"))
        if status is None or horizon is None:
            continue
        identity = ("id", outcome_id)
        if identity in seen_outcomes:
            continue
        seen_outcomes.add(identity)
        outcomes.append({
            "outcome_id": outcome_id,
            "recommendation_id": recommendation_id,
            "ticker": recommendation["ticker"],
            "action": recommendation["action"],
            "confidence": recommendation["confidence"],
            "horizon_days": horizon,
            "evaluation_source": _text(raw.get("evaluation_source")),
            "status": status,
            "success": status == "Succeeded" if status in SCORED_STATUSES else None,
            "percentage_return": finite_number(raw.get("percentage_return")),
            "evaluation_at": _text(raw.get("evaluation_at")),
            "starting_price": finite_number(raw.get("starting_price")),
            "ending_price": finite_number(raw.get("ending_price")),
        })

    return {
        "recommendations": list(recommendations.values()),
        "outcomes": outcomes,
    }


def subset(dataset, recommendation_ids):
    ids = set(recommendation_ids)
    return {
        "recommendations": [
            row for row in dataset["recommendations"]
            if row["recommendation_id"] in ids
        ],
        "outcomes": [
            row for row in dataset["outcomes"]
            if row["recommendation_id"] in ids
        ],
    }


def group_metrics(dataset, rolling_window=20, confidence_key=None):
    recommendations = dataset["recommendations"]
    outcomes = dataset["outcomes"]
    scored = [row for row in outcomes if row["status"] in SCORED_STATUSES]
    completed = [row for row in outcomes if row["status"] in COMPLETED_STATUSES]
    rec_by_id = {row["recommendation_id"]: row for row in recommendations}

    def confidence_for(recommendation):
        if confidence_key is None:
            return recommendation.get("confidence")
        return recommendation.get("engine_confidence", {}).get(confidence_key)

    recommendation_confidences = [
        confidence_for(row) for row in recommendations
        if confidence_for(row) is not None
    ]
    evaluation_confidences = [
        confidence_for(rec_by_id[row["recommendation_id"]])
        for row in scored
        if confidence_for(rec_by_id[row["recommendation_id"]]) is not None
    ]
    observed_accuracy = rate(
        sum(row["status"] == "Succeeded" for row in scored), len(scored)
    )
    observed_confidence = average(evaluation_confidences)
    calibration_gap = (
        None if observed_accuracy is None or observed_confidence is None
        else round(observed_confidence - observed_accuracy, 2)
    )
    returns = [
        row["percentage_return"] for row in scored
        if row["percentage_return"] is not None
    ]
    completed_recommendations = {
        row["recommendation_id"] for row in completed
    }
    ordered_scored = sorted(
        scored,
        key=lambda row: (row.get("evaluation_at") or "", str(row.get("outcome_id"))),
    )

    return {
        "status": "EVALUATED" if recommendations else "NOT_EVALUATED",
        "recommendation_count": len(recommendations),
        "total_evaluations": len(outcomes),
        "completed_outcomes": len(completed),
        "pending": sum(row["status"] == "Pending" for row in outcomes),
        "deferred": sum(row["status"] == "Deferred" for row in outcomes),
        "expired": sum(row["status"] == "Expired" for row in outcomes),
        "accuracy": observed_accuracy,
        "accuracy_sample_size": len(scored),
        "accuracy_scope": "recommendation_horizon_evaluations",
        "multiple_horizons_weight_separately": True,
        "average_confidence": average(recommendation_confidences),
        "observed_confidence": observed_confidence,
        "observed_accuracy": observed_accuracy,
        "calibration_gap": calibration_gap,
        "calibration_state": calibration_state(calibration_gap, len(scored)),
        "average_return": average(returns),
        "median_return": None if not returns else round(median(returns), 2),
        "return_sample_size": len(returns),
        "best_recommendation": ranked_row(scored, reverse=True),
        "worst_recommendation": ranked_row(scored, reverse=False),
        "rolling_accuracy": rolling_accuracy(ordered_scored, rolling_window),
        "streaks": streaks(ordered_scored),
        "outcome_completion": rate(len(completed), len(outcomes)),
        "recommendation_coverage": rate(
            len(completed_recommendations), len(recommendations)
        ),
        "confidence_distribution": confidence_distribution(
            scored, rec_by_id, confidence_for
        ),
        "minimum_sample_warning": (
            "INSUFFICIENT_SAMPLE" if len(scored) < MINIMUM_SAMPLE else None
        ),
    }


def calibration_state(gap, sample_size):
    if gap is None:
        return "NO_DATA"
    if sample_size < MINIMUM_SAMPLE:
        return "INSUFFICIENT_SAMPLE"
    if gap > 0:
        return "OVERCONFIDENT"
    if gap < 0:
        return "UNDERCONFIDENT"
    return "CALIBRATED"


def ranked_row(rows, reverse):
    available = [row for row in rows if row["percentage_return"] is not None]
    if not available:
        return None
    row = sorted(
        available,
        key=lambda item: (
            item["percentage_return"],
            str(item.get("recommendation_id")),
            str(item.get("outcome_id")),
        ),
        reverse=reverse,
    )[0]
    return dict(row)


def rolling_accuracy(rows, window):
    safe_window = max(1, min(int(window), 500))
    points = []
    for index, row in enumerate(rows):
        sample = rows[max(0, index - safe_window + 1):index + 1]
        points.append({
            "evaluation_at": row.get("evaluation_at"),
            "outcome_id": row.get("outcome_id"),
            "window": safe_window,
            "sample_size": len(sample),
            "accuracy": rate(
                sum(item["status"] == "Succeeded" for item in sample), len(sample)
            ),
        })
    return points


def streaks(rows):
    longest_correct = longest_incorrect = current_count = 0
    current_state = "NO_DATA"
    previous = None
    run = 0
    for row in rows:
        state = "Correct" if row["status"] == "Succeeded" else "Incorrect"
        run = run + 1 if state == previous else 1
        previous = state
        if state == "Correct":
            longest_correct = max(longest_correct, run)
        else:
            longest_incorrect = max(longest_incorrect, run)
        current_state = state
        current_count = run
    return {
        "current": current_state,
        "current_count": current_count,
        "longest_correct": longest_correct,
        "longest_incorrect": longest_incorrect,
    }


def confidence_distribution(scored, rec_by_id, confidence_for):
    result = []
    for low, high in CONFIDENCE_BUCKETS:
        rows = [
            row for row in scored
            if confidence_for(rec_by_id[row["recommendation_id"]]) is not None
            and low <= confidence_for(rec_by_id[row["recommendation_id"]]) <= high
        ]
        result.append({
            "bucket": f"{low}-{high}",
            "sample_size": len(rows),
            "accuracy": rate(sum(row["status"] == "Succeeded" for row in rows), len(rows)),
        })
    return result


def horizon_maturity(outcomes):
    rows = []
    for horizon in HORIZONS:
        selected = [row for row in outcomes if row["horizon_days"] == horizon]
        counts = Counter(row["status"] for row in selected)
        completed = sum(counts[status] for status in COMPLETED_STATUSES)
        rows.append({
            "horizon_days": horizon,
            "total": len(selected),
            "completed": completed,
            "pending": counts["Pending"],
            "deferred": counts["Deferred"],
            "expired": counts["Expired"],
            "completion_rate": rate(completed, len(selected)),
            "status": "EVALUATED" if selected else "NOT_EVALUATED",
        })
    return rows
