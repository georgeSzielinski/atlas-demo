class RiskEngine:

    def portfolio_risk(self, portfolio):

        positions = portfolio.position_count()

        if positions == 0:
            return "No Risk"

        if positions == 1:
            return "Very High"

        if positions <= 3:
            return "High"

        if positions <= 6:
            return "Medium"

        return "Low"

    def cash_percentage(self, portfolio):

        total = portfolio.portfolio_value()

        if total == 0:
            return 0

        return (portfolio.cash / total) * 100