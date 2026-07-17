import os

from engines.fred_provider import FredProvider
from engines.mock_macro_provider import MockMacroProvider


class MacroEngine:
    DEFAULT_PROVIDER = "mock"

    def __init__(self, provider_name=None, provider=None):
        self.provider_name = provider_name or os.environ.get(
            "MACRO_PROVIDER",
            self.DEFAULT_PROVIDER,
        )
        self.provider = provider or self._provider(self.provider_name)

    def analyze(self):
        indicators = self.provider.get_indicators()
        pressures = self._pressures(indicators)
        macro_risk_score = self._macro_risk_score(pressures)
        regime = self._regime(pressures, macro_risk_score)

        return {
            "provider": self.provider.provider_name,
            "indicators": indicators,
            "current_macro_regime": regime,
            "inflation_pressure": pressures["inflation_pressure"],
            "rate_pressure": pressures["rate_pressure"],
            "growth_pressure": pressures["growth_pressure"],
            "recession_risk": pressures["recession_risk"],
            "macro_risk_score": macro_risk_score,
            "summary": self._summary(regime, pressures, macro_risk_score),
            "health": self.health_check(),
            "policy": {
                "read_only": True,
                "mock_default": True,
                "requires_api_key": False,
                "changes_recommendation_behavior": False,
                "automatic_execution": False,
            },
        }

    def summary(self):
        report = self.analyze()

        return {
            "provider": report["provider"],
            "current_macro_regime": report["current_macro_regime"],
            "inflation_pressure": report["inflation_pressure"],
            "rate_pressure": report["rate_pressure"],
            "growth_pressure": report["growth_pressure"],
            "recession_risk": report["recession_risk"],
            "macro_risk_score": report["macro_risk_score"],
            "summary": report["summary"],
            "indicator_count": len(report["indicators"]),
        }

    def observatory_summary(self):
        report = self.analyze()
        health = report["health"]

        return {
            "provider": health["provider"],
            "status": health["status"],
            "healthy": health["healthy"],
            "fallback_used": health["fallback_used"],
            "indicator_count": len(report["indicators"]),
            "current_macro_regime": report["current_macro_regime"],
            "macro_risk_score": report["macro_risk_score"],
            "offline_capable": health["supports_offline"],
            "requires_api_key": health["requires_api_key"],
            "policy": (
                "Macro intelligence is read-only and does not change "
                "recommendation behavior."
            ),
        }

    def knowledge_graph_context(self):
        report = self.analyze()
        macro_id = "macro:current"

        return {
            "nodes": [
                {
                    "id": macro_id,
                    "type": "Macro Regime",
                    "label": report["current_macro_regime"],
                    "properties": report,
                },
                *[
                    {
                        "id": f"macro_indicator:{indicator['indicator']}",
                        "type": "Macro Indicator",
                        "label": indicator["indicator"],
                        "properties": indicator,
                    }
                    for indicator in report["indicators"]
                ],
            ],
            "relationships": [
                {
                    "source": macro_id,
                    "target": f"macro_indicator:{indicator['indicator']}",
                    "type": "uses_macro_indicator",
                    "properties": {"value": indicator["value"]},
                }
                for indicator in report["indicators"]
            ],
        }

    def health_check(self):
        return self.provider.health_check()

    def _provider(self, provider_name):
        if provider_name == "fred":
            return FredProvider()

        return MockMacroProvider()

    def _pressures(self, indicators):
        values = {item["indicator"]: item["value"] for item in indicators}
        cpi = values.get("CPI", 0)
        fed_funds = values.get("Fed Funds Rate", 0)
        unemployment = values.get("Unemployment", 0)
        gdp = values.get("GDP Growth", 0)
        ten_year = values.get("10Y Treasury Yield", 0)
        curve = values.get("Yield Curve Spread", 0)

        return {
            "inflation_pressure": self._level(cpi, 2.5, 4.0),
            "rate_pressure": self._level(max(fed_funds, ten_year), 3.5, 5.0),
            "growth_pressure": (
                "Weak" if gdp < 1.0 else "Moderate" if gdp < 3.0 else "Strong"
            ),
            "recession_risk": (
                "High"
                if curve < -0.75 or (unemployment >= 5.0 and gdp < 1.0)
                else "Elevated"
                if curve < 0 or unemployment >= 4.5
                else "Low"
            ),
        }

    def _macro_risk_score(self, pressures):
        score = 20
        score += {"Low": 5, "Moderate": 15, "High": 25}.get(
            pressures["inflation_pressure"],
            10,
        )
        score += {"Low": 5, "Moderate": 15, "High": 25}.get(
            pressures["rate_pressure"],
            10,
        )
        score += {"Strong": 5, "Moderate": 10, "Weak": 20}.get(
            pressures["growth_pressure"],
            10,
        )
        score += {"Low": 5, "Elevated": 15, "High": 25}.get(
            pressures["recession_risk"],
            10,
        )

        return min(100, score)

    def _regime(self, pressures, score):
        if score >= 75:
            return "Restrictive High-Risk"

        if pressures["inflation_pressure"] == "High":
            return "Inflation Pressure"

        if pressures["recession_risk"] in {"Elevated", "High"}:
            return "Late Cycle"

        if pressures["growth_pressure"] == "Strong":
            return "Expansion"

        return "Balanced"

    def _summary(self, regime, pressures, score):
        return (
            f"Macro regime is {regime} with risk score {score}. "
            f"Inflation pressure is {pressures['inflation_pressure']}, "
            f"rate pressure is {pressures['rate_pressure']}, growth pressure "
            f"is {pressures['growth_pressure']}, and recession risk is "
            f"{pressures['recession_risk']}."
        )

    def _level(self, value, moderate_threshold, high_threshold):
        if value >= high_threshold:
            return "High"

        if value >= moderate_threshold:
            return "Moderate"

        return "Low"
