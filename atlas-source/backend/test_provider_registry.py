from api.main import provider_health_dashboard, providers_dashboard
from backend.status import provider_registry_status
from engines.performance_observatory import PerformanceObservatory
from market.provider_health import HEALTH_STATUSES
from market.provider_registry import ProviderRegistry


registry = ProviderRegistry()
providers = registry.providers()
summary = registry.summary()
health = registry.health()

assert summary["provider_count"] == len(providers)
assert summary["policy"]["requires_api_keys_by_default"] is False
assert summary["policy"]["mock_providers_remain_default"] is True
assert summary["policy"]["providers_are_swappable"] is True
assert summary["policy"]["changes_recommendation_behavior"] is False
assert "Market Data" in summary["categories"]
assert "Historical Data" in summary["categories"]
assert "Research" in summary["categories"]

categories = {provider["category"] for provider in providers}
assert categories == set(ProviderRegistry.CATEGORIES)

for provider in providers:
    assert provider["name"]
    assert provider["category"] in ProviderRegistry.CATEGORIES
    assert provider["version"]
    assert provider["status"] in HEALTH_STATUSES
    assert isinstance(provider["capabilities"], list)
    assert isinstance(provider["requires_api_key"], bool)
    assert isinstance(provider["deterministic"], bool)
    assert isinstance(provider["supports_offline"], bool)
    assert isinstance(provider["priority"], int)
    assert provider["health"]["status"] in HEALTH_STATUSES
    assert "coverage" in provider["metadata"]
    assert "supported_tickers" in provider["metadata"]
    assert "earliest_date" in provider["metadata"]
    assert "latest_date" in provider["metadata"]
    assert "update_frequency" in provider["metadata"]
    assert "known_limitations" in provider["metadata"]

mock_providers = [
    provider for provider in providers
    if provider["status"] == "Mock"
]
assert mock_providers
assert all(provider["supports_offline"] for provider in mock_providers)
assert all(provider["deterministic"] for provider in mock_providers)
assert all(not provider["requires_api_key"] for provider in mock_providers)

assert health["summary"]["total_providers"] == len(providers)
assert health["summary"]["offline_capable_count"] >= len(mock_providers)
assert health["summary"]["requires_api_key_count"] >= 1
assert health["summary"]["status_counts"]["Mock"] >= 1
assert summary["offline_capability"]["mock_default"] is True
assert summary["offline_capability"]["offline_tests_supported"] is True
assert "mock-market-data" in summary["offline_capability"]["offline_capable_providers"]
assert "mock-historical-data" in summary["offline_capability"]["offline_capable_providers"]
assert "yahoo-market-data" in summary["experimental_providers"]
assert "sec-edgar-fundamentals" in summary["experimental_providers"]
assert "fred-macro" in summary["experimental_providers"]

status = provider_registry_status()
assert status["summary"]["provider_count"] == len(providers)
assert status["offline_capability"]["mock_default"] is True
assert "yahoo-market-data" in status["experimental_providers"]

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
provider_summary = observatory["provider_health_summary"]
assert provider_summary["total_providers"] == len(providers)
assert provider_summary["active_providers"]["Market Data"] == "mock"
assert provider_summary["policy"].startswith("Provider health is read-only")

providers_api = providers_dashboard()
assert providers_api["summary"]["provider_count"] == len(providers)
assert providers_api["providers"][0]["category"] in ProviderRegistry.CATEGORIES
assert providers_api["metadata"]

health_api = provider_health_dashboard()
assert health_api["summary"]["total_providers"] == len(providers)
assert health_api["providers"][0]["health"]["status"] in HEALTH_STATUSES

print("ProviderRegistry test passed.")
