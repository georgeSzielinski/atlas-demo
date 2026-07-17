class ChangeEngine:

    def compare_runs(self, current_run, previous_run):
        average_rsi_change = (
            current_run["average_rsi"]
            - previous_run["average_rsi"]
        )
        average_volatility_change = (
            current_run["average_volatility"]
            - previous_run["average_volatility"]
        )

        if (
            current_run["market_status"] == previous_run["market_status"]
            and abs(average_rsi_change) < 1
            and abs(average_volatility_change) < 0.1
        ):
            summary = "Market conditions were mostly unchanged since the last run."

        elif average_rsi_change > 0 and average_volatility_change <= 0:
            summary = "Market conditions improved with stronger RSI and controlled volatility."

        elif average_rsi_change < 0 or average_volatility_change > 0:
            summary = "Market conditions worsened with weaker RSI or higher volatility."

        else:
            summary = "Market conditions were mixed since the last run."

        return {
            "market_status_change": (
                f"{previous_run['market_status']} -> "
                f"{current_run['market_status']}"
            ),
            "average_rsi_change": average_rsi_change,
            "average_volatility_change": average_volatility_change,
            "summary": summary,
        }

    def compare_recommendations(
        self,
        current_recommendations,
        previous_recommendations
    ):
        previous_by_ticker = {
            recommendation["ticker"]: recommendation
            for recommendation in previous_recommendations
        }

        changes = []

        for current in current_recommendations:
            previous = previous_by_ticker.get(current["ticker"])

            if previous is None:
                continue

            changes.append({
                "ticker": current["ticker"],
                "previous_action": previous["action"],
                "current_action": current["action"],
                "previous_confidence": previous["confidence"],
                "current_confidence": current["confidence"],
                "confidence_change": (
                    current["confidence"]
                    - previous["confidence"]
                ),
            })

        return changes

    def compare_portfolio_health(
        self,
        current_snapshot,
        previous_snapshot,
        portfolio_health_engine
    ):
        if current_snapshot is None or previous_snapshot is None:
            return None

        current_health = portfolio_health_engine.calculate_health(
            current_snapshot
        )
        previous_health = portfolio_health_engine.calculate_health(
            previous_snapshot
        )

        health_score_change = (
            current_health["health_score"]
            - previous_health["health_score"]
        )

        if health_score_change > 0:
            summary = "Portfolio health improved since the last run."

        elif health_score_change < 0:
            summary = "Portfolio health worsened since the last run."

        else:
            summary = "Portfolio health was unchanged since the last run."

        return {
            "previous_health_score": previous_health["health_score"],
            "current_health_score": current_health["health_score"],
            "health_score_change": health_score_change,
            "previous_risk_rating": previous_health["risk_rating"],
            "current_risk_rating": current_health["risk_rating"],
            "previous_cash_rating": previous_health["cash_rating"],
            "current_cash_rating": current_health["cash_rating"],
            "previous_diversification_rating": previous_health[
                "diversification_rating"
            ],
            "current_diversification_rating": current_health[
                "diversification_rating"
            ],
            "summary": summary,
        }
