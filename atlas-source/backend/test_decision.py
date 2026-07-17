from models.stock_analysis import StockAnalysis
from engines.decision_engine import DecisionEngine

stock = StockAnalysis(
    ticker="AAPL",
    asset_type="Stock",
    price=280,
    week_return=2,
    month_return=5,
    moving_average_20=275,
    moving_average_50=270,
    price_vs_20ma=2,
    price_vs_50ma=4,
    rsi=55,
    macd=1.2,
    macd_signal=1.0,
    macd_trend="Bullish",
    volatility=1.3,
    trend="Bullish",
    score=5
)

engine = DecisionEngine()

print(engine.decide(stock))