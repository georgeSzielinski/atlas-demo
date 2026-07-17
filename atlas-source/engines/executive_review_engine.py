class ExecutiveReviewEngine:
    REQUIRED_EVIDENCE = [
        "Technical",
        "Fundamental",
        "Forecast",
        "News",
        "Portfolio",
        "Risk",
    ]

    def review(
        self,
        recommendation,
        historical_recommendations=None,
        discoveries=None,
    ):
        historical_recommendations = historical_recommendations or []
        discoveries = discoveries or []
        checks = {
            "evidence_completeness": self._evidence_completeness(
                recommendation,
            ),
            "committee_agreement": self._committee_agreement(recommendation),
            "historical_similarity": self._historical_similarity(
                recommendation,
                historical_recommendations,
            ),
            "validation_history": self._validation_history(
                recommendation,
                historical_recommendations,
            ),
            "discovery_conflicts": self._discovery_conflicts(
                recommendation,
                discoveries,
            ),
            "confidence_calibration": self._confidence_calibration(
                recommendation,
            ),
            "missing_providers": self._missing_providers(recommendation),
            "missing_data": self._missing_data(recommendation),
            "upcoming_major_events": self._upcoming_major_events(),
            "recommendation_stability": self._recommendation_stability(
                recommendation,
            ),
        }
        warnings = self._warnings(checks)
        strengths = self._strengths(checks)
        weaknesses = self._weaknesses(checks)
        required_research = self._required_research(checks)
        status = self._status(checks, warnings)
        executive_confidence = self._executive_confidence(checks, warnings)

        return {
            "executive_status": status,
            "executive_confidence": executive_confidence,
            "executive_summary": self._summary(
                recommendation,
                status,
                executive_confidence,
            ),
            "executive_warnings": warnings,
            "executive_strengths": strengths,
            "executive_weaknesses": weaknesses,
            "required_follow_up_research": required_research,
            "checks": checks,
            "controlled_decision": (
                "Executive review is a quality gate and does not change "
                "BUY, HOLD, or AVOID actions."
            ),
        }

    def _evidence_completeness(self, recommendation):
        evidence = self._evidence(recommendation)
        present = [
            item.get("category") or item.get("name")
            for item in evidence
            if isinstance(item, dict)
        ]
        missing = [
            item for item in self.REQUIRED_EVIDENCE
            if item not in present
        ]

        return {
            "passed": len(missing) == 0,
            "score": self._rate(len(present), len(self.REQUIRED_EVIDENCE)),
            "missing": missing,
        }

    def _committee_agreement(self, recommendation):
        agreement = self._number(
            self._get(recommendation, "committee_agreement", 0)
        )

        return {
            "passed": agreement >= 60,
            "score": agreement,
            "agreement": agreement,
        }

    def _historical_similarity(self, recommendation, history):
        ticker = self._get(recommendation, "ticker", "")
        action = self._get(recommendation, "action", "")
        similar = [
            item for item in history
            if self._get(item, "ticker", "") == ticker
            or self._get(item, "action", "") == action
        ]

        if not similar:
            return {
                "passed": False,
                "score": 0,
                "sample_size": 0,
                "success_rate": 0,
            }

        validated = [
            item for item in similar
            if self._validation(item).get("success") is not None
        ]
        wins = [
            item for item in validated
            if self._validation(item).get("success") is True
        ]
        success_rate = self._rate(len(wins), len(validated))

        return {
            "passed": len(validated) > 0 and success_rate >= 50,
            "score": success_rate,
            "sample_size": len(validated),
            "success_rate": success_rate,
        }

    def _validation_history(self, recommendation, history):
        validation = self._validation(recommendation)

        if validation.get("success") is not None:
            score = 100 if validation.get("success") else 0
            return {
                "passed": validation.get("success") is True,
                "score": score,
                "status": validation.get("status", "Completed"),
            }

        validated = [
            item for item in history
            if self._validation(item).get("success") is not None
        ]

        return {
            "passed": len(validated) > 0,
            "score": 50 if validated else 0,
            "status": "Pending",
        }

    def _discovery_conflicts(self, recommendation, discoveries):
        conflicts = []
        weak_sources = [
            item.get("category") or item.get("name")
            for item in self._evidence(recommendation)
            if isinstance(item, dict)
            and self._number(item.get("score")) < 50
        ]

        for discovery in discoveries:
            title = self._get(discovery, "title", "")
            description = self._get(discovery, "description", "")
            text = f"{title} {description}".lower()
            if any(source.lower() in text for source in weak_sources):
                conflicts.append(title)

        return {
            "passed": len(conflicts) == 0,
            "score": 100 if not conflicts else 40,
            "conflicts": conflicts,
        }

    def _confidence_calibration(self, recommendation):
        metadata = self._get(recommendation, "confidence_metadata", []) or []
        confidence = self._number(self._get(recommendation, "confidence", 0))
        low = [
            item for item in metadata
            if isinstance(item, dict)
            and self._number(item.get("confidence")) < 50
        ]

        score = max(0, min(100, confidence - (len(low) * 8)))

        return {
            "passed": score >= 55,
            "score": score,
            "low_confidence_items": len(low),
        }

    def _missing_providers(self, recommendation):
        missing = []

        if not self._get(recommendation, "forecast_direction", ""):
            missing.append("Forecast provider output")

        if self._number(self._get(recommendation, "headline_count", 0)) == 0:
            missing.append("News provider headlines")

        if self._number(self._get(recommendation, "fundamental_score", 0)) == 0:
            missing.append("Fundamental provider score")

        return {
            "passed": len(missing) == 0,
            "score": 100 if not missing else max(0, 100 - len(missing) * 25),
            "missing": missing,
        }

    def _missing_data(self, recommendation):
        missing = list(self._get(recommendation, "missing_evidence", []) or [])
        missing.extend(self._get(recommendation, "missing_inputs", []) or [])

        return {
            "passed": len(missing) == 0,
            "score": 100 if not missing else max(0, 100 - len(missing) * 20),
            "missing": sorted(set(missing)),
        }

    def _upcoming_major_events(self):
        return {
            "passed": True,
            "score": 50,
            "events": [],
            "placeholder": True,
        }

    def _recommendation_stability(self, recommendation):
        flip_conditions = self._get(
            recommendation,
            "recommendation_flip_conditions",
            [],
        ) or []
        unstable = [
            item for item in flip_conditions
            if not str(item).startswith("No single")
        ]

        return {
            "passed": len(unstable) == 0,
            "score": 100 if not unstable else 60,
            "flip_conditions": flip_conditions,
        }

    def _warnings(self, checks):
        warnings = []

        for name, check in checks.items():
            if check["passed"]:
                continue

            warnings.append(self._warning_text(name, check))

        return warnings

    def _strengths(self, checks):
        strengths = []

        for name, check in checks.items():
            if check["passed"] and check["score"] >= 60:
                strengths.append(self._label(name))

        return strengths or ["No material executive strengths identified."]

    def _weaknesses(self, checks):
        weaknesses = []

        for name, check in checks.items():
            if not check["passed"]:
                weaknesses.append(self._label(name))

        return weaknesses or ["No material executive weaknesses identified."]

    def _required_research(self, checks):
        research = []

        if checks["evidence_completeness"]["missing"]:
            missing = ", ".join(checks["evidence_completeness"]["missing"])
            research.append(f"Complete missing evidence: {missing}.")

        if checks["missing_providers"]["missing"]:
            missing = ", ".join(checks["missing_providers"]["missing"])
            research.append(f"Verify provider coverage: {missing}.")

        if checks["discovery_conflicts"]["conflicts"]:
            research.append("Review discovery conflicts before presentation.")

        if not checks["historical_similarity"]["passed"]:
            research.append("Collect or review comparable historical outcomes.")

        if not research:
            research.append("Monitor validation and observatory outcomes.")

        return research[:5]

    def _status(self, checks, warnings):
        if checks["evidence_completeness"]["score"] < 50:
            return "INSUFFICIENT_DATA"

        if checks["missing_providers"]["missing"]:
            return "INSUFFICIENT_DATA"

        if len(warnings) >= 4:
            return "NEEDS_REVIEW"

        if warnings:
            return "CAUTION"

        return "READY"

    def _executive_confidence(self, checks, warnings):
        score = self._average([
            check["score"] for check in checks.values()
        ])

        return round(max(0, min(100, score - len(warnings) * 3)))

    def _summary(self, recommendation, status, confidence):
        return (
            f"Executive review status {status} with {confidence}% confidence "
            f"for {self._get(recommendation, 'ticker', '')}; action remains "
            f"{self._get(recommendation, 'action', '')}."
        )

    def _warning_text(self, name, check):
        label = self._label(name)

        if check.get("missing"):
            return f"{label} incomplete: {', '.join(check['missing'])}."

        if check.get("conflicts"):
            return f"{label} conflict: {', '.join(check['conflicts'])}."

        return f"{label} requires review."

    def _label(self, name):
        return name.replace("_", " ").title()

    def _evidence(self, recommendation):
        return self._get(recommendation, "evidence_breakdown", []) or []

    def _validation(self, recommendation):
        return self._get(recommendation, "validation_result", None) or {}

    def _get(self, item, key, fallback):
        if isinstance(item, dict):
            return item.get(key, fallback)

        return getattr(item, key, fallback)

    def _number(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0

    def _average(self, values):
        cleaned = [value for value in values if value is not None]

        if not cleaned:
            return 0

        return sum(cleaned) / len(cleaned)

    def _rate(self, numerator, denominator):
        if denominator == 0:
            return 0

        return round(numerator / denominator * 100, 2)
