from api.main import portfolio_strategy_dashboard
from engines.discovery_engine import DiscoveryEngine
from engines.knowledge_graph_engine import KnowledgeGraphEngine
from engines.performance_observatory import PerformanceObservatory
from engines.portfolio_strategy_engine import PortfolioStrategyEngine
from engines.research_engine import ResearchEngine


portfolio = {
    "cash": 5000,
    "positions": [
        {
            "ticker": "VOO",
            "value": 50000,
            "sector": "Broad Market",
            "factor": "Core",
            "expected_return": 7,
            "volatility": 14,
        },
        {
            "ticker": "QQQ",
            "value": 30000,
            "sector": "Technology",
            "factor": "Growth",
            "expected_return": 9,
            "volatility": 20,
        },
        {
            "ticker": "AAPL",
            "value": 15000,
            "sector": "Technology",
            "factor": "Quality",
            "expected_return": 8,
            "volatility": 22,
        },
    ],
}
replay_rows = [
    {"period": "Q1", "current_return": 2, "atlas_return": 3},
    {"period": "Q2", "current_return": -3, "atlas_return": -1},
    {"period": "Q3", "current_return": 4, "atlas_return": 5},
]

engine = PortfolioStrategyEngine()
review = engine.review(portfolio=portfolio, replay_rows=replay_rows)
analysis = review["analysis"]
actions = {
    item["ticker"]: item["action"]
    for item in review["strategy_recommendations"]
}

assert analysis["total_value"] == 100000
assert analysis["cash_percentage"] == 5
assert analysis["sector_exposure"]["Technology"] == 45
assert analysis["factor_exposure"]["Core"] == 50
assert analysis["concentration"]["largest_position"] == 50
assert analysis["risk"] == "High"
assert analysis["expected_return"] == 7.4
assert analysis["expected_volatility"] > 0
assert analysis["sharpe_estimate"] > 0
assert analysis["position_overlap"] == [
    {"tickers": ["QQQ", "AAPL"], "shared": ["sector"]}
]

assert actions["VOO"] == "Reduce"
assert actions["AAPL"] == "Increase"
assert all(
    item["requires_human_approval"]
    for item in review["strategy_recommendations"]
)

simulation = review["simulation"]
assert "current_portfolio" in simulation
assert "atlas_portfolio" in simulation
assert "difference" in simulation
assert simulation["difference"]["cash_delta"] > 0

historical_replay = review["historical_replay"]
assert historical_replay["periods"] == 3
assert historical_replay["atlas_outperformed"] is True
assert historical_replay["difference"] > 0

case_study = review["case_study"]
assert case_study["case_type"] == "Portfolio Strategy"
assert case_study["outcome"] == "Atlas Outperformed"
assert case_study["automatic_execution"] is False
assert case_study["requires_human_approval"] is True

assert review["controlled_decision"] == {
    "read_only": True,
    "executes_trades": False,
    "connects_brokers": False,
    "requires_human_approval": True,
}

research = ResearchEngine().portfolio_strategy_research([review])
assert research["sample_size"] == 1
assert research["atlas_outperformance_rate"] == 100
assert research["average_return_improvement"] == historical_replay["difference"]

source_data = {
    "recommendations": [],
    "benchmark_results": [],
    "provider_results": [],
    "research_experiments": [],
    "portfolio_strategies": [review],
}

observatory = PerformanceObservatory().generate(
    source_data=source_data,
    discovery_data={
        "recent_discoveries": [],
        "top_discoveries": [],
        "discovery_history": [],
    },
)
assert observatory["portfolio_strategy_summary"]["review_count"] == 1
assert (
    observatory["portfolio_strategy_summary"]["atlas_outperformance_rate"]
    == 100
)

discoveries = DiscoveryEngine().analyze(
    source_data=source_data,
    discovery_date="2026-06-30T13:00:00",
)
assert any(
    item["description"]
    == "Atlas portfolio strategies outperformed baseline in 100.0% of reviews."
    for item in discoveries
)

graph = KnowledgeGraphEngine().build(
    source_data=source_data,
    discovery_data={
        "recent_discoveries": [],
        "top_discoveries": [],
        "discovery_history": [],
    },
    historical_runs=[],
)
node_types = {node["type"] for node in graph["nodes"]}
relationship_types = {item["type"] for item in graph["relationships"]}

assert {"Portfolio", "Portfolio Strategy", "Portfolio Optimization"} <= node_types
assert {"has_strategy", "optimizes"} <= relationship_types

api_review = portfolio_strategy_dashboard()
assert api_review["controlled_decision"]["executes_trades"] is False
assert api_review["simulation"]["difference"]

print("PortfolioStrategyEngine test passed.")
