class PortfolioHealthEngine:

    def calculate_health(self, snapshot):
        health_score = 100

        position_count = snapshot["position_count"]
        cash_percentage = snapshot["cash_percentage"]
        risk_level = snapshot["risk_level"]

        if position_count == 0:
            health_score -= 50
            diversification_rating = "No positions"

        elif position_count == 1:
            health_score -= 35
            diversification_rating = "Very weak"

        elif position_count <= 3:
            health_score -= 20
            diversification_rating = "Needs improvement"

        elif position_count <= 6:
            health_score -= 10
            diversification_rating = "Moderate"

        else:
            diversification_rating = "Strong"

        if cash_percentage < 5:
            health_score -= 15
            cash_rating = "Low cash"

        elif cash_percentage <= 40:
            cash_rating = "Healthy cash"

        else:
            health_score -= 10
            cash_rating = "High cash"

        if risk_level == "Very High":
            health_score -= 30
            risk_rating = "Very high risk"

        elif risk_level == "High":
            health_score -= 20
            risk_rating = "High risk"

        elif risk_level == "Medium":
            health_score -= 10
            risk_rating = "Medium risk"

        elif risk_level == "Low":
            risk_rating = "Low risk"

        elif risk_level == "No Risk":
            health_score -= 25
            risk_rating = "Not invested"

        else:
            health_score -= 15
            risk_rating = "Unknown risk"

        health_score = max(0, min(100, health_score))

        summary = (
            f"Portfolio health is {health_score}/100 with "
            f"{diversification_rating.lower()} diversification, "
            f"{cash_rating.lower()}, and {risk_rating.lower()}."
        )

        return {
            "health_score": health_score,
            "diversification_rating": diversification_rating,
            "cash_rating": cash_rating,
            "risk_rating": risk_rating,
            "summary": summary,
        }
