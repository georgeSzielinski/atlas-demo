import pandas as pd

def calculate_rsi(close_prices, period=14):

    delta = close_prices.diff()

    gains = delta.where(delta > 0, 0)

    losses = -delta.where(delta < 0, 0)

    average_gain = gains.rolling(period).mean()

    average_loss = losses.rolling(period).mean()

    rs = average_gain / average_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1]

def detect_trend(price_vs_20ma, price_vs_50ma, month_return, rsi):

    if price_vs_20ma > 0 and price_vs_50ma > 0 and month_return > 0 and rsi < 70:

        return "Bullish"

    if price_vs_20ma < 0 and price_vs_50ma < 0 and month_return < 0:

        return "Bearish"

    return "Neutral"

def calculate_macd(close_prices):
    ema_12 = close_prices.ewm(span=12, adjust=False).mean()
    ema_26 = close_prices.ewm(span=26, adjust=False).mean()

    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()

    macd_value = macd_line.iloc[-1]
    signal_value = signal_line.iloc[-1]

    if macd_value > signal_value:
        macd_signal = "Bullish"
    elif macd_value < signal_value:
        macd_signal = "Bearish"
    else:
        macd_signal = "Neutral"

    return {
        "macd": macd_value,
        "macd_signal": signal_value,
        "macd_trend": macd_signal
    }

def calculate_indicators(history):
    close = history["Close"]
    rsi = calculate_rsi(close)
    macd_data = calculate_macd(close)

    latest_price = close.iloc[-1]
    moving_average_20 = close.rolling(window=20).mean().iloc[-1]
    moving_average_50 = close.rolling(window=50).mean().iloc[-1]

    price_vs_20ma = ((latest_price - moving_average_20) / moving_average_20) * 100
    price_vs_50ma = ((latest_price - moving_average_50) / moving_average_50) * 100
    trend = detect_trend(price_vs_20ma, price_vs_50ma, close.pct_change(22).iloc[-1] * 100, rsi)
    daily_returns = close.pct_change()
    volatility = daily_returns.std() * 100

    return {
        "moving_average_20": moving_average_20,
        "moving_average_50": moving_average_50,
        "price_vs_20ma": price_vs_20ma,
        "price_vs_50ma": price_vs_50ma,
        "volatility": volatility,
        "rsi": rsi,
        "trend": trend,
        "macd": macd_data["macd"],
        "macd_signal": macd_data["macd_signal"],
        "macd_trend": macd_data["macd_trend"],
    }