class ReportEngine:

    def print_header(self):
        print("=" * 50)
        print("               ATLAS")
        print("     AI Investment Research Platform")
        print("=" * 50)

    def print_market_summary(self, results):
        print("\nMarket Summary")
        print("-" * 50)

        average_rsi = sum(stock.rsi for stock in results) / len(results)
        average_volatility = sum(stock.volatility for stock in results) / len(results)

        print(f"Average RSI: {average_rsi:.1f}")
        print(f"Average Volatility: {average_volatility:.2f}%")

    def print_recommendations(self, results, decision_engine):
        print("\nRecommendations")
        print("-" * 50)

        for stock in results:
            recommendation = decision_engine.decide(stock)

            print(
                f"{stock.ticker:6} | "
                f"{recommendation:5} | "
                f"Score: {stock.score}"
            )