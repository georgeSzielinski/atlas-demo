class ConfidenceEngine:

    base_confidence = {
        "Technical": 75,
        "Fundamental": 70,
        "Forecast": 60,
        "News": 45,
        "Portfolio": 65,
        "Risk": 70,
        "Signal Quality": 80,
    }

    def calibrate(self, evidence_item):
        name = evidence_item["name"]
        score = evidence_item["score"]
        confidence = self._confidence_for(name, score)

        return {
            "confidence": confidence,
            "reliability_label": self._label(confidence),
            "explanation": self._explanation(name, confidence),
        }

    def _confidence_for(self, name, score):
        base = self.base_confidence.get(name, 50)

        if score >= 80:
            return min(100, base + 10)

        if score < 40:
            return max(0, base - 20)

        if score < 60:
            return max(0, base - 10)

        return base

    def _label(self, confidence):
        if confidence >= 75:
            return "High"

        if confidence >= 50:
            return "Medium"

        return "Low"

    def _explanation(self, name, confidence):
        label = self._label(confidence).lower()
        return f"{name} evidence has {label} estimated reliability."
