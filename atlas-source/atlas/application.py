from services.investment_platform import InvestmentPlatform
from core.settings import APPROVED_TICKERS


class Atlas:

    def __init__(self):
        self.platform = InvestmentPlatform()

    def start(self):
        print("=" * 50)
        print("             ATLAS")
        print(" AI Investment Research Platform")
        print("=" * 50)

        self.platform.run(APPROVED_TICKERS)