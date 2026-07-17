import math


class PortfolioStrategyEngine:
    DEFAULT_PORTFOLIO = {
        "cash": 15000,
        "positions": [
            {
                "ticker": "VOO",
                "value": 40000,
                "sector": "Broad Market",
                "factor": "Core",
                "expected_return": 7,
                "volatility": 14,
            },
            {
                "ticker": "QQQ",
                "value": 25000,
                "sector": "Technology",
                "factor": "Growth",
                "expected_return": 9,
                "volatility": 20,
            },
            {
                "ticker": "AAPL",
                "value": 20000,
                "sector": "Technology",
                "factor": "Quality",
                "expected_return": 8,
                "volatility": 22,
            },
        ],
    }

    def review(self, portfolio=None, replay_rows=None):
        portfolio = portfolio or self.DEFAULT_PORTFOLIO
        analysis = self.analyze_portfolio(portfolio)
        strategy = self.strategy_recommendations(analysis)
        simulation = self.simulate_portfolios(portfolio, strategy)
        replay = self.historical_replay(
            replay_rows or self._default_replay_rows()
        )
        case_study = self.portfolio_case_study(analysis, simulation, replay)
        construction = self.construction_review(portfolio)

        return {
            "analysis": analysis,
            "strategy_recommendations": strategy,
            "portfolio_construction": construction,
            "simulation": simulation,
            "historical_replay": replay,
            "case_study": case_study,
            "controlled_decision": {
                "read_only": True,
                "executes_trades": False,
                "connects_brokers": False,
                "requires_human_approval": True,
            },
        }

    def construction_review(self, portfolio=None, recommendations=None):
        from engines.portfolio_construction_engine import PortfolioConstructionEngine

        engine = PortfolioConstructionEngine()

        return engine.build(
            recommendations=recommendations or engine.demo_recommendations(),
            paper_portfolio=portfolio or self.DEFAULT_PORTFOLIO,
        )

    def analyze_portfolio(self, portfolio):
        positions = portfolio.get("positions", [])
        cash = portfolio.get("cash", 0)
        position_values = [self._position_value(position) for position in positions]
        total_value = cash + sum(position_values)
        weighted_positions = [
            {
                **position,
                "value": self._position_value(position),
                "weight": self._rate(
                    self._position_value(position),
                    total_value,
                ),
            }
            for position in positions
        ]
        sector_exposure = self._exposure(weighted_positions, "sector")
        factor_exposure = self._exposure(weighted_positions, "factor")
        largest_position = max(
            [position["weight"] for position in weighted_positions],
            default=0,
        )
        expected_return = self._weighted_average(
            weighted_positions,
            "expected_return",
        )
        expected_volatility = self._expected_volatility(weighted_positions)

        return {
            "total_value": round(total_value, 2),
            "cash": cash,
            "cash_percentage": self._rate(cash, total_value),
            "positions": weighted_positions,
            "sector_exposure": sector_exposure,
            "factor_exposure": factor_exposure,
            "concentration": {
                "largest_position": largest_position,
                "top_three": round(
                    sum(sorted(
                        [position["weight"] for position in weighted_positions],
                        reverse=True,
                    )[:3]),
                    2,
                ),
                "hhi": round(sum([
                    position["weight"] ** 2
                    for position in weighted_positions
                ]), 2),
            },
            "diversification": self._diversification_score(
                weighted_positions,
                sector_exposure,
                largest_position,
            ),
            "position_overlap": self._position_overlap(weighted_positions),
            "risk": self._risk_label(largest_position, expected_volatility),
            "expected_return": expected_return,
            "expected_volatility": expected_volatility,
            "sharpe_estimate": self._sharpe(expected_return, expected_volatility),
        }

    def strategy_recommendations(self, analysis):
        recommendations = []

        for position in analysis["positions"]:
            action = "Maintain"
            reason = "Position is within deterministic portfolio limits."

            if position.get("expected_return", 0) < 4:
                action = "Replace"
                reason = "Expected return is weak."
            elif position["weight"] > 30:
                action = "Reduce"
                reason = "Position concentration is high."
            elif position.get("expected_return", 0) >= 8 and position["weight"] < 25:
                action = "Increase"
                reason = "Expected return is strong and weight is controlled."

            recommendations.append({
                "ticker": position.get("ticker", ""),
                "action": action,
                "reason": reason,
                "requires_human_approval": True,
            })

        for sector, weight in analysis["sector_exposure"].items():
            if weight > 45:
                recommendations.append({
                    "ticker": "PORTFOLIO",
                    "action": "Diversify",
                    "reason": f"{sector} exposure is above 45%.",
                    "requires_human_approval": True,
                })

        if analysis["cash_percentage"] < 5 and analysis["risk"] == "High":
            recommendations.append({
                "ticker": "CASH",
                "action": "Raise cash",
                "reason": "High risk portfolio has low cash buffer.",
                "requires_human_approval": True,
            })

        return recommendations

    def simulate_portfolios(self, portfolio, recommendations):
        current = self.analyze_portfolio(portfolio)
        adjustment_map = {
            item["ticker"]: item["action"]
            for item in recommendations
        }
        adjusted_positions = []
        cash = portfolio.get("cash", 0)

        for position in portfolio.get("positions", []):
            adjusted = dict(position)
            action = adjustment_map.get(position.get("ticker"), "Maintain")
            value = self._position_value(position)

            if action == "Increase":
                adjusted["value"] = round(value * 1.10, 2)
                cash -= adjusted["value"] - value
            elif action == "Reduce":
                adjusted["value"] = round(value * 0.85, 2)
                cash += value - adjusted["value"]
            elif action == "Replace":
                adjusted["value"] = 0
                cash += value
            else:
                adjusted["value"] = value

            if adjusted["value"] > 0:
                adjusted_positions.append(adjusted)

        atlas_portfolio = {
            "cash": round(max(0, cash), 2),
            "positions": adjusted_positions,
        }
        atlas = self.analyze_portfolio(atlas_portfolio)

        return {
            "current_portfolio": current,
            "atlas_portfolio": atlas,
            "difference": {
                "expected_return_delta": round(
                    atlas["expected_return"] - current["expected_return"],
                    2,
                ),
                "expected_volatility_delta": round(
                    atlas["expected_volatility"]
                    - current["expected_volatility"],
                    2,
                ),
                "sharpe_delta": round(
                    atlas["sharpe_estimate"] - current["sharpe_estimate"],
                    4,
                ),
                "cash_delta": round(
                    atlas["cash_percentage"] - current["cash_percentage"],
                    2,
                ),
            },
        }

    def historical_replay(self, replay_rows):
        current_returns = [
            row.get("current_return", 0) for row in replay_rows
        ]
        atlas_returns = [
            row.get("atlas_return", 0) for row in replay_rows
        ]

        return {
            "periods": len(replay_rows),
            "current_portfolio_return": self._compound_return(current_returns),
            "atlas_portfolio_return": self._compound_return(atlas_returns),
            "difference": round(
                self._compound_return(atlas_returns)
                - self._compound_return(current_returns),
                2,
            ),
            "atlas_outperformed": (
                self._compound_return(atlas_returns)
                > self._compound_return(current_returns)
            ),
        }

    def portfolio_case_study(self, analysis, simulation, replay):
        return {
            "case_type": "Portfolio Strategy",
            "outcome": (
                "Atlas Outperformed"
                if replay["atlas_outperformed"]
                else "Baseline Outperformed"
            ),
            "lessons_learned": [
                f"Risk level was {analysis['risk']}.",
                (
                    "Diversification improved."
                    if simulation["difference"]["expected_volatility_delta"] < 0
                    else "Diversification needs review."
                ),
                (
                    "Atlas portfolio beat baseline in replay."
                    if replay["atlas_outperformed"]
                    else "Baseline portfolio beat Atlas in replay."
                ),
            ],
            "requires_human_approval": True,
            "automatic_execution": False,
        }

    def research_summary(self, reviews):
        completed = [review for review in reviews if review.get("historical_replay")]
        outperformers = [
            review for review in completed
            if review["historical_replay"].get("atlas_outperformed")
        ]

        return {
            "sample_size": len(completed),
            "atlas_outperformance_rate": self._rate(
                len(outperformers),
                len(completed),
            ),
            "average_return_improvement": self._average([
                review["historical_replay"].get("difference", 0)
                for review in completed
            ]),
            "construction_research": {
                "candidate_strategy": "Institutional Portfolio Construction v1",
                "requires_simulation_arena": True,
                "requires_scientific_validation": True,
            },
            "policy": (
                "Portfolio strategy research is advisory and requires human "
                "approval before any allocation change."
            ),
        }

    def _default_replay_rows(self):
        return [
            {"period": "Q1", "current_return": 3.0, "atlas_return": 3.8},
            {"period": "Q2", "current_return": -2.0, "atlas_return": -1.2},
            {"period": "Q3", "current_return": 4.0, "atlas_return": 4.4},
            {"period": "Q4", "current_return": 1.0, "atlas_return": 1.3},
        ]

    def _position_value(self, position):
        if position.get("value") is not None:
            return position["value"]

        return position.get("shares", 0) * position.get("price", 0)

    def _exposure(self, positions, key):
        exposure = {}

        for position in positions:
            name = position.get(key, "Unknown")
            exposure[name] = exposure.get(name, 0) + position["weight"]

        return {
            name: round(weight, 2)
            for name, weight in sorted(exposure.items())
        }

    def _position_overlap(self, positions):
        overlaps = []

        for index, position in enumerate(positions):
            for other in positions[index + 1:]:
                shared = []
                if position.get("sector") == other.get("sector"):
                    shared.append("sector")
                if position.get("factor") == other.get("factor"):
                    shared.append("factor")

                if shared:
                    overlaps.append({
                        "tickers": [
                            position.get("ticker"),
                            other.get("ticker"),
                        ],
                        "shared": shared,
                    })

        return overlaps

    def _diversification_score(self, positions, sector_exposure, largest_position):
        score = len(positions) * 12 + len(sector_exposure) * 15
        score -= max(0, largest_position - 25)
        score -= max(0, max(sector_exposure.values(), default=0) - 40)

        return round(max(0, min(100, score)), 2)

    def _risk_label(self, largest_position, expected_volatility):
        if largest_position > 35 or expected_volatility > 20:
            return "High"

        if largest_position > 25 or expected_volatility > 14:
            return "Medium"

        return "Low"

    def _expected_volatility(self, positions):
        variance = sum([
            ((position["weight"] / 100) * position.get("volatility", 0)) ** 2
            for position in positions
        ])

        return round(math.sqrt(variance), 2)

    def _weighted_average(self, positions, key):
        return round(sum([
            position.get(key, 0) * position["weight"] / 100
            for position in positions
        ]), 2)

    def _sharpe(self, expected_return, expected_volatility):
        if expected_volatility == 0:
            return 0

        return round((expected_return - 2) / expected_volatility, 4)

    def _compound_return(self, returns):
        value = 1

        for item in returns:
            value *= 1 + item / 100

        return round((value - 1) * 100, 2)

    def _average(self, values):
        if not values:
            return 0

        return round(sum(values) / len(values), 2)

    def _rate(self, numerator, denominator):
        if denominator == 0:
            return 0

        return round(numerator / denominator * 100, 2)
