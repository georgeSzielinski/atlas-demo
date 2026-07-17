import hashlib
from datetime import datetime


class CaseStudyEngine:
    def build_case_study(self, recommendation, case_date=None):
        validation = recommendation.get("validation_result") or {}
        if validation.get("success") is None and validation.get("hit") is None:
            return None

        case = {
            "case_id": self._case_id(recommendation, validation),
            "ticker": recommendation.get("ticker", ""),
            "recommendation": recommendation.get("action", ""),
            "market_regime": recommendation.get("market_regime", "Unknown"),
            "evidence": recommendation.get("evidence_breakdown", []),
            "committee": self._committee(recommendation),
            "executive_review": self._executive_review(recommendation),
            "knowledge_score": recommendation.get("knowledge_score", 0),
            "stability_score": recommendation.get("stability_score", 0),
            "outcome": "Win" if self._success(validation) else "Loss",
            "return": validation.get("percentage_return", 0),
            "holding_period": validation.get("holding_period", 0),
            "validation": validation,
            "benchmark": recommendation.get("benchmark", {}),
            "hypotheses": recommendation.get("assumptions", []),
            "counterfactuals": recommendation.get("counterfactuals", []),
            "catalysts": recommendation.get("catalysts", []),
            "probability_report": recommendation.get("probability_report", {}),
            "lessons_learned": {},
            "case_date": case_date or datetime.now().isoformat(),
        }
        case["lessons_learned"] = self.lessons_learned(case)

        return case

    def build_case_studies(self, recommendations, case_date=None):
        cases = []

        for recommendation in recommendations:
            case = self.build_case_study(recommendation, case_date=case_date)
            if case is not None:
                cases.append(case)

        return cases

    def lessons_learned(self, case):
        evidence = [
            item for item in case.get("evidence", [])
            if isinstance(item, dict)
        ]
        strongest = max(
            evidence,
            key=lambda item: item.get("score", 0),
            default={"category": "Unavailable", "score": 0},
        )
        weakest = min(
            evidence,
            key=lambda item: item.get("score", 0),
            default={"category": "Unavailable", "score": 0},
        )
        success = case.get("outcome") == "Win"
        confidence = case.get("validation", {}).get(
            "confidence",
            case.get("committee", {}).get("agreement", 0),
        )

        return {
            "most_useful_evidence": strongest.get(
                "category",
                strongest.get("name", "Unavailable"),
            ),
            "least_useful_evidence": weakest.get(
                "category",
                weakest.get("name", "Unavailable"),
            ),
            "unexpected_outcome": (
                "High confidence loss"
                if not success and confidence >= 70
                else "Low confidence win"
                if success and confidence < 50
                else "No major surprise"
            ),
            "confidence_calibration": (
                "Aligned"
                if (success and confidence >= 50)
                or (not success and confidence < 50)
                else "Needs review"
            ),
            "committee_effectiveness": (
                "Aligned"
                if (success and case.get("committee", {}).get("agreement", 0) >= 60)
                or (not success and case.get("committee", {}).get("agreement", 0) < 60)
                else "Needs review"
            ),
            "executive_effectiveness": self._executive_effectiveness(case),
            "hypothesis_success": (
                "Supported" if success and case.get("hypotheses") else "Unproven"
            ),
            "future_improvements": self._future_improvements(case, weakest),
        }

    def filter_cases(self, cases, filter_name):
        if filter_name == "winning":
            return [case for case in cases if case.get("outcome") == "Win"]

        if filter_name == "losing":
            return [case for case in cases if case.get("outcome") == "Loss"]

        if filter_name == "bull_market":
            return [
                case for case in cases
                if case.get("market_regime") in {"Strong Bull", "Bull"}
            ]

        if filter_name == "bear_market":
            return [
                case for case in cases
                if case.get("market_regime") in {"Strong Bear", "Bear"}
            ]

        if filter_name == "committee_disagreements":
            return [
                case for case in cases
                if case.get("committee", {}).get("main_disagreement")
            ]

        if filter_name == "forecast_failures":
            return self._evidence_failures(cases, "Forecast")

        if filter_name == "news_failures":
            return self._evidence_failures(cases, "News")

        return cases

    def _case_id(self, recommendation, validation):
        seed = "|".join([
            str(recommendation.get("id", "")),
            recommendation.get("ticker", ""),
            recommendation.get("action", ""),
            str(validation.get("percentage_return", "")),
        ])
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]

        return f"case-{digest}"

    def _success(self, validation):
        return validation.get("success") is True or validation.get("hit") is True

    def _committee(self, recommendation):
        return {
            "agreement": recommendation.get("committee_agreement", 0),
            "main_disagreement": recommendation.get("main_disagreement", ""),
            "summary": recommendation.get("final_committee_summary", ""),
        }

    def _executive_review(self, recommendation):
        return {
            "status": recommendation.get("executive_status", ""),
            "confidence": recommendation.get("executive_confidence", 0),
            "warnings": recommendation.get("executive_warnings", []),
        }

    def _executive_effectiveness(self, case):
        status = case.get("executive_review", {}).get("status", "")
        success = case.get("outcome") == "Win"

        if status in {"READY", "CAUTION"} and success:
            return "Aligned"

        if status in {"NEEDS_REVIEW", "INSUFFICIENT_DATA"} and not success:
            return "Aligned"

        if not status:
            return "Unavailable"

        return "Needs review"

    def _future_improvements(self, case, weakest):
        improvements = []

        if case.get("outcome") == "Loss":
            improvements.append("Review failed evidence before repeating setup.")

        if weakest.get("score", 0) < 50:
            improvements.append(
                f"Improve {weakest.get('category', weakest.get('name', 'evidence'))} coverage."
            )

        if case.get("lessons_learned", {}).get("confidence_calibration") == "Needs review":
            improvements.append("Recheck confidence calibration for similar cases.")

        return improvements or ["Preserve case as a validated research analog."]

    def _evidence_failures(self, cases, category):
        failures = []

        for case in cases:
            if case.get("outcome") != "Loss":
                continue

            if any(
                item.get("category") == category and item.get("score", 0) >= 60
                for item in case.get("evidence", [])
                if isinstance(item, dict)
            ):
                failures.append(case)

        return failures
