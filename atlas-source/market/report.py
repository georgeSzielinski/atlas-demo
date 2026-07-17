class ReportGenerator:

    def print_market_report(self, results):

        print("\n====================================")
        print("      MARKET INTELLIGENCE REPORT")
        print("====================================")

        for stock in results:
            print(stock.summary())