from api.main import sec_dashboard, sec_summary_dashboard
from backend.status import sec_provider_status
from engines.edgar_provider import EdgarProvider
from engines.knowledge_graph_engine import KnowledgeGraphEngine
from engines.mock_sec_provider import MockSecProvider
from engines.performance_observatory import PerformanceObservatory
from engines.sec_engine import SecEngine
from engines.sec_provider import SecProvider
from market.provider_registry import ProviderRegistry


provider = MockSecProvider()
filings = provider.get_filings(
    tickers=["AAPL"],
    filing_types=["10-K", "10-Q", "8-K", "DEF 14A", "S-1"],
)

assert len(filings) == 5
assert [filing["form_type"] for filing in filings] == [
    "10-K",
    "10-Q",
    "8-K",
    "DEF 14A",
    "S-1",
]

for filing in filings:
    assert {
        "filing_date",
        "form_type",
        "company",
        "ticker",
        "sections_available",
        "filing_url",
        "summaries",
    } <= set(filing)
    assert filing["ticker"] == "AAPL"
    assert filing["form_type"] in SecProvider.FILING_TYPES
    assert filing["filing_url"].startswith("https://www.sec.gov/Archives/mock/")
    assert set(filing["summaries"]) == set(SecProvider.SUMMARY_SECTIONS)
    assert filing["summaries"]["Business"].startswith("Mock")

health = provider.health_check()
assert health["provider"] == "mock"
assert health["status"] == "Mock"
assert health["healthy"] is True
assert health["supports_offline"] is True
assert health["requires_api_key"] is False

try:
    provider.get_filings(tickers=["INVALID"])
    raise AssertionError("Invalid SEC ticker should fail.")
except ValueError as error:
    assert "Unsupported SEC ticker" in str(error)

try:
    provider.get_filings(tickers=["AAPL"], filing_types=["13F"])
    raise AssertionError("Invalid SEC filing type should fail.")
except ValueError as error:
    assert "Unsupported SEC filing type" in str(error)

engine = SecEngine()
analysis = engine.analyze(tickers=["AAPL"], filing_types=["10-K"])
assert analysis["provider"] == "mock"
assert analysis["summary"]["filing_count"] == 1
assert analysis["summary"]["form_type_counts"]["10-K"] == 1
assert analysis["research_context"]["research_domain"] == "SEC Filings"
assert analysis["observatory"]["provider"] == "mock"
assert analysis["observatory"]["offline_capable"] is True
assert analysis["policy"]["changes_recommendation_behavior"] is False
assert analysis["knowledge_graph_context"]["nodes"][0]["type"] == "SEC Filing"
assert analysis["knowledge_graph_context"]["relationships"][0]["type"] == "filed"

edgar = EdgarProvider()
edgar_filings = edgar.get_filings(tickers=["AAPL"], filing_types=["10-K"])
edgar_health = edgar.health_check()
assert len(edgar_filings) == 1
assert edgar.fallback_used is True
assert "not active in offline mode" in edgar.last_error
assert edgar_health["provider"] == "edgar"
assert edgar_health["status"] == "Experimental"
assert edgar_health["healthy"] is False
assert edgar_health["fallback_used"] is True
assert edgar_health["requires_api_key"] is False

registry = ProviderRegistry()
sec_providers = registry.by_category("SEC Filings")
assert [provider["name"] for provider in sec_providers] == [
    "mock-sec-filings",
    "sec-edgar-filings",
]
assert sec_providers[0]["status"] == "Mock"
assert sec_providers[0]["supports_offline"] is True
assert sec_providers[1]["status"] == "Experimental"
assert sec_providers[1]["requires_api_key"] is False
assert registry.active_providers()["SEC Filings"] == "mock"

status = sec_provider_status()
assert status["provider"] == "mock"
assert status["status"] == "Mock"
assert status["healthy"] is True
assert "10-K" in status["filing_types"]

api_result = sec_dashboard(ticker="AAPL", form_type="10-k")
assert api_result["summary"]["filing_count"] == 1
assert api_result["filings"][0]["form_type"] == "10-K"
assert api_result["policy"]["mock_default"] is True

api_summary = sec_summary_dashboard()
assert api_summary["summary"]["supported_filing_types"] == SecProvider.FILING_TYPES
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
assert observatory["sec_summary"]["provider"] == "mock"
assert observatory["sec_summary"]["filing_count"] > 0
assert observatory["sec_summary"]["requires_api_key"] is False

graph = KnowledgeGraphEngine().build(
    source_data={
        "recommendations": [],
        "sec_filings": filings,
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
sec_nodes = KnowledgeGraphEngine().query(graph, "sec_filings", "AAPL")
sec_relationships = [
    relationship for relationship in graph["relationships"]
    if relationship["type"] == "filed"
]
assert len(sec_nodes) == 5
assert sec_relationships

print("SecEngine test passed.")
