from engines.forecast_provider import ForecastProvider


class MockForecastProvider(ForecastProvider):

    def forecast(self, stock):
        ticker = stock.get("ticker") if isinstance(stock, dict) else getattr(
            stock,
            "ticker",
            stock
        )
        forecast_data = self._simulated_forecast(ticker)
        forecast_score = 50

        if forecast_data["direction"] == "Bullish":
            forecast_score += 20

        elif forecast_data["direction"] == "Bearish":
            forecast_score -= 20

        if forecast_data["confidence"] > 80:
            forecast_score += 20

        elif forecast_data["confidence"] < 40:
            forecast_score -= 10

        if forecast_data["expected_change"] > 3:
            forecast_score += 10

        forecast_data["forecast_score"] = max(0, min(100, forecast_score))

        return forecast_data

    def _simulated_forecast(self, stock):
        simulated_forecasts = {
            "VOO": {
                "direction": "Bullish",
                "confidence": 78,
                "expected_change": 3.2,
            },
            "VTI": {
                "direction": "Bullish",
                "confidence": 76,
                "expected_change": 2.9,
            },
            "QQQ": {
                "direction": "Bullish",
                "confidence": 82,
                "expected_change": 5.4,
            },
            "SCHD": {
                "direction": "Neutral",
                "confidence": 64,
                "expected_change": 1.2,
            },
            "AAPL": {
                "direction": "Bullish",
                "confidence": 74,
                "expected_change": 2.7,
            },
            "MSFT": {
                "direction": "Bullish",
                "confidence": 85,
                "expected_change": 4.1,
            },
            "NVDA": {
                "direction": "Bullish",
                "confidence": 88,
                "expected_change": 6.8,
            },
            "AMZN": {
                "direction": "Neutral",
                "confidence": 61,
                "expected_change": 1.8,
            },
            "GOOGL": {
                "direction": "Bullish",
                "confidence": 80,
                "expected_change": 3.5,
            },
            "COST": {
                "direction": "Bearish",
                "confidence": 52,
                "expected_change": -1.4,
            },
        }

        forecast = simulated_forecasts.get(stock, {
            "direction": "Neutral",
            "confidence": 50,
            "expected_change": 0,
        })

        return {
            "direction": forecast["direction"],
            "confidence": forecast["confidence"],
            "expected_change": forecast["expected_change"],
            "days": 7,
        }
