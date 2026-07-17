class MarketRegimeEngine:
    REGIMES = [
        "Strong Bull",
        "Bull",
        "Sideways",
        "Volatile",
        "Bear",
        "Strong Bear",
    ]

    def classify_row(self, row):
        period_return = self._period_return(row)
        volatility = row.get("volatility", 0) or 0
        drawdown = self._drawdown(row)
        trend = row.get("trend", "Neutral")
        above_short_average = row.get("price_vs_20ma", 0) >= 0
        above_long_average = row.get("price_vs_50ma", 0) >= 0

        if period_return <= -8 or (
            drawdown <= -12 and not above_long_average
        ):
            return self._result("Strong Bear", row, period_return, drawdown)

        if period_return >= 8 and above_short_average and above_long_average:
            return self._result("Strong Bull", row, period_return, drawdown)

        if volatility >= 5:
            return self._result("Volatile", row, period_return, drawdown)

        if period_return <= -2 or (
            trend == "Bearish" and not above_long_average
        ):
            return self._result("Bear", row, period_return, drawdown)

        if period_return >= 2 or (
            trend == "Bullish" and above_short_average
        ):
            return self._result("Bull", row, period_return, drawdown)

        return self._result("Sideways", row, period_return, drawdown)

    def classify_period(self, rows):
        if not rows:
            return self._result("Sideways", {}, 0, 0)

        sorted_rows = sorted(rows, key=lambda row: (row.get("date", ""), row.get("ticker", "")))
        first_price = sorted_rows[0].get("price", sorted_rows[0].get("close", 0))
        last_price = sorted_rows[-1].get("price", sorted_rows[-1].get("close", 0))
        period_return = self._percentage(last_price, first_price)
        closes = [
            row.get("price", row.get("close"))
            for row in sorted_rows
            if row.get("price", row.get("close")) is not None
        ]
        drawdown = self._max_drawdown(closes)
        average_volatility = self._average([
            row.get("volatility", 0) or 0 for row in sorted_rows
        ])
        average_price_vs_20ma = self._average([
            row.get("price_vs_20ma", 0) or 0 for row in sorted_rows
        ])
        average_price_vs_50ma = self._average([
            row.get("price_vs_50ma", 0) or 0 for row in sorted_rows
        ])
        row = {
            "month_return": period_return,
            "volatility": average_volatility,
            "price_vs_20ma": average_price_vs_20ma,
            "price_vs_50ma": average_price_vs_50ma,
            "trend": "Bullish" if period_return >= 0 else "Bearish",
            "drawdown": drawdown,
        }

        return self.classify_row(row)

    def _result(self, regime, row, period_return, drawdown):
        return {
            "regime": regime,
            "trend": row.get("trend", "Neutral"),
            "volatility": round(row.get("volatility", 0) or 0, 4),
            "drawdown": round(drawdown, 4),
            "period_return": round(period_return, 4),
            "price_vs_20ma": round(row.get("price_vs_20ma", 0) or 0, 4),
            "price_vs_50ma": round(row.get("price_vs_50ma", 0) or 0, 4),
        }

    def _period_return(self, row):
        if row.get("month_return") is not None:
            return row.get("month_return") or 0

        if row.get("week_return") is not None:
            return row.get("week_return") or 0

        return self._percentage(row.get("future_price", 0), row.get("price", 0))

    def _drawdown(self, row):
        if row.get("drawdown") is not None:
            return row.get("drawdown") or 0

        price_vs_20ma = row.get("price_vs_20ma", 0) or 0
        price_vs_50ma = row.get("price_vs_50ma", 0) or 0

        return min(0, price_vs_20ma, price_vs_50ma)

    def _max_drawdown(self, values):
        if not values:
            return 0

        peak = values[0]
        drawdowns = []

        for value in values:
            peak = max(peak, value)
            drawdowns.append(self._percentage(value, peak))

        return min(drawdowns)

    def _percentage(self, current, previous):
        if not previous:
            return 0

        return round((current - previous) / previous * 100, 4)

    def _average(self, values):
        cleaned = [value for value in values if value is not None]

        if not cleaned:
            return 0

        return round(sum(cleaned) / len(cleaned), 4)
