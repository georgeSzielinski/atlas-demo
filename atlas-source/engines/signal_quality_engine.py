class SignalQualityEngine:

    def evaluate(
        self,
        technical_score,
        fundamental_score,
        forecast_score,
        news_confidence,
        risk_score,
        volatility
    ):
        warnings = []
        component_scores = [
            self._score_from_percent(technical_score),
            self._score_from_percent(fundamental_score),
            self._score_from_percent(forecast_score),
            self._score_from_percent(news_confidence),
            self._score_from_percent(risk_score),
            self._volatility_score(volatility),
        ]
        quality_score = round(sum(component_scores) / len(component_scores))

        if technical_score < 50:
            warnings.append("Weak technical confirmation")

        if fundamental_score < 50:
            warnings.append("Weak fundamental support")

        if forecast_score < 50:
            warnings.append("Weak forecast confirmation")

        if news_confidence < 25:
            warnings.append("Limited news confirmation")

        if risk_score < 50:
            warnings.append("Elevated risk profile")

        if volatility > 35:
            warnings.append("High volatility may increase false positives")

        return {
            "signal_quality_score": max(1, min(10, quality_score)),
            "signal_label": self._label_for_score(quality_score),
            "false_positive_warnings": warnings,
        }

    def _score_from_percent(self, value):
        return max(1, min(10, round(value / 10)))

    def _volatility_score(self, volatility):
        if volatility <= 10:
            return 10

        if volatility <= 20:
            return 8

        if volatility <= 35:
            return 6

        if volatility <= 50:
            return 4

        return 2

    def _label_for_score(self, score):
        if score >= 9:
            return "High Conviction"

        if score >= 8:
            return "Strong"

        if score >= 7:
            return "Acceptable"

        return "Weak"
