class ExplainabilityEngine:

    def generate(self, recommendation):
        action = self._get(recommendation, "action", "HOLD")
        rating = self._get(recommendation, "rating", "Unrated")
        ticker = self._get(recommendation, "ticker", "This ticker")
        technical_score = self._number(
            self._get(recommendation, "technical_score", 0)
        )
        fundamental_score = self._number(
            self._get(recommendation, "fundamental_score", 0)
        )
        portfolio_score = self._number(
            self._get(recommendation, "portfolio_score", 0)
        )
        risk_score = self._number(self._get(recommendation, "risk_score", 0))
        forecast_score = self._number(
            self._get(recommendation, "forecast_score", 0)
        )
        forecast_direction = self._get(
            recommendation,
            "forecast_direction",
            "UNKNOWN"
        )
        news_sentiment = self._get(
            recommendation,
            "news_sentiment",
            "neutral"
        )
        news_confidence = self._number(
            self._get(recommendation, "news_confidence", 0)
        )

        strengths = []
        weaknesses = []

        self._score_signal(
            technical_score,
            "Technical indicators support the setup.",
            "Technical indicators are not yet supportive.",
            strengths,
            weaknesses
        )
        self._score_signal(
            fundamental_score,
            "Fundamentals support the recommendation.",
            "Fundamentals are a weaker part of the setup.",
            strengths,
            weaknesses
        )
        self._score_signal(
            forecast_score,
            f"Forecast model points {forecast_direction}.",
            "Forecast score is not strong enough to add conviction.",
            strengths,
            weaknesses
        )
        self._score_signal(
            portfolio_score,
            "Portfolio fit is acceptable.",
            "Portfolio fit is limited.",
            strengths,
            weaknesses
        )
        self._score_signal(
            risk_score,
            "Risk profile is acceptable.",
            "Risk score is a concern.",
            strengths,
            weaknesses
        )

        if news_confidence > 0:
            strengths.append(
                f"News coverage is {news_sentiment} with available headlines."
            )
        else:
            weaknesses.append("News signal is limited or unavailable.")

        summary = (
            f"{ticker} is rated {rating} with a {action} action based on "
            "technical, fundamental, forecast, portfolio, risk, and news "
            "signals."
        )
        why_this_rating = (
            f"The rating reflects an overall score of "
            f"{self._get(recommendation, 'overall_score', 0)}, with forecast "
            f"score {forecast_score}, technical score {technical_score}, "
            f"fundamental score {fundamental_score}, portfolio score "
            f"{portfolio_score}, and risk score {risk_score}."
        )

        return {
            "summary": summary,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "why_this_rating": why_this_rating,
        }

    def generate_explanation(
        self,
        recommendation,
        technical_score,
        fundamental_score,
        portfolio_score,
        risk_score
    ):
        strengths = []
        concerns = []

        if technical_score >= 80:
            strengths.append("Strong technical momentum")

        elif technical_score < 50:
            concerns.append("Weak technical momentum")

        if fundamental_score >= 80:
            strengths.append("Strong company fundamentals")

        elif fundamental_score < 50:
            concerns.append("Weak company fundamentals")

        if portfolio_score >= 80:
            strengths.append("Excellent portfolio fit")

        elif portfolio_score < 50:
            concerns.append("Poor portfolio fit")

        if risk_score >= 80:
            strengths.append("Risk profile is acceptable")

        elif risk_score < 50:
            concerns.append("Investment carries elevated risk")

        if recommendation == "BUY":
            summary = "Atlas considers this a strong investment candidate."

        elif recommendation == "HOLD":
            summary = "Atlas recommends monitoring this investment."

        elif recommendation == "AVOID":
            summary = "Atlas does not currently recommend this investment."

        else:
            summary = "Atlas does not have a recommendation for this investment."

        return {
            "strengths": strengths,
            "concerns": concerns,
            "summary": summary,
        }

    def _get(self, recommendation, key, fallback):
        if isinstance(recommendation, dict):
            return recommendation.get(key, fallback)

        return getattr(recommendation, key, fallback)

    def _number(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0

    def _score_signal(
        self,
        score,
        strength,
        weakness,
        strengths,
        weaknesses
    ):
        if score >= 70:
            strengths.append(strength)
        elif score < 50:
            weaknesses.append(weakness)
