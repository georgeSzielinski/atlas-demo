from dataclasses import dataclass


@dataclass
class StockAnalysis:
    ticker: str
    asset_type: str

    price: float

    week_return: float
    month_return: float

    moving_average_20: float
    moving_average_50: float

    price_vs_20ma: float
    price_vs_50ma: float

    rsi: float

    macd: float
    macd_signal: float
    macd_trend: str

    volatility: float

    trend: str

    score: int = 0

    def summary(self):
        return (
            f"{self.ticker} | "
            f"Trend: {self.trend} | "
            f"RSI: {self.rsi:.1f} | "
            f"Score: {self.score}"
        )