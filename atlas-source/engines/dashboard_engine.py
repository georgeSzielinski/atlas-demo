from models.dashboard import Dashboard


class DashboardEngine:

    def build_dashboard(self, stocks, recommendations):

        if not stocks:
            return Dashboard(
                title="ATLAS - AI Investment Research Platform",
                market_status="Unavailable",
                average_rsi=0,
                average_volatility=0,
                recommendations=[]
            )

        average_rsi = sum(stock.rsi for stock in stocks) / len(stocks)

        average_volatility = (
            sum(stock.volatility for stock in stocks)
            / len(stocks)
        )

        bullish = sum(
            1 for stock in stocks
            if stock.trend == "Bullish"
        )

        bearish = sum(
            1 for stock in stocks
            if stock.trend == "Bearish"
        )

        if bullish > bearish:
            market_status = "Bullish"

        elif bearish > bullish:
            market_status = "Bearish"

        else:
            market_status = "Neutral"

        return Dashboard(
            title="ATLAS - AI Investment Research Platform",
            market_status=market_status,
            average_rsi=average_rsi,
            average_volatility=average_volatility,
            recommendations=recommendations
        )
