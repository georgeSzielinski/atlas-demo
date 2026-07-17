from engines.confidence_engine import ConfidenceEngine


class EvidenceEngine:

    weights = {
        "Technical": 0.25,
        "Fundamental": 0.20,
        "Forecast": 0.20,
        "News": 0.10,
        "Portfolio": 0.10,
        "Risk": 0.10,
        "Validation": 0.03,
        "Benchmark": 0.02,
    }

    def __init__(self):
        self.confidence_engine = ConfidenceEngine()

    def build(self, recommendation):
        evidence = [
            self._item(
                "Technical",
                recommendation.technical_score,
            ),
            self._item(
                "Fundamental",
                recommendation.fundamental_score,
            ),
            self._item(
                "Forecast",
                recommendation.forecast_score,
            ),
            self._item(
                "News",
                recommendation.news_confidence,
            ),
            self._item(
                "Portfolio",
                recommendation.portfolio_score,
            ),
            self._item(
                "Risk",
                recommendation.risk_score,
            ),
            self._item(
                "Validation",
                50 if recommendation.validation_status == "Pending" else 70,
            ),
            self._item(
                "Benchmark",
                recommendation.overall_conviction or recommendation.overall_score,
            ),
        ]
        recommendation.confidence_metadata = [
            item["confidence_metadata"] for item in evidence
        ]

        return evidence

    def _item(self, name, score):
        normalized_score = self._normalize_score(score)
        metadata = self.confidence_engine.calibrate({
            "name": name,
            "score": normalized_score,
        })

        return {
            "name": name,
            "category": name,
            "score": normalized_score,
            "confidence": metadata["confidence"],
            "weight": self.weights[name],
            "label": self._label(normalized_score),
            "reason": self._reason(name, normalized_score),
            "summary": self._summary(name, normalized_score, metadata),
            "confidence_metadata": metadata,
        }

    def _normalize_score(self, score):
        return max(0, min(100, round(score)))

    def _label(self, score):
        if score >= 80:
            return "Strong"

        if score >= 60:
            return "Acceptable"

        if score >= 40:
            return "Weak"

        return "Poor"

    def _reason(self, name, score):
        if score >= 70:
            return f"{name} evidence supports the recommendation."

        if score < 50:
            return f"{name} evidence is a weaker input."

        return f"{name} evidence is mixed."

    def _summary(self, name, score, metadata):
        return (
            f"{name} score {score} with "
            f"{metadata['reliability_label'].lower()} confidence."
        )
