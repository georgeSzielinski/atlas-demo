from engines.portfolio_engine import PortfolioEngine
from engines.risk_engine import RiskEngine

portfolio = PortfolioEngine()

portfolio.set_cash(1000)

portfolio.add_position("VOO", 2, 500)
portfolio.add_position("AAPL", 3, 200)

risk = RiskEngine()

print("Portfolio Risk:", risk.portfolio_risk(portfolio))
print("Cash %:", round(risk.cash_percentage(portfolio), 2))