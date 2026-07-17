class AdvisorEngine:

    def advise(self, portfolio_health, recommendations, available_cash):
        warnings = self._build_warnings(portfolio_health, available_cash)

        if available_cash < 50:
            return {
                "best_investment": "Cash",
                "amount": available_cash,
                "reason": "Available cash is below the minimum investment threshold.",
                "warnings": warnings,
            }

        if portfolio_health < 60:
            return {
                "best_investment": "Diversification",
                "amount": available_cash,
                "reason": "Improve diversification before adding concentrated positions.",
                "warnings": warnings,
            }

        best_recommendation = self._highest_overall_score(recommendations)

        if best_recommendation is None:
            return {
                "best_investment": "Cash",
                "amount": available_cash,
                "reason": "No investment recommendations are currently available.",
                "warnings": warnings,
            }

        return {
            "best_investment": self._value(best_recommendation, "ticker"),
            "amount": available_cash,
            "reason": "Highest overall investment score.",
            "warnings": warnings,
        }

    def _build_warnings(self, portfolio_health, available_cash):
        warnings = []

        if portfolio_health < 60:
            warnings.append("Low Diversification")

        if portfolio_health < 50:
            warnings.append("High Risk")

        if available_cash > 1000:
            warnings.append("Too Much Cash")

        if available_cash < 50:
            warnings.append("Too Little Cash")

        return warnings

    def _highest_overall_score(self, recommendations):
        if not recommendations:
            return None

        return max(
            recommendations,
            key=lambda recommendation: self._value(
                recommendation,
                "overall_score"
            )
        )

    def _value(self, item, key):
        if isinstance(item, dict):
            return item.get(key, 0)

        return getattr(item, key, 0)
