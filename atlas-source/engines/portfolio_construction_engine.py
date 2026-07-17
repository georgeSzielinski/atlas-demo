class PortfolioConstructionEngine:
    DEFAULT_CONSTRAINTS = {
        "max_single_position": 20,
        "max_sector_allocation": 35,
        "min_cash": 5,
        "max_portfolio_beta": 1.15,
        "max_volatility": 18,
        "max_drawdown_target": -12,
        "max_correlation_placeholder": 0.65,
        "target_diversification_score": 75,
        "target_number_of_positions": 8,
    }

    SCENARIOS = {
        "Bull": 1.18,
        "Bear": 0.72,
        "Sideways": 0.94,
        "High Volatility": 0.78,
        "Low Volatility": 1.04,
        "Rising Rates": 0.88,
        "Falling Rates": 1.08,
    }

    def build(
        self,
        recommendations=None,
        paper_portfolio=None,
        macro_state=None,
        probabilities=None,
        risk_metrics=None,
        constraints=None,
    ):
        recommendations = recommendations or self.demo_recommendations()
        paper_portfolio = paper_portfolio or self.demo_portfolio()
        macro_state = macro_state or {}
        probabilities = probabilities or []
        risk_metrics = risk_metrics or {}
        constraints = constraints or self.DEFAULT_CONSTRAINTS
        portfolio = self._portfolio_state(paper_portfolio)
        probability_map = {
            item.get("ticker"): item
            for item in probabilities
            if item.get("ticker")
        }
        allocations = self.recommended_allocations(
            recommendations,
            portfolio,
            macro_state,
            probability_map,
            constraints,
        )
        diversification = self.diversification_analysis(portfolio, allocations)
        risk_budget = self.risk_budget(allocations, diversification, risk_metrics)
        rebalance = self.rebalance_recommendations(
            allocations,
            portfolio,
            diversification,
            risk_budget,
            constraints,
        )
        scenarios = self.scenario_analysis(allocations, macro_state)
        construction = {
            "recommended_allocations": allocations,
            "capital_allocation_ranking": self.capital_allocation_ranking(
                allocations
            ),
            "portfolio_actions": rebalance,
            "risk_summary": risk_budget["summary"],
            "risk_budget": risk_budget,
            "diversification": diversification,
            "constraints": constraints,
            "scenario_analysis": scenarios,
            "scientific_validation": self.scientific_validation_candidate(
                allocations,
                diversification,
                risk_budget,
            ),
            "operations_summary": self.operations_summary(
                portfolio,
                diversification,
                risk_budget,
                rebalance,
            ),
            "policy": self.policy(),
        }

        return construction

    def recommended_allocations(
        self,
        recommendations,
        portfolio,
        macro_state,
        probability_map,
        constraints,
    ):
        total_value = portfolio["portfolio_value"]
        cash = portfolio["cash"]
        macro_risk = macro_state.get("macro_risk_score", 50)
        buy_like = [
            item for item in recommendations
            if item.get("action", "").upper() in {"BUY", "HOLD"}
        ]
        scored = []

        for recommendation in buy_like:
            ticker = recommendation.get("ticker", "").upper()
            conviction = self._conviction(recommendation)
            probability = self._probability_score(probability_map.get(ticker, {}))
            knowledge = recommendation.get("knowledge_score", 50) or 50
            stability = recommendation.get("stability_score", 50) or 50
            raw_score = (
                conviction * 0.40
                + probability * 0.25
                + knowledge * 0.18
                + stability * 0.17
            )
            macro_adjustment = max(0.70, 1 - max(0, macro_risk - 50) / 200)
            scored.append({
                "recommendation": recommendation,
                "ticker": ticker,
                "score": round(raw_score * macro_adjustment, 4),
                "conviction": conviction,
                "probability": probability,
                "knowledge": knowledge,
                "stability": stability,
            })

        total_score = sum(item["score"] for item in scored) or 1
        deployable = max(
            0,
            100 - constraints["min_cash"] - portfolio["current_cash_percent"],
        )
        target_pool = min(100 - constraints["min_cash"], max(30, deployable + 35))
        allocations = []

        for index, item in enumerate(
            sorted(scored, key=lambda row: (-row["score"], row["ticker"])),
            start=1,
        ):
            recommendation = item["recommendation"]
            base_weight = item["score"] / total_score * target_pool
            suggested = min(constraints["max_single_position"], base_weight)
            current_weight = portfolio["position_weights"].get(item["ticker"], 0)
            confidence_allocation = suggested * item["conviction"] / 100
            probability_allocation = suggested * item["probability"] / 100
            knowledge_allocation = suggested * item["knowledge"] / 100
            stability_allocation = suggested * item["stability"] / 100
            expected_return = self._expected_return(recommendation, item)
            expected_risk = self._expected_risk(recommendation, item, macro_risk)

            allocations.append({
                "ticker": item["ticker"],
                "action": recommendation.get("action", "HOLD"),
                "sector": recommendation.get("sector", "Unknown"),
                "industry": recommendation.get("industry", "Unknown"),
                "country": recommendation.get("country", "US"),
                "factor": self._factor(recommendation),
                "market_cap": recommendation.get("market_cap_bucket", "Large"),
                "suggested_allocation": round(suggested, 2),
                "minimum_allocation": round(max(0, suggested * 0.50), 2),
                "maximum_allocation": round(
                    min(constraints["max_single_position"], suggested * 1.35),
                    2,
                ),
                "current_allocation": round(current_weight, 2),
                "position_priority": self._priority_label(index),
                "capital_required": round(total_value * suggested / 100, 2),
                "expected_contribution": round(
                    suggested * expected_return / 100,
                    4,
                ),
                "expected_risk_contribution": round(
                    suggested * expected_risk / 100,
                    4,
                ),
                "confidence_adjusted_allocation": round(confidence_allocation, 2),
                "probability_adjusted_allocation": round(probability_allocation, 2),
                "knowledge_adjusted_allocation": round(knowledge_allocation, 2),
                "stability_adjusted_allocation": round(stability_allocation, 2),
                "allocation_score": round(item["score"], 2),
                "requires_human_approval": True,
            })

        return allocations

    def risk_budget(self, allocations, diversification, risk_metrics):
        rows = []

        for allocation in allocations:
            volatility = self._volatility_for(allocation)
            rows.append({
                "ticker": allocation["ticker"],
                "risk_contribution": allocation["expected_risk_contribution"],
                "expected_return_contribution": allocation["expected_contribution"],
                "volatility_contribution": round(
                    allocation["suggested_allocation"] * volatility / 100,
                    4,
                ),
                "risk_level": self._risk_label(volatility),
            })

        total_risk = round(sum(item["risk_contribution"] for item in rows), 4)
        portfolio_volatility = risk_metrics.get(
            "volatility",
            round(sum(item["volatility_contribution"] for item in rows), 4),
        )
        drawdown = risk_metrics.get("max_drawdown", -abs(total_risk))
        level = self._portfolio_risk_level(
            total_risk,
            portfolio_volatility,
            diversification["concentration_score"],
        )

        return {
            "summary": {
                "risk_budget": level,
                "total_risk_contribution": total_risk,
                "portfolio_volatility": portfolio_volatility,
                "drawdown_target": drawdown,
                "portfolio_beta": risk_metrics.get("beta", 1.0),
            },
            "holdings": rows,
            "policy": self.policy(),
        }

    def diversification_analysis(self, portfolio, allocations):
        sector = self._exposure(allocations, "sector")
        industry = self._exposure(allocations, "industry")
        country = self._exposure(allocations, "country")
        factor = self._exposure(allocations, "factor")
        market_cap = self._exposure(allocations, "market_cap")
        largest = max(
            [item["suggested_allocation"] for item in allocations],
            default=0,
        )
        cash_allocation = max(
            0,
            100 - sum(item["suggested_allocation"] for item in allocations),
        )
        sector_penalty = max(sector.values(), default=0)
        position_count = len(allocations)
        diversification_score = round(
            max(
                0,
                min(
                    100,
                    55
                    + min(position_count, 10) * 4
                    + min(cash_allocation, 10)
                    - max(0, largest - 15) * 1.5
                    - max(0, sector_penalty - 35),
                ),
            ),
            2,
        )
        concentration_score = round(
            min(100, largest * 2 + max(0, sector_penalty - 25)),
            2,
        )

        return {
            "sector_exposure": sector,
            "industry_exposure": industry,
            "country_exposure": country,
            "factor_exposure": factor,
            "market_cap_exposure": market_cap,
            "etf_overlap": self._etf_overlap(allocations),
            "cash_allocation": round(cash_allocation, 2),
            "largest_position": round(largest, 2),
            "most_concentrated_sector": self._largest_key(sector),
            "diversification_score": diversification_score,
            "concentration_score": concentration_score,
            "portfolio_health": self._portfolio_health(
                diversification_score,
                concentration_score,
                cash_allocation,
            ),
        }

    def rebalance_recommendations(
        self,
        allocations,
        portfolio,
        diversification,
        risk_budget,
        constraints,
    ):
        actions = []

        for allocation in allocations:
            delta = (
                allocation["suggested_allocation"]
                - allocation["current_allocation"]
            )
            action = "Maintain"
            explanation = "Current paper weight is close to suggested allocation."

            if allocation["action"].upper() == "AVOID":
                action = "Exit"
                explanation = "Recommendation is AVOID; do not allocate new capital."
            elif delta >= 3:
                action = "Increase"
                explanation = (
                    "Suggested allocation is materially above current paper weight."
                )
            elif delta <= -3:
                action = "Reduce"
                explanation = (
                    "Suggested allocation is materially below current paper weight."
                )

            actions.append({
                "ticker": allocation["ticker"],
                "action": action,
                "current_allocation": allocation["current_allocation"],
                "target_allocation": allocation["suggested_allocation"],
                "explanation": explanation,
                "requires_human_approval": True,
            })

        if diversification["cash_allocation"] < constraints["min_cash"]:
            actions.append({
                "ticker": "CASH",
                "action": "Raise Cash",
                "current_allocation": portfolio["current_cash_percent"],
                "target_allocation": constraints["min_cash"],
                "explanation": "Cash is below the deterministic minimum cash buffer.",
                "requires_human_approval": True,
            })

        if diversification["diversification_score"] < constraints[
            "target_diversification_score"
        ]:
            actions.append({
                "ticker": "PORTFOLIO",
                "action": "Diversify",
                "current_allocation": diversification["diversification_score"],
                "target_allocation": constraints["target_diversification_score"],
                "explanation": "Diversification score is below institutional target.",
                "requires_human_approval": True,
            })

        if risk_budget["summary"]["risk_budget"] in {"Elevated", "High"}:
            actions.append({
                "ticker": "PORTFOLIO",
                "action": "Rebalance",
                "current_allocation": risk_budget["summary"][
                    "total_risk_contribution"
                ],
                "target_allocation": "Moderate risk budget",
                "explanation": "Risk budget is above the preferred moderate range.",
                "requires_human_approval": True,
            })

        return actions

    def capital_allocation_ranking(self, allocations):
        return [
            dict(allocation) | {
                "rank": index,
                "priority": self._priority_label(index),
            }
            for index, allocation in enumerate(
                sorted(
                    allocations,
                    key=lambda item: (
                        -item["suggested_allocation"],
                        -item["allocation_score"],
                        item["ticker"],
                    ),
                ),
                start=1,
            )
        ]

    def scenario_analysis(self, allocations, macro_state):
        current_regime = macro_state.get("current_macro_regime", "Unknown")
        base_return = sum(item["expected_contribution"] for item in allocations)

        return [
            {
                "scenario": scenario,
                "estimated_return_effect": round(base_return * multiplier, 4),
                "allocation_appropriate": (
                    multiplier >= 0.85
                    and sum(
                        item["suggested_allocation"] for item in allocations
                    ) <= 95
                ),
                "explanation": (
                    f"Current macro regime is {current_regime}; scenario "
                    f"multiplier is {multiplier}."
                ),
            }
            for scenario, multiplier in self.SCENARIOS.items()
        ]

    def scientific_validation_candidate(
        self,
        allocations,
        diversification,
        risk_budget,
    ):
        decision = "RETEST"

        if (
            diversification["diversification_score"] >= 80
            and risk_budget["summary"]["risk_budget"] in {"Low", "Moderate"}
        ):
            decision = "ADOPT"
        elif risk_budget["summary"]["risk_budget"] == "High":
            decision = "REJECT"

        return {
            "candidate_strategy": "Institutional Portfolio Construction v1",
            "baseline": "Equal weight paper portfolio",
            "simulation_arena_required": True,
            "scientific_validation_required": True,
            "adoption_decision": decision,
            "policy": (
                "Candidate allocations are research-only until Simulation Arena "
                "and Scientific Validation support adoption."
            ),
        }

    def operations_summary(self, portfolio, diversification, risk_budget, rebalance):
        largest_action = rebalance[0] if rebalance else {}

        return {
            "portfolio_health": diversification["portfolio_health"],
            "risk_budget": risk_budget["summary"]["risk_budget"],
            "largest_position": diversification["largest_position"],
            "most_concentrated_sector": diversification["most_concentrated_sector"],
            "diversification_score": diversification["diversification_score"],
            "cash": portfolio["cash"],
            "suggested_rebalance": largest_action.get("action", "Maintain"),
        }

    def demo_recommendations(self):
        return [
            {
                "ticker": "AAPL",
                "action": "BUY",
                "confidence": 88,
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "knowledge_score": 82,
                "stability_score": 78,
                "portfolio_score": 75,
            },
            {
                "ticker": "MSFT",
                "action": "HOLD",
                "confidence": 80,
                "sector": "Technology",
                "industry": "Software",
                "knowledge_score": 85,
                "stability_score": 84,
                "portfolio_score": 72,
            },
            {
                "ticker": "NVDA",
                "action": "BUY",
                "confidence": 84,
                "sector": "Semiconductors",
                "industry": "Semiconductors",
                "knowledge_score": 76,
                "stability_score": 70,
                "portfolio_score": 68,
            },
        ]

    def demo_portfolio(self):
        return {
            "cash": 76250,
            "portfolio_value": 100592,
            "positions": {},
        }

    def policy(self):
        return {
            "paper_only": True,
            "broker_integration": False,
            "real_money": False,
            "automatic_execution": False,
            "changes_recommendation_behavior": False,
            "human_approval_required": True,
            "deterministic": True,
        }

    def _portfolio_state(self, portfolio):
        positions = portfolio.get("positions", {})
        if isinstance(positions, dict):
            rows = list(positions.values())
        else:
            rows = positions

        total_value = portfolio.get("portfolio_value") or (
            portfolio.get("cash", 0)
            + sum(self._position_value(position) for position in rows)
        )
        position_weights = {
            position.get("ticker", "").upper(): self._rate(
                self._position_value(position),
                total_value,
            )
            for position in rows
        }

        return {
            "cash": portfolio.get("cash", 0),
            "portfolio_value": total_value,
            "positions": rows,
            "position_weights": position_weights,
            "current_cash_percent": self._rate(portfolio.get("cash", 0), total_value),
        }

    def _position_value(self, position):
        return position.get(
            "current_value",
            position.get("value", position.get("market_value", 0)),
        )

    def _conviction(self, recommendation):
        return (
            recommendation.get("overall_conviction")
            or recommendation.get("confidence")
            or recommendation.get("overall_score")
            or 50
        )

    def _probability_score(self, report):
        probabilities = report.get("probabilities", {})
        return (
            probabilities.get("outperformance")
            or probabilities.get("positive")
            or 50
        )

    def _expected_return(self, recommendation, item):
        return round(
            max(
                2,
                (
                    item["conviction"] * 0.06
                    + item["probability"] * 0.04
                    + recommendation.get("portfolio_score", 50) * 0.03
                ),
            ),
            2,
        )

    def _expected_risk(self, recommendation, item, macro_risk):
        return round(
            max(
                5,
                24
                - item["stability"] * 0.09
                - item["knowledge"] * 0.05
                + macro_risk * 0.04
                + (100 - item["probability"]) * 0.03,
            ),
            2,
        )

    def _factor(self, recommendation):
        action = recommendation.get("action", "").upper()
        if recommendation.get("factor"):
            return recommendation["factor"]
        if recommendation.get("stability_score", 0) >= 80:
            return "Quality"
        if action == "BUY":
            return "Growth"
        return "Core"

    def _volatility_for(self, allocation):
        return {
            "Quality": 14,
            "Core": 12,
            "Growth": 21,
        }.get(allocation.get("factor"), 18)

    def _risk_label(self, volatility):
        if volatility < 13:
            return "Low"
        if volatility < 18:
            return "Moderate"
        if volatility < 23:
            return "Elevated"
        return "High"

    def _portfolio_risk_level(self, total_risk, volatility, concentration):
        score = total_risk + volatility * 0.35 + concentration * 0.08
        if score < 9:
            return "Low"
        if score < 14:
            return "Moderate"
        if score < 20:
            return "Elevated"
        return "High"

    def _priority_label(self, index):
        labels = {
            1: "Highest Priority",
            2: "Second Priority",
            3: "Third Priority",
        }
        return labels.get(index, f"Priority {index}")

    def _exposure(self, allocations, key):
        exposure = {}

        for allocation in allocations:
            name = allocation.get(key) or "Unknown"
            exposure[name] = round(
                exposure.get(name, 0) + allocation["suggested_allocation"],
                2,
            )

        return dict(sorted(exposure.items(), key=lambda item: (-item[1], item[0])))

    def _etf_overlap(self, allocations):
        broad = [
            item for item in allocations
            if item["ticker"] in {"VOO", "SPY", "QQQ", "VTI"}
        ]
        return {
            "overlap_placeholder": round(
                sum(item["suggested_allocation"] for item in broad),
                2,
            ),
            "policy": "Placeholder only; requires holdings-level validation.",
        }

    def _largest_key(self, values):
        if not values:
            return None

        return sorted(values.items(), key=lambda item: (-item[1], item[0]))[0][0]

    def _portfolio_health(self, diversification_score, concentration_score, cash):
        score = diversification_score - concentration_score * 0.25 + min(cash, 10)
        if score >= 80:
            return "Strong"
        if score >= 65:
            return "Healthy"
        if score >= 50:
            return "Watch"
        return "Concentrated"

    def _rate(self, numerator, denominator):
        if not denominator:
            return 0
        return round(numerator / denominator * 100, 4)
