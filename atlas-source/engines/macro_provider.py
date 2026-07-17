class MacroProvider:
    provider_name = "base"
    fallback_used = False
    last_error = ""

    INDICATORS = [
        "CPI",
        "Fed Funds Rate",
        "Unemployment",
        "GDP Growth",
        "10Y Treasury Yield",
        "Yield Curve Spread",
    ]

    def get_indicators(self):
        raise NotImplementedError

    def health_check(self):
        raise NotImplementedError

    def normalize_indicators(self, indicators):
        normalized = []

        for indicator in indicators:
            name = indicator.get("indicator")
            if name not in self.INDICATORS:
                raise ValueError(f"Unsupported macro indicator: {name}")

            normalized.append({
                "indicator": name,
                "value": indicator.get("value", 0),
                "unit": indicator.get("unit", ""),
                "as_of_date": indicator.get("as_of_date", ""),
                "frequency": indicator.get("frequency", ""),
                "source": indicator.get("source", self.provider_name),
                "trend": indicator.get("trend", "Stable"),
                "notes": indicator.get("notes", ""),
            })

        return sorted(normalized, key=lambda item: item["indicator"])
