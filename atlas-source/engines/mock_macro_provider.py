from engines.macro_provider import MacroProvider


class MockMacroProvider(MacroProvider):
    provider_name = "mock"

    def __init__(self):
        self.fallback_used = False
        self.last_error = ""

    def get_indicators(self):
        return self.normalize_indicators([
            {
                "indicator": "CPI",
                "value": 3.2,
                "unit": "YoY %",
                "as_of_date": "2026-06-30",
                "frequency": "Monthly",
                "source": self.provider_name,
                "trend": "Elevated",
                "notes": "Deterministic mock inflation reading.",
            },
            {
                "indicator": "Fed Funds Rate",
                "value": 5.25,
                "unit": "%",
                "as_of_date": "2026-06-30",
                "frequency": "Policy",
                "source": self.provider_name,
                "trend": "Restrictive",
                "notes": "Deterministic mock policy rate.",
            },
            {
                "indicator": "Unemployment",
                "value": 4.1,
                "unit": "%",
                "as_of_date": "2026-06-30",
                "frequency": "Monthly",
                "source": self.provider_name,
                "trend": "Stable",
                "notes": "Deterministic mock labor reading.",
            },
            {
                "indicator": "GDP Growth",
                "value": 2.1,
                "unit": "Annualized %",
                "as_of_date": "2026-06-30",
                "frequency": "Quarterly",
                "source": self.provider_name,
                "trend": "Moderate",
                "notes": "Deterministic mock growth reading.",
            },
            {
                "indicator": "10Y Treasury Yield",
                "value": 4.35,
                "unit": "%",
                "as_of_date": "2026-06-30",
                "frequency": "Daily",
                "source": self.provider_name,
                "trend": "Elevated",
                "notes": "Deterministic mock long-rate reading.",
            },
            {
                "indicator": "Yield Curve Spread",
                "value": -0.45,
                "unit": "Percentage points",
                "as_of_date": "2026-06-30",
                "frequency": "Daily",
                "source": self.provider_name,
                "trend": "Inverted",
                "notes": "Deterministic mock 10Y minus 2Y spread.",
            },
        ])

    def health_check(self):
        return {
            "provider": self.provider_name,
            "status": "Mock",
            "healthy": True,
            "fallback_used": self.fallback_used,
            "indicator_count": len(self.INDICATORS),
            "indicators": self.INDICATORS,
            "supports_offline": True,
            "requires_api_key": False,
            "failure_message": self.last_error,
        }
