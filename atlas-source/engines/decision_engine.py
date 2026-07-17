from models.investment_recommendation import InvestmentRecommendation


class DecisionEngine:

    def decide(self, stock):

        confidence = 50

        reasons = []
        risks = []

        confidence += stock.score * 5

        if stock.trend == "Bullish":
            confidence += 10
            reasons.append("Bullish technical trend")

        elif stock.trend == "Bearish":
            confidence -= 10
            risks.append("Bearish technical trend")

        if stock.macd_trend == "Bullish":
            confidence += 8
            reasons.append("Bullish MACD momentum")

        elif stock.macd_trend == "Bearish":
            confidence -= 8
            risks.append("Bearish MACD momentum")

        if 40 <= stock.rsi <= 65:
            confidence += 7
            reasons.append("Healthy RSI range")

        elif stock.rsi > 70:
            confidence -= 10
            risks.append("RSI indicates overbought conditions")

        elif stock.rsi < 30:
            confidence -= 10
            risks.append("RSI indicates oversold weakness")

        if stock.volatility > 2:
            confidence -= 7
            risks.append("High volatility")

        if stock.price_vs_20ma > 0:
            confidence += 5
            reasons.append("Trading above 20-day moving average")

        if stock.price_vs_50ma > 0:
            confidence += 8
            reasons.append("Trading above 50-day moving average")

        elif stock.price_vs_50ma < 0:
            confidence -= 8
            risks.append("Trading below 50-day moving average")

        if stock.month_return > 0:
            confidence += 6
            reasons.append("Positive monthly return")

        elif stock.month_return < 0:
            confidence -= 6
            risks.append("Negative monthly return")

        confidence = max(1, min(99, confidence))

        if confidence >= 80:
            action = "BUY"

        elif confidence >= 55:
            action = "HOLD"

        else:
            action = "AVOID"

        return InvestmentRecommendation(
            ticker=stock.ticker,
            action=action,
            confidence=confidence,
            reasons=reasons,
            risks=risks,
            score=stock.score
        )
