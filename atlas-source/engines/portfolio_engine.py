class PortfolioEngine:

    def __init__(self):
        self.cash = 0.0
        self.positions = []

    def set_cash(self, amount):
        self.cash = amount

    def add_position(self, ticker, shares, average_price):
        self.positions.append({
            "ticker": ticker,
            "shares": shares,
            "average_price": average_price
        })

    def portfolio_value(self):
        total = self.cash

        for position in self.positions:
            total += position["shares"] * position["average_price"]

        return total

    def position_count(self):
        return len(self.positions)