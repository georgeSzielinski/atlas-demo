from engines.macro_provider import MacroProvider
from engines.mock_macro_provider import MockMacroProvider


class FredProvider(MacroProvider):
    provider_name = "fred"

    def __init__(self):
        self.fallback_provider = MockMacroProvider()
        self.fallback_used = False
        self.last_error = ""

    def get_indicators(self):
        try:
            raise RuntimeError(
                "FRED provider is registered for future integration and "
                "is not active in offline mode."
            )
        except Exception as error:
            self.fallback_used = True
            self.last_error = str(error)

            return self.fallback_provider.get_indicators()

    def health_check(self):
        return {
            "provider": self.provider_name,
            "status": "Experimental",
            "healthy": False,
            "fallback_used": self.fallback_used,
            "indicator_count": len(self.INDICATORS),
            "indicators": self.INDICATORS,
            "supports_offline": False,
            "requires_api_key": False,
            "failure_message": self.last_error
            or "FRED provider is not active in offline mode.",
        }
