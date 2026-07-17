from dataclasses import dataclass, field

from models.investment_recommendation import InvestmentRecommendation


@dataclass
class Dashboard:

    title: str

    market_status: str

    average_rsi: float

    average_volatility: float

    recommendations: list[InvestmentRecommendation] = field(default_factory=list)

    version: str = "Atlas v0.4"

    def display(self):

        print("=" * 60)
        print(self.title)
        print(self.version)
        print("=" * 60)

        print(f"\nMarket Status: {self.market_status}")
        print(f"Average RSI: {self.average_rsi:.1f}")
        print(f"Average Volatility: {self.average_volatility:.2f}%")

        print("\nTop Recommendations")
        print("-" * 60)

        for recommendation in self.recommendations:
            print(recommendation.summary())