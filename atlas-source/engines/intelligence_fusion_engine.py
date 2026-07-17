class IntelligenceFusionEngine:
    weights = {
        "technical": 0.20,
        "fundamentals": 0.18,
        "forecast": 0.18,
        "news": 0.10,
        "portfolio": 0.12,
        "risk": 0.12,
        "evidence": 0.05,
        "confidence": 0.05,
    }

    def fuse(
        self,
        technical=None,
        fundamentals=None,
        forecast=None,
        news=None,
        portfolio=None,
        risk=None,
        evidence=None,
        confidence=None,
    ):
        inputs = {
            "technical": technical,
            "fundamentals": fundamentals,
            "forecast": forecast,
            "news": news,
            "portfolio": portfolio,
            "risk": risk,
            "evidence": evidence,
            "confidence": confidence,
        }
        normalized = {
            name: self._normalize(name, value)
            for name, value in inputs.items()
        }
        present_scores = {
            name: score for name, score in normalized.items()
            if score is not None
        }
        missing_inputs = [
            name for name, score in normalized.items()
            if score is None
        ]
        overall_conviction = self._weighted_average(present_scores)
        positive = [
            (name, score) for name, score in present_scores.items()
            if score >= 70
        ]
        negative = [
            (name, score) for name, score in present_scores.items()
            if score < 50
        ]
        neutral = [
            (name, score) for name, score in present_scores.items()
            if 50 <= score < 70
        ]
        strongest_positive = self._strongest_positive(positive)
        strongest_negative = self._strongest_negative(negative)
        conflicting_signals = self._conflicts(positive, negative)
        contribution_percentages = self._contributions(present_scores)
        confidence_breakdown = self._confidence_breakdown(
            confidence,
            present_scores,
        )
        evidence_weighting_table = self._evidence_weighting_table(evidence)
        strongest_agreement = self._strongest_agreement(present_scores)
        strongest_disagreement = self._strongest_disagreement(present_scores)
        uncertainty_score = self._uncertainty_score(
            present_scores,
            missing_inputs,
            conflicting_signals,
        )
        recommendation_rationale = self._recommendation_rationale(
            overall_conviction,
            strongest_positive,
            strongest_negative,
            uncertainty_score,
        )

        return {
            "overall_conviction": overall_conviction,
            "bull_case": self._case_summary(positive, "supportive"),
            "bear_case": self._case_summary(negative, "weak"),
            "neutral_case": self._case_summary(neutral, "mixed"),
            "strongest_positive_factor": strongest_positive,
            "strongest_negative_factor": strongest_negative,
            "conflicting_signals": conflicting_signals,
            "missing_inputs": missing_inputs,
            "confidence_breakdown": confidence_breakdown,
            "evidence_weighting_table": evidence_weighting_table,
            "engine_contribution_percentages": contribution_percentages,
            "strongest_agreement": strongest_agreement,
            "strongest_disagreement": strongest_disagreement,
            "uncertainty_score": uncertainty_score,
            "recommendation_rationale": recommendation_rationale,
            "fusion_summary": self._summary(
                overall_conviction,
                strongest_positive,
                strongest_negative,
                conflicting_signals,
                missing_inputs,
            ),
        }

    def _normalize(self, name, value):
        if value is None:
            return None

        if isinstance(value, list):
            return self._normalize_list(name, value)

        if isinstance(value, dict):
            return self._normalize_dict(name, value)

        return self._clamp(value)

    def _normalize_dict(self, name, value):
        keys = [
            "score",
            "overall_score",
            "forecast_score",
            "confidence",
            "news_confidence",
            "portfolio_score",
            "risk_score",
            "technical_score",
            "fundamental_score",
        ]

        if name == "news":
            keys = ["confidence"] + keys

        for key in keys:
            if key in value and value[key] is not None:
                return self._clamp(value[key])

        return None

    def _normalize_list(self, name, value):
        if not value:
            return None

        if name == "confidence":
            scores = [
                item.get("confidence")
                for item in value
                if isinstance(item, dict)
                and item.get("confidence") is not None
            ]
        else:
            scores = [
                item.get("score")
                for item in value
                if isinstance(item, dict)
                and item.get("score") is not None
            ]

        if not scores:
            return None

        return self._clamp(sum(scores) / len(scores))

    def _weighted_average(self, scores):
        if not scores:
            return 0

        total_weight = sum(self.weights[name] for name in scores)
        weighted_total = sum(
            scores[name] * self.weights[name] for name in scores
        )

        return round(weighted_total / total_weight, 2)

    def _strongest_positive(self, positive):
        if not positive:
            return None

        name, score = max(positive, key=lambda item: item[1])

        return {"name": name, "score": score}

    def _strongest_negative(self, negative):
        if not negative:
            return None

        name, score = min(negative, key=lambda item: item[1])

        return {"name": name, "score": score}

    def _conflicts(self, positive, negative):
        if not positive or not negative:
            return []

        return [
            f"{positive_name} supports the thesis while {negative_name} is weak"
            for positive_name, _ in positive
            for negative_name, _ in negative
        ]

    def _case_summary(self, factors, label):
        if not factors:
            return []

        return [
            f"{name} is {label} at {round(score, 2)}"
            for name, score in factors
        ]

    def _contributions(self, scores):
        if not scores:
            return {}

        total_weight = sum(self.weights[name] for name in scores)

        return {
            name: round(self.weights[name] / total_weight * 100, 2)
            for name in scores
        }

    def _confidence_breakdown(self, confidence, scores):
        if isinstance(confidence, list) and confidence:
            return [
                {
                    "engine": item.get("name", f"evidence_{index + 1}"),
                    "confidence": item.get("confidence", 0),
                    "reliability_label": item.get(
                        "reliability_label",
                        "Unknown",
                    ),
                }
                for index, item in enumerate(confidence)
                if isinstance(item, dict)
            ]

        return [
            {
                "engine": name,
                "confidence": score,
                "reliability_label": self._confidence_label(score),
            }
            for name, score in scores.items()
        ]

    def _evidence_weighting_table(self, evidence):
        if not isinstance(evidence, list):
            return []

        return [
            {
                "category": item.get("category", item.get("name", "Unknown")),
                "score": item.get("score", 0),
                "confidence": item.get(
                    "confidence",
                    item.get("confidence_metadata", {}).get("confidence", 0),
                ),
                "weight": item.get("weight", 0),
                "summary": item.get("summary", ""),
            }
            for item in evidence
            if isinstance(item, dict)
        ]

    def _strongest_agreement(self, scores):
        high = [name for name, score in scores.items() if score >= 70]
        low = [name for name, score in scores.items() if score < 50]

        if len(high) >= 2:
            return f"{', '.join(high[:3])} agree positively."

        if len(low) >= 2:
            return f"{', '.join(low[:3])} agree negatively."

        return "No strong multi-engine agreement."

    def _strongest_disagreement(self, scores):
        if not scores:
            return "No signals available."

        highest_name, highest_score = max(scores.items(), key=lambda item: item[1])
        lowest_name, lowest_score = min(scores.items(), key=lambda item: item[1])
        spread = highest_score - lowest_score

        if spread < 25:
            return "No material disagreement."

        return (
            f"{highest_name} is strongest at {highest_score}; "
            f"{lowest_name} is weakest at {lowest_score}."
        )

    def _uncertainty_score(self, scores, missing_inputs, conflicting_signals):
        if not scores:
            return 100

        values = list(scores.values())
        spread = max(values) - min(values)
        missing_penalty = len(missing_inputs) * 8
        conflict_penalty = min(30, len(conflicting_signals) * 4)

        return max(0, min(100, round(spread * 0.4 + missing_penalty + conflict_penalty, 2)))

    def _recommendation_rationale(
        self,
        overall_conviction,
        strongest_positive,
        strongest_negative,
        uncertainty_score,
    ):
        if overall_conviction >= 70:
            stance = "supports a higher-conviction thesis"
        elif overall_conviction >= 50:
            stance = "supports a measured or neutral thesis"
        else:
            stance = "supports caution"

        rationale = f"Fusion {stance} with uncertainty {uncertainty_score}/100."

        if strongest_positive:
            rationale += f" Positive driver: {strongest_positive['name']}."

        if strongest_negative:
            rationale += f" Negative driver: {strongest_negative['name']}."

        return rationale

    def _confidence_label(self, score):
        if score >= 75:
            return "High"

        if score >= 50:
            return "Medium"

        return "Low"

    def _summary(
        self,
        overall_conviction,
        strongest_positive,
        strongest_negative,
        conflicting_signals,
        missing_inputs,
    ):
        summary = f"Fusion conviction is {overall_conviction}/100."

        if strongest_positive:
            summary += (
                " Strongest positive factor is "
                f"{strongest_positive['name']}."
            )

        if strongest_negative:
            summary += (
                " Strongest negative factor is "
                f"{strongest_negative['name']}."
            )

        if conflicting_signals:
            summary += " Conflicting signals are present."

        if missing_inputs:
            summary += (
                " Missing inputs: "
                f"{', '.join(missing_inputs)}."
            )

        return summary

    def _clamp(self, value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None

        return max(0, min(100, round(number, 2)))
