from core.settings import APPROVED_ETFS
from market.data import get_market_data
from ai.analyzer import analyze_stock
from models.stock_analysis import StockAnalysis


class MarketAnalyzer:

    def analyze_ticker(self, ticker):
        data = get_market_data(ticker)

        asset_type = "ETF" if ticker in APPROVED_ETFS else "Stock"

        score = analyze_stock(
            data["ticker"],
            data["week_return"],
            data["month_return"],
            data["volatility"]
        )

        return StockAnalysis(
            ticker=data["ticker"],
            asset_type=asset_type,
            price=data["price"],
            week_return=data["week_return"],
            month_return=data["month_return"],
            moving_average_20=data["moving_average_20"],
            moving_average_50=data["moving_average_50"],
            price_vs_20ma=data["price_vs_20ma"],
            price_vs_50ma=data["price_vs_50ma"],
            rsi=data["rsi"],
            macd=data["macd"],
            macd_signal=data["macd_signal"],
            macd_trend=data["macd_trend"],
            volatility=data["volatility"],
            trend=data["trend"],
            score=score
        )

    def analyze_many(self, tickers):
        results = []

        for ticker in tickers:
            try:
                analysis = self.analyze_ticker(ticker)
                results.append(analysis)
            except Exception as error:
                print(f"Skipping ticker {ticker}: {error}")

        results.sort(key=lambda stock: stock.score, reverse=True)

        return results
