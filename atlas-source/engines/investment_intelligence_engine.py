class InvestmentIntelligenceEngine:

    def evaluate(
        self,
        technical_score,
        fundamental_score,
        portfolio_health_score,
        risk_score,
        forecast_score=50
    ):
        overall_score = (
            technical_score * 0.30
            + fundamental_score * 0.30
            + portfolio_health_score * 0.15
            + risk_score * 0.10
            + forecast_score * 0.15
        )
        overall_score = round(max(0, min(100, overall_score)))

        if overall_score >= 90:
            rating = "Exceptional"
            summary = "Strong investment candidate."

        elif overall_score >= 80:
            rating = "Excellent"
            summary = "Strong investment candidate."

        elif overall_score >= 70:
            rating = "Good"
            summary = "Solid investment with moderate risk."

        elif overall_score >= 60:
            rating = "Fair"
            summary = "Solid investment with moderate risk."

        else:
            rating = "Poor"
            summary = "Weak investment candidate."

        return {
            "overall_score": overall_score,
            "rating": rating,
            "summary": summary,
        }
