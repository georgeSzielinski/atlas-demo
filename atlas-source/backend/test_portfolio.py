from engines.portfolio_engine import PortfolioEngine

portfolio = PortfolioEngine()

portfolio.set_cash(1000)

portfolio.add_position("VOO", 2, 500)

portfolio.add_position("AAPL", 3, 200)

print("Cash:", portfolio.cash)

print("Positions:", portfolio.position_count())

print("Portfolio Value:", portfolio.portfolio_value())
