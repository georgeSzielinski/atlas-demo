from api.main import macro_dashboard, macro_summary_dashboard
from backend.status import macro_provider_status
from engines.discovery_engine import DiscoveryEngine
from engines.fred_provider import FredProvider
from engines.knowledge_graph_engine import KnowledgeGraphEngine
from engines.macro_engine import MacroEngine
from engines.macro_provider import MacroProvider
from engines.mock_macro_provider import MockMacroProvider
from engines.performance_observatory import PerformanceObservatory
from market.provider_registry import ProviderRegistry


provider = MockMacroProvider()
indicators = provider.get_indicators()

assert [item["indicator"] for item in indicators] == sorted(MacroProvider.INDICATORS)
assert len(indicators) == 6
assert all("value" in item for item in indicators)
assert all("as_of_date" in item for item in indicators)
assert all(item["source"] == "mock" for item in indicators)

health = provider.health_check()
assert health["provider"] == "mock"
assert health["status"] == "Mock"
assert health["healthy"] is True
assert health["supports_offline"] is True
assert health["requires_api_key"] is False

engine = MacroEngine()
report = engine.analyze()
summary = engine.summary()

assert report["provider"] == "mock"
assert report["current_macro_regime"] == "Restrictive High-Risk"
assert report["inflation_pressure"] == "Moderate"
assert report["rate_pressure"] == "High"
assert report["growth_pressure"] == "Moderate"
assert report["recession_risk"] == "Elevated"
assert report["macro_risk_score"] == 85
assert "Macro regime is Restrictive High-Risk" in report["summary"]
assert report["policy"]["changes_recommendation_behavior"] is False
assert summary["indicator_count"] == 6

fred = FredProvider()
fred_indicators = fred.get_indicators()
fred_health = fred.health_check()

assert fred.fallback_used is True
assert fred_indicators == indicators
assert "not active in offline mode" in fred.last_error
assert fred_health["provider"] == "fred"
assert fred_health["status"] == "Experimental"
assert fred_health["healthy"] is False
assert fred_health["requires_api_key"] is False

registry = ProviderRegistry()
macro_providers = registry.by_category("Macro")
assert [provider["name"] for provider in macro_providers] == [
    "mock-macro",
    "fred-macro",
]
assert macro_providers[0]["status"] == "Mock"
assert macro_providers[0]["supports_offline"] is True
assert macro_providers[1]["status"] == "Experimental"
assert macro_providers[1]["requires_api_key"] is False
assert registry.active_providers()["Macro"] == "mock"
assert "fred-macro" in registry.summary()["experimental_providers"]

status = macro_provider_status()
assert status["provider"] == "mock"
assert status["status"] == "Mock"
assert status["healthy"] is True
assert status["macro_regime"] == "Restrictive High-Risk"
assert status["macro_risk_score"] == 85
assert status["requires_api_key"] is False

api_report = macro_dashboard()
api_summary = macro_summary_dashboard()
assert api_report["current_macro_regime"] == "Restrictive High-Risk"
assert api_report["macro_risk_score"] == 85
assert api_summary["summary"]["indicator_count"] == 6
assert api_summary["health"]["provider"] == "mock"
assert api_summary["policy"]["changes_recommendation_behavior"] is False

observatory = PerformanceObservatory().generate(
    source_data={
        "recommendations": [],
        "benchmark_results": [],
        "provider_results": [],
        "research_experiments": [],
    },
    discovery_data={
        "recent_discoveries": [],
        "top_discoveries": [],
        "discovery_history": [],
    },
)
assert observatory["macro_summary"]["provider"] == "mock"
assert observatory["macro_summary"]["macro_risk_score"] == 85
assert observatory["macro_summary"]["requires_api_key"] is False

discoveries = DiscoveryEngine().analyze(
    source_data={
        "recommendations": [],
        "benchmark_results": [],
        "provider_results": [],
        "research_experiments": [],
        "macro_report": report,
    },
    discovery_date="2026-06-30T18:00:00",
)
assert any(item["title"] == "Macro regime context" for item in discoveries)

graph = KnowledgeGraphEngine().build(
    source_data={
        "recommendations": [],
        "macro_report": report,
        "benchmark_results": [],
        "provider_results": [],
        "research_experiments": [],
    },
    discovery_data={
        "recent_discoveries": [],
        "top_discoveries": [],
        "discovery_history": [],
    },
    historical_runs=[],
)
macro_nodes = KnowledgeGraphEngine().query(graph, "macro")
macro_relationships = [
    relationship for relationship in graph["relationships"]
    if relationship["type"] == "uses_macro_indicator"
]
assert len([node for node in macro_nodes if node["type"] == "Macro Indicator"]) == 6
assert len([node for node in macro_nodes if node["type"] == "Macro Regime"]) == 1
assert len(macro_relationships) == 6

print("MacroEngine test passed.")
