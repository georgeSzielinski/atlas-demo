import importlib.util
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.learning_intelligence_schemas import (
    LearningCenterResponse,
    LearningCenterStatusResponse,
    RecommendationIntelligenceRecordsResponse,
    RecommendationOutcomesResponse,
)
from api.scheduler_runtime import scheduler_runtime

from core.settings import APPROVED_TICKERS, FORECAST_PROVIDER
from database.repository import (
    get_case_studies,
    get_committee_cycle_evaluations,
    get_daily_cycle_runs,
    get_daily_journals,
    get_discovery_source_data,
    get_historical_validation_runs,
    get_intelligence_dashboard_summary,
    get_latest_daily_cycle_run,
    get_latest_daily_journal,
    get_latest_recommendation_for_ticker,
    get_latest_runtime_state,
    get_model_evaluations,
    get_paper_performance_reports,
    get_paper_portfolio_history,
    get_paper_trades,
    get_recent_risk_decisions,
    get_latest_market_data_snapshot,
    get_latest_monthly_report,
    get_portfolio_construction_reports,
    get_probability_reports,
    get_registry_experiments,
    get_scientific_validation_reports,
    get_simulation_arena_runs,
    get_runtime_states,
    reset_paper_fund_data,
    reset_paper_simulation_data,
)
from database.migrator import run_migrations
from engines.catalyst_engine import CatalystEngine
from engines.discovery_engine import DiscoveryEngine
from engines.fundamental_engine import FundamentalEngine
from engines.intelligence_fusion_engine import IntelligenceFusionEngine
from engines.kronos_forecast_provider import KronosForecastProvider
from engines.history_engine import HistoryEngine
from engines.institutional_report_engine import InstitutionalReportEngine
from engines.knowledge_graph_engine import KnowledgeGraphEngine
from engines.macro_engine import MacroEngine
from engines.news_engine import NewsEngine
from engines.operations_engine import OperationsEngine
from engines.reliability_engine import ReliabilityEngine
from engines.dashboard_v2_engine import DashboardV2Engine
from engines.daily_cycle_engine import DailyCycleEngine
from engines.live_paper_fund_engine import LivePaperFundEngine
from engines.paper_trading_engine import PaperTradingEngine
from engines.performance_analytics_engine import PerformanceAnalyticsEngine
from engines.correlation_engine import CorrelationEngine
from engines.performance_attribution_engine import PerformanceAttributionEngine
from engines.performance_lab_engine import PerformanceLabEngine
from engines.self_improvement_engine import SelfImprovementEngine
from engines.performance_observatory import PerformanceObservatory
from engines.portfolio_construction_engine import PortfolioConstructionEngine
from engines.portfolio_intelligence_engine import PortfolioIntelligenceEngine
from engines.portfolio_strategy_engine import PortfolioStrategyEngine
from engines.probability_engine import ProbabilityEngine
from engines.research_lab_engine import ResearchLabEngine
from engines.research_memory_engine import ResearchMemoryEngine
from engines.research_engine import ResearchEngine
from engines.risk_management_engine import RiskManagementEngine
from engines.runtime_engine import RuntimeEngine
from engines.scenario_analysis_engine import ScenarioAnalysisEngine
from engines.sec_engine import SecEngine
from engines.self_learning_analytics_engine import SelfLearningAnalyticsEngine
from engines.committee_engine import CommitteeEngine
from engines.strategy_comparison_engine import StrategyComparisonEngine
from engines.watchlist_research_engine import WatchlistResearchEngine
from engines.research_cycle_engine import ResearchCycleEngine
from engines.outcome_evaluation_engine import OutcomeEvaluationEngine
from engines.recommendation_intelligence_engine import RecommendationIntelligenceEngine
from engines.committee_intelligence_engine import CommitteeIntelligenceEngine
from engines.engine_intelligence_engine import EngineIntelligenceEngine
from engines.learning_center_engine import LearningCenterEngine
from engines.strategy_registry_engine import StrategyRegistryEngine
from market.data import data_provider_health, historical_data_provider_health
from market.market_data_manager import MarketDataManager
from market.provider_registry import ProviderRegistry
from services.investment_platform import InvestmentPlatform


@asynccontextmanager
async def lifespan(app):
    # Single deterministic ownership point for the backend scheduler. It starts
    # nothing unless ATLAS_SCHEDULER_ENABLED is set, and always cancels/awaits on
    # shutdown. Tests call handlers directly and never trigger this lifespan.
    run_migrations()
    await scheduler_runtime.start()
    try:
        yield
    finally:
        await scheduler_runtime.stop()


app = FastAPI(title="Atlas API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
REPORTS_PATH = Path("reports")


@app.get("/")
def root():
    return {
        "name": "Atlas",
        "type": "AI Investment Research Platform",
        "status": "running",
    }


@app.get("/status")
def status():
    return {
        "status": "ok",
        "message": "Atlas API is running",
    }


@app.get("/operations")
def operations_center():
    """Read-only Atlas Operations Center v1 aggregate status.

    Pure reads only: it never runs a scheduler tick or paper-fund cycle, sets up
    the database, or writes anything. It delegates directly to the deterministic
    OperationsEngine, which composes overall health, scheduler, market data,
    paper fund, learning, database, uptime, recent errors, operational
    recommendations, warnings, and operational mode from existing read-only
    surfaces and degrades gracefully when a subsystem is unavailable.
    """
    report = OperationsEngine().report()
    report["outcome_evaluation"] = OutcomeEvaluationEngine().status()
    report["recommendation_intelligence"] = RecommendationIntelligenceEngine().status()
    return report


@app.get("/reliability")
def reliability_center():
    """Read-only Atlas Reliability Framework v1 aggregate report.

    Pure reads only: it never runs a scheduler tick or paper-fund cycle, sets up
    the database, or writes anything. It delegates directly to the deterministic
    ReliabilityEngine, which composes the OperationsEngine report plus read-only
    runtime and market-data history into a weighted reliability score, subsystem
    breakdown, incidents, availability, trend, and recommendations, and degrades
    to NOT_EVALUATED with reasons when evidence is unavailable.
    """
    return ReliabilityEngine().report()


@app.get("/history")
def history():
    history_engine = HistoryEngine()

    return history_engine.recent_runs(limit=5)


@app.get("/history/{run_id}")
def history_detail(run_id: int):
    history_engine = HistoryEngine()
    runs = history_engine.recent_runs(limit=100)
    run = next((item for item in runs if item["id"] == run_id), None)

    if run is None:
        raise HTTPException(status_code=404, detail="Atlas run not found")

    return {
        "run": run,
        "recommendations": history_engine.recommendations_for_run(run_id),
        "portfolio_snapshot": history_engine.portfolio_snapshot(run_id),
    }


@app.get("/recommendations/history")
def recommendations_history(limit: int = 500):
    """Read-only feed of every committee recommendation cycle ever recorded.

    Powers the Recommendation Explorer. Returns the persisted
    committee_cycle_evaluations rows (deterministic read; no scheduler tick,
    no writes, no order placement). Each cycle carries its evaluated_at
    timestamp and the per-ticker evaluations the investment committee produced.
    Filtering, sorting and statistics are derived client-side.
    """
    safe_limit = max(1, min(int(limit), 2000))
    return {"cycles": get_committee_cycle_evaluations(limit=safe_limit)}


@app.post("/run")
def run_atlas():
    platform = InvestmentPlatform()
    dashboard = platform.run(APPROVED_TICKERS)

    return {
        "status": "completed",
        "market_status": dashboard.market_status,
        "average_rsi": dashboard.average_rsi,
        "average_volatility": dashboard.average_volatility,
        "recommendations_count": len(dashboard.recommendations),
    }


@app.get("/dashboard")
def dashboard():
    history_engine = HistoryEngine()
    runs = history_engine.recent_runs(limit=1)
    latest_run = runs[0] if runs else None

    if latest_run is None:
        latest_recommendations = []
        latest_portfolio_snapshot = None
    else:
        run_id = latest_run["id"]
        latest_recommendations = history_engine.recommendations_for_run(run_id)
        latest_portfolio_snapshot = history_engine.portfolio_snapshot(run_id)

    reports_count = 0
    if REPORTS_PATH.exists():
        reports_count = len(list(REPORTS_PATH.glob("*.md")))

    intelligence = get_intelligence_dashboard_summary()
    observatory = PerformanceObservatory().generate()

    return {
        "latest_run": latest_run,
        "latest_portfolio_snapshot": latest_portfolio_snapshot,
        "latest_recommendations": latest_recommendations,
        "reports_count": reports_count,
        "system_health": _system_health(),
        "recommendation_metrics": intelligence["recommendation_metrics"],
        "evidence_metrics": intelligence["evidence_metrics"],
        "forecast_information": _forecast_information(),
        "data_provider_health": _data_provider_health(),
        "news_provider_health": _news_provider_health(),
        "fundamental_provider_health": _fundamental_provider_health(),
        "pipeline_status": _pipeline_status(),
        "fusion_status": _fusion_status(),
        "latest_recommendation": intelligence["latest_recommendation"],
        "observatory": {
            "platform_metrics": observatory["platform_metrics"],
            "engine_report_cards": observatory["engine_report_cards"],
            "provider_report_cards": observatory["provider_report_cards"],
            "provider_health_summary": observatory["provider_health_summary"],
        },
    }


@app.get("/dashboard/v2")
def dashboard_v2():
    """Read-only unified dashboard: one composed payload of existing engines.

    Pure reads only: it never writes, runs a scheduler tick or paper-fund cycle,
    or sets up the database. It delegates directly to the deterministic
    DashboardV2Engine, which composes the operations, reliability, paper-fund,
    portfolio, performance, scenario, correlation, learning, risk, market, and
    scheduler read-only surfaces into a single response, loading the shared
    paper-fund dataset exactly once. The existing /dashboard endpoint is
    unchanged.
    """
    return DashboardV2Engine().report()


@app.get("/research")
def research_dashboard():

    return ResearchEngine().research_dashboard_data()


@app.get("/discoveries")
def discovery_dashboard():

    return DiscoveryEngine().discovery_dashboard_data()


@app.get("/observatory")
def observatory_dashboard():

    return PerformanceObservatory().generate()


@app.get("/historical-validation")
def historical_validation_dashboard():

    return {
        "historical_validation_runs": get_historical_validation_runs(limit=10),
    }


@app.get("/model-evaluations")
def model_evaluations_dashboard():

    return {
        "model_evaluations": get_model_evaluations(limit=50),
        "model_evaluation_report": ResearchEngine().model_evaluation_report(
            get_model_evaluations(limit=50)
        ),
    }


@app.get("/case-studies")
def case_studies_dashboard():
    cases = get_case_studies(limit=50)

    return {
        "case_studies": cases,
        "case_study_filters": ResearchEngine().case_study_filters(cases),
    }


@app.get("/portfolio-strategy")
def portfolio_strategy_dashboard():
    return PortfolioStrategyEngine().review()


@app.get("/portfolio-construction")
def portfolio_construction_dashboard():
    report = _portfolio_construction_report()

    return {
        "portfolio_construction": report,
        "stored_reports": get_portfolio_construction_reports(limit=10),
        "policy": report["policy"],
    }


@app.get("/allocation")
def allocation_dashboard():
    report = _portfolio_construction_report()

    return {
        "recommended_allocations": report["recommended_allocations"],
        "capital_allocation_ranking": report["capital_allocation_ranking"],
        "policy": report["policy"],
    }


@app.get("/rebalance")
def rebalance_dashboard():
    report = _portfolio_construction_report()

    return {
        "portfolio_actions": report["portfolio_actions"],
        "policy": report["policy"],
    }


@app.get("/risk-budget")
def risk_budget_dashboard():
    report = _portfolio_construction_report()

    return {
        "risk_budget": report["risk_budget"],
        "risk_summary": report["risk_summary"],
        "policy": report["policy"],
    }


@app.get("/portfolio/intelligence")
def portfolio_intelligence(limit: int = 200):
    return PortfolioIntelligenceEngine().generate(limit=limit)


@app.get("/scenario-analysis")
def scenario_analysis(limit: int = 200):
    return ScenarioAnalysisEngine().generate(limit=limit)


@app.get("/performance-attribution")
def performance_attribution(limit: int = 200):
    return PerformanceAttributionEngine().generate(limit=limit)


@app.get("/performance-lab")
def performance_lab(limit: int = 200):
    """Read-only Performance Lab: deterministic paper-fund attribution."""
    return PerformanceLabEngine().generate(limit=limit)


@app.get("/self-improvement")
def self_improvement(limit: int = 200):
    """Read-only Self-Improvement Engine: deterministic research opportunities.

    Analyzes persisted historical evidence and proposes evidence-backed
    research opportunities. It never changes strategies, weights, the
    committee, risk limits, or trading behavior, calls no LLM, and uses no
    randomness. Domains with insufficient evidence are NOT_EVALUATED.
    """
    return SelfImprovementEngine().generate(limit=limit)


@app.get("/market-regime")
def market_regime():
    """Read-only, deterministic classification of the current market regime.

    Does not change trading, recommendation, or paper-fund behavior.
    """
    from engines.market_regime_classifier import MarketRegimeClassifier

    return MarketRegimeClassifier().generate()


@app.get("/portfolio/correlation")
def portfolio_correlation(limit: int = 200):
    return CorrelationEngine().generate(limit=limit)


@app.get("/catalysts")
def catalysts_dashboard():
    return CatalystEngine().analyze(
        tickers=APPROVED_TICKERS[:4],
        as_of_date="2026-06-30",
    )


@app.get("/catalyst-summary")
def catalyst_summary_dashboard():
    analysis = CatalystEngine().analyze(
        tickers=APPROVED_TICKERS[:4],
        as_of_date="2026-06-30",
    )

    return analysis["summary"]


@app.get("/probabilities")
def probabilities_dashboard():

    return {
        "probability_reports": get_probability_reports(limit=50),
        "policy": {
            "read_only": True,
            "changes_recommendation_behavior": False,
            "automatic_execution": False,
        },
    }


@app.get("/scientific-validation")
def scientific_validation_dashboard():

    return {
        "scientific_validations": get_scientific_validation_reports(limit=50),
        "policy": {
            "read_only": True,
            "deterministic": True,
            "changes_recommendation_behavior": False,
            "automatic_adoption": False,
            "broker_integration": False,
        },
    }


@app.get("/simulation-arena")
def simulation_arena_dashboard():

    return {
        "simulation_arena_runs": get_simulation_arena_runs(limit=50),
        "policy": {
            "read_only": True,
            "deterministic": True,
            "research_only": True,
            "changes_recommendation_behavior": False,
            "automatic_execution": False,
            "broker_integration": False,
        },
    }


@app.get("/analytics")
def analytics_dashboard():

    return PerformanceAnalyticsEngine().generate()


@app.get("/analytics/equity")
def analytics_equity_dashboard():
    analytics = PerformanceAnalyticsEngine().generate()

    return {
        "equity_curve": analytics["equity_curve"],
        "demo_data": analytics["demo_data"],
        "policy": analytics["policy"],
    }


@app.get("/analytics/benchmarks")
def analytics_benchmarks_dashboard():
    analytics = PerformanceAnalyticsEngine().generate()

    return {
        "benchmark_comparison": analytics["benchmark_comparison"],
        "policy": analytics["policy"],
    }


@app.get("/analytics/calibration")
def analytics_calibration_dashboard():
    analytics = PerformanceAnalyticsEngine().generate()
    recommendation = analytics["recommendation_analytics"]

    return {
        "recommendation_analytics": recommendation,
        "calibration": {
            "confidence_calibration": recommendation["confidence_calibration"],
            "probability_calibration": recommendation["probability_calibration"],
        },
        "risk_statistics": analytics["risk_statistics"],
        "policy": analytics["policy"],
    }


@app.get("/analytics/research")
def analytics_research_dashboard():
    analytics = PerformanceAnalyticsEngine().generate()

    return {
        "research_progress": analytics["research_progress"],
        "learning_curve": analytics["learning_curve"],
        "policy": analytics["policy"],
    }


@app.get("/learning/analytics")
def learning_analytics(limit: int = 200):
    return SelfLearningAnalyticsEngine().generate(limit=limit)


@app.get("/monthly-report/latest")
def latest_monthly_report_dashboard():
    report = get_latest_monthly_report()

    if report is None:
        report = PerformanceAnalyticsEngine().latest_monthly_report()

    return {
        "monthly_report": report,
        "policy": {
            "read_only": True,
            "deterministic": True,
            "changes_recommendation_behavior": False,
            "broker_integration": False,
        },
    }


@app.get("/brain/{ticker}")
def brain_dashboard(ticker: str):

    return ResearchEngine().brain_report(ticker)


@app.get("/brain/summary/{ticker}")
def brain_summary_dashboard(ticker: str):

    return ResearchEngine().brain_summary(ticker)


@app.get("/brain/evidence/{ticker}")
def brain_evidence_dashboard(ticker: str):

    return ResearchEngine().brain_evidence(ticker)


@app.get("/brain/timeline/{ticker}")
def brain_timeline_dashboard(ticker: str):

    return ResearchEngine().brain_timeline(ticker)


@app.get("/research-lab")
def research_lab_dashboard():

    return ResearchLabEngine().laboratory_dashboard()


@app.get("/strategies")
def strategies_dashboard():
    """Read-only registry of research-only strategy specs. No activation."""
    return StrategyRegistryEngine().report()


# NOTE: registered before /strategies/{strategy_id} so "compare" is never
# captured as a strategy id.
@app.get("/strategies/compare")
def strategies_compare():
    """On-demand, read-only strategy comparison. Nothing is persisted."""
    return StrategyComparisonEngine().compare()


@app.get("/strategies/{strategy_id}")
def strategy_detail(strategy_id: str):
    strategy = StrategyRegistryEngine().get_strategy(strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@app.get("/committee/members")
def committee_members():
    """Read-only roster of the research-only investment committee.

    Members are the built-in Strategy Registry specs convened by
    CommitteeEngine; there is no activation, execution, or persistence.
    """
    engine = CommitteeEngine()
    return {
        "version": engine.VERSION,
        "members": [
            {
                "member_id": member.strategy_id,
                "name": member.name,
                "description": member.spec["description"],
                "expected_holding_period": member.spec["expected_holding_period"],
                "signal_inputs": member.spec["signal_inputs"],
                "scoring_weights": member.spec["scoring_logic"]["weights"],
                "action_bands": member.spec["scoring_logic"]["action_bands"],
                "definition_hash": member.spec["definition_hash"],
                "is_baseline": member.spec.get("is_baseline", False),
                "policy": member.policy(),
            }
            for member in engine.members
        ],
        "count": len(engine.members),
        "quorum": engine.quorum,
        "policy": engine.policy(),
    }


@app.post("/recommendations/generate")
def generate_recommendations(payload: dict | None = Body(default=None)):
    """Explicit, deterministic watchlist research run (manual only).

    Persists ordinary recommendation records for the paper-fund watchlist
    (fallback: APPROVED_TICKERS; explicit "tickers" list overrides both) so
    the committee and Strategy Lab operate on real stored inputs. Refuses
    mock/test/unknown providers and writes nothing when refused. Never touches
    the live paper fund, construction, risk, or any execution path.
    """
    tickers = (payload or {}).get("tickers")
    return WatchlistResearchEngine().generate(tickers=tickers)


@app.get("/committee/evaluate/{ticker}")
def committee_evaluate(ticker: str):
    """Read-only committee evaluation of one ticker.

    Reads the NEWEST stored recommendation record for the ticker and convenes
    the deterministic strategy committee on it. If no record exists the
    committee returns NOT_EVALUATED with a clear reason — stock inputs are
    never fabricated. No writes, no cycles, no scheduler, no broker.
    """
    engine = CommitteeEngine()
    record = get_latest_recommendation_for_ticker(ticker)
    if record is None:
        return engine.unavailable(
            ticker,
            (
                f"No stored recommendation exists for "
                f"{str(ticker).strip().upper()}; run an Atlas analysis first. "
                "Committee inputs are never fabricated."
            ),
        )

    result = engine.evaluate(record)
    result["source"] = {
        "recommendation_id": record.get("id"),
        "run_id": record.get("run_id"),
        "stored_action": record.get("action"),
        "read_only": True,
    }
    return result


@app.get("/experiments")
def experiments_dashboard():
    engine = ResearchLabEngine()
    experiments = get_registry_experiments(limit=200) or engine.default_experiments()

    return {
        "experiments": experiments,
        "experiment_count": len(experiments),
        "experiment_states": engine.EXPERIMENT_STATES,
        "queue": engine.build_queue(experiments),
        "policy": engine.policy(),
    }


@app.get("/experiments/history")
def experiments_history_dashboard(
    feature: str | None = None,
    regime: str | None = None,
    date: str | None = None,
    result: str | None = None,
    status: str | None = None,
):
    engine = ResearchLabEngine()
    experiments = get_registry_experiments(limit=200) or engine.default_experiments()

    return {
        "history": engine.build_history(experiments),
        "results": engine.search_history(
            experiments,
            feature=feature,
            regime=regime,
            date=date,
            result=result,
            status=status,
        ),
        "policy": engine.policy(),
    }


@app.get("/experiments/active")
def experiments_active_dashboard():
    engine = ResearchLabEngine()

    return {
        "active_experiments": engine.active_experiments(),
        "policy": engine.policy(),
    }


@app.get("/validation/latest")
def validation_latest_dashboard():
    reports = get_scientific_validation_reports(limit=1)

    return {
        "latest_validation": reports[0] if reports else None,
        "policy": {
            "read_only": True,
            "deterministic": True,
            "changes_recommendation_behavior": False,
            "automatic_adoption": False,
            "broker_integration": False,
        },
    }


PAPER_EMPTY_STATE = (
    "No paper replay has run yet. Configure Historical Price Replay."
)
REMOVED_PAPER_MODES = {
    "demo_simulation",
    "demo_preview",
    "fake_paper",
    "deterministic_demo_portfolio",
}


@app.get("/paper-portfolio")
def paper_portfolio_dashboard():
    history = get_paper_portfolio_history(limit=50)

    return {
        "latest_portfolio": history[0] if history else None,
        "portfolio_history": history,
        "empty_state": None if history else PAPER_EMPTY_STATE,
        "policy": _paper_trading_policy(),
    }


@app.get("/paper-trades")
def paper_trades_dashboard():
    trades = get_paper_trades(limit=100)

    return {
        "paper_trades": trades,
        "empty_state": None if trades else PAPER_EMPTY_STATE,
        "policy": _paper_trading_policy(),
    }


@app.get("/paper-performance")
def paper_performance_dashboard():
    reports = get_paper_performance_reports(limit=50)

    return {
        "paper_performance_reports": reports,
        "empty_state": None if reports else PAPER_EMPTY_STATE,
        "policy": _paper_trading_policy(),
    }


@app.post("/paper-sim/run")
def run_paper_simulation(
    mode: str = "market_close",
    paper_mode: str | None = None,
):
    result = _run_paper_simulation(mode, paper_mode=paper_mode)

    return {
        "simulation": result,
        "paper_portfolio": paper_portfolio_dashboard(),
        "paper_trades": paper_trades_dashboard(),
        "paper_performance": paper_performance_dashboard(),
        "daily_cycle": daily_cycle_dashboard(),
        "daily_journal": daily_journal_dashboard(),
        "policy": _paper_trading_policy() | {
            "status": "SIMULATED",
            "automatic_execution": False,
            "human_approval_required_for_real_trading": True,
        },
    }


@app.post("/paper-replay/run")
def run_paper_replay(payload: dict | None = Body(default=None)):
    result = _run_paper_replay(payload or {})
    price_backed = bool(result.get("price_backed"))

    response = {
        "replay": result,
        "audit": result.get("audit"),
        "price_backed": price_backed,
        "replay_status": result["replay_status"],
        "error": result.get("error"),
        "policy": _paper_trading_policy() | {
            "status": result["replay_status"],
            "price_backed": price_backed,
            "automatic_execution": False,
            "human_approval_required_for_real_trading": True,
        },
    }

    # Only surface portfolio/trades/performance for a real price-backed replay.
    # A FAILED replay never shows a chart, trades, or P/L.
    if price_backed:
        response["paper_portfolio"] = paper_portfolio_dashboard()
        response["paper_trades"] = paper_trades_dashboard()
        response["paper_performance"] = paper_performance_dashboard()
    else:
        response["paper_portfolio"] = {"latest_portfolio": None, "portfolio_history": []}
        response["paper_trades"] = {"paper_trades": []}
        response["paper_performance"] = {"paper_performance_reports": []}

    return response


@app.post("/paper-sim/reset")
def reset_paper_simulation():
    result = reset_paper_simulation_data()

    return {
        "reset": result,
        "paper_portfolio": paper_portfolio_dashboard(),
        "paper_trades": paper_trades_dashboard(),
        "paper_performance": paper_performance_dashboard(),
        "daily_cycle": daily_cycle_dashboard(),
        "daily_journal": daily_journal_dashboard(),
        "policy": result["policy"],
    }


@app.get("/paper-trading/status")
def paper_trading_status_dashboard():
    history = get_paper_portfolio_history(limit=200)
    trades = get_paper_trades(limit=200)
    reports = get_paper_performance_reports(limit=50)
    audits = [
        (report.get("performance") or {}).get("replay_audit")
        for report in reports
        if (report.get("performance") or {}).get("replay_audit")
    ]
    latest_audit = audits[0] if audits else None
    latest_policy = (reports[0].get("policy") or {}) if reports else {}
    price_backed = bool(latest_audit and latest_audit.get("price_backed"))
    last_replay_time = latest_policy.get("simulated_at")

    return {
        "paper_trading_status": "Replay completed" if latest_audit else "Not started",
        "current_mode": "historical_price_replay" if latest_audit else "not_started",
        "supported_modes": [
            "historical_price_replay",
            "live_paper_fund",
            "broker_paper_pending",
        ],
        "last_replay_time": last_replay_time,
        "last_successful_replay": last_replay_time if price_backed else None,
        "replays_completed": len(audits),
        "trades_generated": len(trades),
        "portfolio_points_generated": len(history),
        "price_backed": price_backed,
        "latest_replay_audit": latest_audit,
        "learning": _paper_learning_status(latest_audit, reports),
        "policy": _paper_trading_policy(),
    }


@app.get("/paper-replay/health")
def paper_replay_health(probe: bool = False):
    yfinance_installed = importlib.util.find_spec("yfinance") is not None
    provider_available = yfinance_installed
    last_error = ""
    probe_result = None

    if probe:
        probe_result = historical_data_provider_health()
        provider_available = bool(
            probe_result["healthy"] and not probe_result["fallback_used"]
        )
        last_error = probe_result["failure_message"]

    how_to_fix = []
    if not yfinance_installed:
        how_to_fix.append("Install yfinance with pip install yfinance")
    if yfinance_installed and not provider_available:
        how_to_fix.append("Select a date range with available market data")

    return {
        "yfinance_installed": yfinance_installed,
        "historical_provider": "yahoo",
        "historical_provider_available": provider_available,
        "last_error": last_error,
        "how_to_fix": how_to_fix,
        "probe_result": probe_result,
        "policy": _paper_trading_policy(),
    }


@app.get("/paper-broker/status")
def paper_broker_status():
    missing_config = [
        name
        for name in ("ALPACA_API_KEY", "ALPACA_API_SECRET")
        if not os.environ.get(name)
    ]

    return {
        "broker_paper_supported": "pending",
        "mode": "broker_paper_pending",
        "provider": "alpaca_paper",
        "configured": not missing_config,
        "missing_config": missing_config,
        "execution_enabled": False,
        "real_money": False,
        "order_endpoints": [],
        "message": (
            "Broker paper trading is future architecture only and is not "
            "active yet. Alpaca Paper is a configuration placeholder: no "
            "orders can be placed, no account connection is required, and "
            "no real money is involved."
        ),
        "policy": _paper_trading_policy(),
    }


@app.get("/paper-fund/status")
def paper_fund_status():

    return LivePaperFundEngine().status()


@app.get("/risk/limits")
def risk_limits():
    return {
        "limits": dict(RiskManagementEngine.DEFAULT_LIMITS),
        "deterministic": True,
        "read_only": True,
        **RiskManagementEngine.SAFETY_FIELDS,
    }


@app.get("/risk/decisions")
def risk_decisions(limit: int = 100):
    decisions = get_recent_risk_decisions(limit=limit)

    return {
        "decisions": decisions,
        "count": len(decisions),
        "read_only": True,
        **RiskManagementEngine.SAFETY_FIELDS,
    }


@app.post("/paper-fund/start")
def paper_fund_start(payload: dict | None = Body(default=None)):
    payload = payload or {}

    try:
        state = LivePaperFundEngine().start(
            watchlist=payload.get("watchlist", APPROVED_TICKERS[:4]),
            starting_cash=payload.get("starting_cash"),
            interval_minutes=payload.get("interval_minutes"),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    return {"state": state, "status": paper_fund_status()}


@app.post("/paper-fund/pause")
def paper_fund_pause():

    try:
        state = LivePaperFundEngine().pause()
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    return {"state": state, "status": paper_fund_status()}


@app.post("/paper-fund/resume")
def paper_fund_resume():

    try:
        state = LivePaperFundEngine().resume()
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    return {"state": state, "status": paper_fund_status()}


@app.post("/paper-fund/stop")
def paper_fund_stop():

    try:
        state = LivePaperFundEngine().stop()
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    return {"state": state, "status": paper_fund_status()}


@app.post("/paper-fund/reset")
def paper_fund_reset():
    result = reset_paper_fund_data()

    return {"reset": result, "status": paper_fund_status()}


@app.post("/paper-fund/cycle")
def paper_fund_cycle():
    """Manual cycle override, sharing the autonomous single-flight lock.

    If any cycle (manual or scheduled) is already running, this returns 409
    immediately instead of overlapping it — it never blocks and never runs
    two cycles concurrently. Cycle logic itself is unchanged.
    """
    engine = LivePaperFundEngine()
    try:
        cycle = engine.run_manual_cycle(manager=MarketDataManager())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    if (cycle or {}).get("reason") == LivePaperFundEngine.CYCLE_IN_PROGRESS_REASON:
        raise HTTPException(
            status_code=409,
            detail=LivePaperFundEngine.CYCLE_IN_PROGRESS_REASON,
        )

    recovery = None
    if (cycle or {}).get("cycle_status") == "FAILED":
        # A failed manual cycle must not latch ERROR and kill autonomous
        # operation; run the same recovery pass the scheduler path uses.
        recovery = engine.recover_after_failure()

    return {"cycle": cycle, "recovery": recovery, "status": paper_fund_status()}


@app.post("/paper-fund/tick")
def paper_fund_tick():
    """Automatic scheduler entrypoint: run a cycle only if safe and due.

    Idempotent and safe to call frequently (e.g. from cron). It captures one
    `now`, builds the standard MarketDataManager, and delegates to
    run_due_cycle, which owns the single-flight guard and all skip logic.
    Returns a skip when automation is disabled and cycle_in_progress when the
    guard is already held. /paper-fund/cycle remains the manual override.
    """
    now = datetime.now()
    manager = MarketDataManager()
    result = LivePaperFundEngine().run_due_cycle(manager=manager, now=now)

    if result.get("reason") == LivePaperFundEngine.CYCLE_IN_PROGRESS_REASON:
        return {"status": "cycle_in_progress", "tick": result}

    return {"tick": result, "status": paper_fund_status()}


@app.post("/research-cycle/tick")
def research_cycle_tick():
    """Autonomous research cycle tick: research -> committee -> fund.

    Idempotent and safe to call frequently. Stage 1 (recommendation
    generation) and stage 2 (committee evaluation) run only when
    AUTO_RESEARCH_ENABLED is on and recommendations are stale; stage 3 is the
    unchanged guarded paper-fund tick. With research disabled this reduces
    exactly to the prior scheduler behavior. Composition only — no engine
    logic is duplicated, no broker, no real money, no LLM.
    """
    now = datetime.now()
    manager = MarketDataManager()
    result = ResearchCycleEngine().run_due_cycle(manager=manager, now=now)
    return {"tick": result, "status": result.get("status")}


def scheduled_cycle_tick():
    """One scheduler tick: existing research/fund composition plus outcomes.

    Outcome failure is isolated from research and the paper fund. The existing
    scheduler owns serialization, watchdog handling, and durable stage evidence.
    """
    response = research_cycle_tick()
    try:
        outcome = OutcomeEvaluationEngine().run_due_cycle(
            manager=MarketDataManager(), now=datetime.now()
        )
    except Exception as error:
        outcome = {
            "status": "ERROR",
            "reason": f"{type(error).__name__}: {error}",
            "duration_seconds": 0.0,
            "errors": [f"{type(error).__name__}: {error}"],
            "policy": OutcomeEvaluationEngine().policy(),
        }

    stages = (response.get("tick") or {}).get("stages")
    if isinstance(stages, list):
        stages.append({
            "stage": "outcome_evaluation",
            "status": outcome.get("status"),
            "reason": outcome.get("reason"),
            "duration_seconds": outcome.get("duration_seconds"),
            "details": {
                key: outcome.get(key)
                for key in (
                    "evaluated", "succeeded", "failed", "deferred",
                    "skipped_completed", "errors", "provider",
                )
            },
        })
    response["outcome_evaluation"] = outcome
    return response


@app.post("/outcomes/evaluate")
def outcomes_evaluate():
    """Manually evaluate due paper outcomes; never places or changes orders."""
    result = OutcomeEvaluationEngine().evaluate(
        manager=MarketDataManager(), now=datetime.now()
    )
    if result.get("reason") == OutcomeEvaluationEngine.CYCLE_IN_PROGRESS_REASON:
        raise HTTPException(status_code=409, detail=result["reason"])
    return {"outcome_evaluation": result}


@app.get("/outcomes")
def outcomes_read(
    ticker: str | None = Query(default=None, min_length=1),
    horizon: int | None = Query(default=None, gt=0),
    evaluation_source: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=200, gt=0),
):
    """Bounded, read-only outcome evidence feed."""
    from database.repository import OUTCOME_READ_MAX_LIMIT, get_outcomes

    safe_limit = min(limit, OUTCOME_READ_MAX_LIMIT)
    rows = get_outcomes(
        ticker=ticker.upper() if ticker else None,
        horizon=horizon,
        evaluation_source=evaluation_source,
        limit=safe_limit,
    )
    return {
        "outcomes": rows,
        "meta": {
            "count": len(rows),
            "limit": safe_limit,
            "filters": {
                "ticker": ticker.upper() if ticker else None,
                "horizon": horizon,
                "evaluation_source": evaluation_source,
            },
            "read_only": True,
        },
    }


@app.get(
    "/recommendations/{recommendation_id}/outcomes",
    response_model=RecommendationOutcomesResponse,
    response_model_exclude_unset=True,
)
def recommendation_outcomes_read(recommendation_id: int):
    """Read-only outcome evidence for one exact persisted recommendation."""
    from database.repository import get_outcomes_for_recommendation

    rows = get_outcomes_for_recommendation(recommendation_id)
    return {
        "recommendation_outcomes": rows,
        "meta": {
            "recommendation_id": recommendation_id,
            "count": len(rows),
            "read_only": True,
        },
    }


@app.get("/outcomes/status")
def outcomes_status():
    """Pure read of outcome gates, evidence counts, and last run status."""
    return {"outcome_status": OutcomeEvaluationEngine().status()}


@app.get("/recommendation-intelligence")
def recommendation_intelligence(
    ticker: str | None = Query(default=None, min_length=1),
    action: str | None = Query(default=None, pattern="^(BUY|HOLD|AVOID)$"),
    horizon: int | None = Query(default=None, gt=0),
    evaluation_source: str = Query(default="paper", min_length=1),
    rolling_window: int = Query(default=20, gt=0, le=500),
    top_limit: int = Query(default=10, gt=0, le=100),
):
    """Read-only historical recommendation accuracy and calibration analytics."""
    return {
        "recommendation_intelligence": RecommendationIntelligenceEngine().report(
            ticker=ticker.upper() if ticker else None,
            action=action,
            horizon=horizon,
            evaluation_source=evaluation_source,
            rolling_window=rolling_window,
            top_limit=top_limit,
        )
    }


@app.get(
    "/recommendation-intelligence/records",
    response_model=RecommendationIntelligenceRecordsResponse,
    response_model_exclude_unset=True,
)
def recommendation_intelligence_records(
    ticker: str | None = Query(default=None, min_length=1),
    action: str | None = Query(default=None, pattern="^(BUY|HOLD|AVOID)$"),
    horizon: int | None = Query(default=None, gt=0),
    evaluation_source: str = Query(default="paper", min_length=1),
    limit: int = Query(default=500, gt=0),
):
    """Bounded selector-ready recommendation/outcome evidence rows."""
    from database.repository import get_recommendation_intelligence_records

    source = get_recommendation_intelligence_records(
        ticker=ticker,
        action=action,
        horizon=horizon,
        evaluation_source=evaluation_source,
        limit=limit,
    )
    return {
        "recommendation_intelligence_records": source["records"],
        "meta": {key: source[key] for key in ("total", "limit", "truncated", "filters")}
        | {"read_only": True},
    }


def _learning_selectors(
    ticker, committee, engine, sector, regime, horizon,
    evaluation_source, rolling_window, limit,
):
    return {
        "ticker": ticker.upper() if ticker else None,
        "committee": committee,
        "engine": engine,
        "sector": sector,
        "regime": regime,
        "horizon": horizon,
        "evaluation_source": evaluation_source,
        "rolling_window": rolling_window,
        "limit": limit,
    }


@app.get(
    "/learning-center",
    response_model=LearningCenterResponse,
    response_model_exclude_unset=True,
)
def learning_center(
    ticker: str | None = Query(default=None, min_length=1),
    committee: str | None = Query(default=None, min_length=1),
    engine: str | None = Query(default=None, min_length=1),
    sector: str | None = Query(default=None, min_length=1),
    regime: str | None = Query(default=None, min_length=1),
    horizon: int | None = Query(default=None, gt=0),
    evaluation_source: str = Query(default="paper", min_length=1),
    rolling_window: int = Query(default=20, gt=0, le=500),
    limit: int = Query(default=10000, gt=0, le=100000),
):
    """Bounded, read-only Learning Intelligence aggregate."""
    return {"learning_center": LearningCenterEngine().report(**_learning_selectors(
        ticker, committee, engine, sector, regime, horizon,
        evaluation_source, rolling_window, limit,
    ))}


@app.get(
    "/learning-center/status",
    response_model=LearningCenterStatusResponse,
    response_model_exclude_unset=True,
)
def learning_center_status(limit: int = Query(default=10000, gt=0, le=100000)):
    return {"learning_center_status": LearningCenterEngine().status(limit=limit)}


@app.get("/committee-intelligence")
def committee_intelligence(
    ticker: str | None = Query(default=None, min_length=1),
    committee: str | None = Query(default=None, min_length=1),
    engine: str | None = Query(default=None, min_length=1),
    sector: str | None = Query(default=None, min_length=1),
    regime: str | None = Query(default=None, min_length=1),
    horizon: int | None = Query(default=None, gt=0),
    evaluation_source: str = Query(default="paper", min_length=1),
    rolling_window: int = Query(default=20, gt=0, le=500),
    limit: int = Query(default=10000, gt=0, le=100000),
):
    return {"committee_intelligence": CommitteeIntelligenceEngine().report(
        ticker=ticker.upper() if ticker else None,
        committee=committee,
        engine=engine,
        sector=sector,
        regime=regime,
        horizon=horizon,
        evaluation_source=evaluation_source,
        rolling_window=rolling_window,
        limit=limit,
    )}


@app.get("/committee-intelligence/leaderboard")
def committee_intelligence_leaderboard(
    ticker: str | None = Query(default=None, min_length=1),
    committee: str | None = Query(default=None, min_length=1),
    engine: str | None = Query(default=None, min_length=1),
    sector: str | None = Query(default=None, min_length=1),
    regime: str | None = Query(default=None, min_length=1),
    horizon: int | None = Query(default=None, gt=0),
    evaluation_source: str = Query(default="paper", min_length=1),
    rolling_window: int = Query(default=20, gt=0, le=500),
    limit: int = Query(default=10000, gt=0, le=100000),
):
    report = CommitteeIntelligenceEngine().report(
        ticker=ticker.upper() if ticker else None, committee=committee, engine=engine,
        sector=sector, regime=regime, horizon=horizon,
        evaluation_source=evaluation_source, rolling_window=rolling_window,
        limit=limit,
    )
    return {"committee_leaderboard": report["leaderboard"], "meta": report["data"]}


@app.get("/committee-intelligence/status")
def committee_intelligence_status(limit: int = Query(default=10000, gt=0, le=100000)):
    return {"committee_intelligence_status": CommitteeIntelligenceEngine().status(limit=limit)}


@app.get("/engine-intelligence")
def engine_intelligence(
    ticker: str | None = Query(default=None, min_length=1),
    engine: str | None = Query(default=None, min_length=1),
    committee: str | None = Query(default=None, min_length=1),
    sector: str | None = Query(default=None, min_length=1),
    regime: str | None = Query(default=None, min_length=1),
    horizon: int | None = Query(default=None, gt=0),
    evaluation_source: str = Query(default="paper", min_length=1),
    rolling_window: int = Query(default=20, gt=0, le=500),
    limit: int = Query(default=10000, gt=0, le=100000),
):
    return {"engine_intelligence": EngineIntelligenceEngine().report(
        ticker=ticker.upper() if ticker else None,
        engine=engine,
        committee=committee,
        sector=sector,
        regime=regime,
        horizon=horizon,
        evaluation_source=evaluation_source,
        rolling_window=rolling_window,
        limit=limit,
    )}


@app.get("/engine-intelligence/leaderboard")
def engine_intelligence_leaderboard(
    ticker: str | None = Query(default=None, min_length=1),
    engine: str | None = Query(default=None, min_length=1),
    committee: str | None = Query(default=None, min_length=1),
    sector: str | None = Query(default=None, min_length=1),
    regime: str | None = Query(default=None, min_length=1),
    horizon: int | None = Query(default=None, gt=0),
    evaluation_source: str = Query(default="paper", min_length=1),
    rolling_window: int = Query(default=20, gt=0, le=500),
    limit: int = Query(default=10000, gt=0, le=100000),
):
    report = EngineIntelligenceEngine().report(
        ticker=ticker.upper() if ticker else None, engine=engine, committee=committee,
        sector=sector, regime=regime, horizon=horizon,
        evaluation_source=evaluation_source, rolling_window=rolling_window,
        limit=limit,
    )
    return {"engine_leaderboard": report["leaderboard"], "meta": report["data"]}


@app.get("/engine-intelligence/status")
def engine_intelligence_status(limit: int = Query(default=10000, gt=0, le=100000)):
    return {"engine_intelligence_status": EngineIntelligenceEngine().status(limit=limit)}


@app.get("/research-cycle/status")
def research_cycle_status():
    """Read-only autonomous-research status: gates, interval, due-ness."""
    return ResearchCycleEngine().status()


@app.get("/paper-fund/preflight")
def paper_fund_preflight():
    """Read-only live-paper readiness check.

    Strictly read-only: it never calls setup_database, runs a tick or cycle,
    writes to the database, or creates a simulated order. It composes config
    flags, in-memory provider health, calendar market status, and the current
    fund state into a GO / NO-GO verdict. Disabled by default, so the default
    verdict is NO-GO.
    """
    from backend.live_paper_preflight import build_preflight_report

    return build_preflight_report()


@app.get("/scheduler/status")
def scheduler_status():
    """Read-only scheduler observability.

    Pure reads only: this never runs a tick, calls run_due_cycle, sets up the
    database, or writes anything. It reports scheduler loop metrics plus the
    gating flags and active market data provider so a dry run can be verified.
    ``last_persisted_tick`` is the newest durable tick record (with its skip
    reason), so tick history survives process restarts.
    """
    from core import settings
    from database.repository import get_latest_scheduler_tick

    return {
        "scheduler": scheduler_runtime.status(),
        "auto_fund_enabled": settings.AUTO_FUND_ENABLED,
        "provider": MarketDataManager().provider_name,
        "last_persisted_tick": get_latest_scheduler_tick(),
    }


def _paper_learning_status(latest_audit, reports):
    price_backed = bool(latest_audit and latest_audit.get("price_backed"))
    journal = get_latest_daily_journal()
    lessons = (journal or {}).get("lessons_learned") or {}
    latest_lesson = (
        lessons.get("most_useful_evidence_today")
        if isinstance(lessons, dict)
        else None
    )

    try:
        active_experiments = ResearchLabEngine().active_experiments()
    except Exception:
        active_experiments = []

    return {
        "learning_active": price_backed,
        "message": (
            "Atlas is learning from historical replay results."
            if price_backed
            else "Atlas has not started learning from paper trading yet."
        ),
        "latest_replay_result": latest_audit,
        "latest_lesson": latest_lesson,
        "analytics_updated": bool(reports),
        "active_experiments": len(active_experiments or []),
    }


@app.post("/daily-cycle/run")
def run_daily_cycle():
    result = _run_paper_simulation("full_daily_cycle")

    return {
        "simulation": result,
        "daily_cycle": daily_cycle_dashboard(),
        "daily_journal": daily_journal_dashboard(),
        "paper_portfolio": paper_portfolio_dashboard(),
        "paper_trades": paper_trades_dashboard(),
        "paper_performance": paper_performance_dashboard(),
        "policy": _paper_trading_policy() | {
            "status": "SIMULATED",
            "automatic_execution": False,
            "human_approval_required_for_real_trading": True,
        },
    }


@app.get("/runtime")
def runtime_dashboard():
    state = get_latest_runtime_state() or RuntimeEngine().build_state(
        current_state="IDLE",
    )

    return {
        "runtime": state,
        "runtime_history": get_runtime_states(limit=20),
        "policy": state["policy"],
    }


@app.get("/runtime/status")
def runtime_status_dashboard():
    state = get_latest_runtime_state() or RuntimeEngine().build_state(
        current_state="IDLE",
    )

    return RuntimeEngine().runtime_status(state)


@app.get("/runtime/tasks")
def runtime_tasks_dashboard():
    state = get_latest_runtime_state() or RuntimeEngine().build_state(
        current_state="IDLE",
    )

    return RuntimeEngine().runtime_tasks(state)


@app.get("/daily-cycle")
def daily_cycle_dashboard():

    return {
        "daily_cycle_runs": get_daily_cycle_runs(limit=50),
        "policy": _paper_trading_policy() | {
            "human_approval_required_for_real_trading": True,
        },
    }


@app.get("/daily-cycle/latest")
def latest_daily_cycle_dashboard():

    return {
        "latest_daily_cycle": get_latest_daily_cycle_run(),
        "policy": _paper_trading_policy() | {
            "human_approval_required_for_real_trading": True,
        },
    }


@app.get("/daily-journal")
def daily_journal_dashboard():

    return {
        "daily_journals": get_daily_journals(limit=50),
        "policy": _paper_trading_policy() | {
            "deterministic": True,
            "permanent_research_record": True,
        },
    }


@app.get("/daily-journal/latest")
def latest_daily_journal_dashboard():

    return {
        "latest_daily_journal": get_latest_daily_journal(),
        "policy": _paper_trading_policy() | {
            "deterministic": True,
            "permanent_research_record": True,
        },
    }


@app.get("/research-memory")
def research_memory_dashboard(ticker: str | None = None):
    engine = ResearchMemoryEngine()

    if ticker:
        source_data = get_discovery_source_data()
        target = next(
            (
                item for item in source_data.get("recommendations", [])
                if item.get("ticker", "").upper() == ticker.upper()
            ),
            {"ticker": ticker.upper()},
        )

        return engine.build(target, source_data=source_data)

    return engine.build()


@app.get("/market/status")
def market_status_dashboard():
    manager = MarketDataManager()
    snapshot = manager.snapshot()
    cache_stats = manager.cache_status()["stats"]
    from market.provider_health import data_freshness

    return {
        "market_status": snapshot["market_status"],
        "snapshot": snapshot,
        "data_freshness": data_freshness(cache_stats.get("latest_age")),
        "latest_persisted_snapshot": get_latest_market_data_snapshot(),
        "policy": manager.policy(),
    }


@app.get("/market/provider")
def market_provider_dashboard():
    manager = MarketDataManager()

    return manager.provider_summary()


@app.get("/market/health")
def market_health_dashboard():
    manager = MarketDataManager()
    manager.snapshot()

    return {
        "health": manager.health(),
        "cache_stats": manager.cache_status()["stats"],
        "policy": manager.policy(),
    }


@app.get("/market/cache")
def market_cache_dashboard():
    manager = MarketDataManager()
    manager.snapshot()

    return manager.cache_status()


@app.get("/providers")
def providers_dashboard():
    registry = ProviderRegistry()

    return {
        "summary": registry.summary(),
        "providers": registry.providers(),
        "metadata": registry.metadata(),
    }


@app.get("/provider-health")
def provider_health_dashboard():
    return ProviderRegistry().health()


@app.get("/sec")
def sec_dashboard(ticker: str | None = None, form_type: str | None = None):
    tickers = [ticker.upper()] if ticker else None
    filing_types = [form_type.upper()] if form_type else None

    return SecEngine().analyze(
        tickers=tickers,
        filing_types=filing_types,
    )


@app.get("/sec-summary")
def sec_summary_dashboard():
    engine = SecEngine()

    return {
        "summary": engine.summary(),
        "health": engine.health_check(),
        "policy": {
            "read_only": True,
            "mock_default": True,
            "requires_api_key": False,
            "changes_recommendation_behavior": False,
        },
    }


@app.get("/macro")
def macro_dashboard():
    return MacroEngine().analyze()


@app.get("/macro-summary")
def macro_summary_dashboard():
    engine = MacroEngine()

    return {
        "summary": engine.summary(),
        "health": engine.health_check(),
        "policy": {
            "read_only": True,
            "mock_default": True,
            "requires_api_key": False,
            "changes_recommendation_behavior": False,
        },
    }


@app.get("/institutional-report/{ticker}")
def institutional_report(ticker: str):

    return InstitutionalReportEngine().generate(ticker)


@app.get("/knowledge-graph")
def knowledge_graph(query_type: str | None = None, value: str | None = None):
    engine = KnowledgeGraphEngine()
    graph = engine.build()

    if query_type:
        return {
            "query_type": query_type,
            "value": value,
            "results": engine.query(graph, query_type, value),
        }

    return graph


def _run_paper_simulation(mode, paper_mode=None):
    engine = DailyCycleEngine()
    paper_engine = PaperTradingEngine()
    history = get_paper_portfolio_history(limit=50)
    run_number = len({
        item.get("run_id")
        for item in history
        if item.get("run_id")
    }) + 1
    step = run_number
    cycle_date = f"2026-07-{run_number + 1:02d}"
    normalized_mode = (mode or "full_daily_cycle").lower()
    normalized_paper_mode = (paper_mode or "daily_cycle_simulation").lower()

    if normalized_paper_mode in REMOVED_PAPER_MODES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Demo paper trading has been removed. Use Historical Price "
                "Replay through POST /paper-replay/run instead."
            ),
        )

    if normalized_paper_mode in {"broker_paper_pending", "future_broker_paper_placeholder"}:
        raise HTTPException(
            status_code=400,
            detail=(
                "Broker paper trading is pending architecture only. "
                "Execution is disabled; see GET /paper-broker/status."
            ),
        )

    metadata = {
        "run_id": f"paper-sim-{run_number:04d}",
        "run_number": run_number,
        "simulated_at": f"{cycle_date}T16:00:00",
        "mode": normalized_paper_mode,
        "data_source": "deterministic cycle prices (not persisted as paper data)",
    }
    recommendations = paper_engine.demo_recommendations()
    portfolio = _latest_paper_portfolio_state(history)

    if normalized_paper_mode in {"historical_price_simulation", "historical_price_replay"}:
        metadata |= {
            "mode": "historical_price_replay",
            "data_source": "historical Yahoo data",
        }
        report = paper_engine.run_historical_price_replay(
            recommendations=recommendations,
            tickers=[item["ticker"] for item in recommendations],
            start_date="2024-01-01",
            end_date="2024-02-15",
            simulation_metadata=metadata,
            persist=True,
        )

        return {
            "mode": "historical_price_replay",
            "date": report["portfolio"]["date"],
            "metadata": report["metadata"],
            "paper_report": report,
            "status": report["replay_status"],
        }

    if normalized_mode == "pre_market":
        cycle = engine.run_phase(
            "pre_market",
            cycle_date=cycle_date,
            recommendations=recommendations,
            persist=True,
        )
        return {
            "mode": normalized_mode,
            "date": cycle_date,
            "phases": [cycle],
            "latest_phase": cycle,
            "status": "SIMULATED",
        }

    if normalized_mode == "market_close":
        cycle = engine.run_phase(
            "market_close",
            cycle_date=cycle_date,
            recommendations=recommendations,
            market_prices=paper_engine.demo_market_prices(step),
            portfolio=portfolio,
            benchmark_returns=paper_engine.demo_benchmark_returns(step),
            simulation_metadata=metadata,
            persist=True,
        )
        return {
            "mode": normalized_mode,
            "date": cycle_date,
            "metadata": metadata,
            "phases": [cycle],
            "latest_phase": cycle,
            "paper_report": cycle["details"]["paper_report"],
            "status": "SIMULATED",
        }

    if normalized_mode not in {"full_daily_cycle", "full"}:
        raise HTTPException(status_code=400, detail="Unsupported paper simulation mode")

    result = engine.run_simulated_daily_cycle(
        cycle_date=cycle_date,
        portfolio=portfolio,
        step=step,
        simulation_metadata=metadata,
        persist=True,
    )

    return result | {
        "mode": "full_daily_cycle",
        "metadata": metadata,
        "status": "SIMULATED",
    }


def _run_paper_replay(payload):
    tickers = [
        str(ticker).upper()
        for ticker in payload.get("tickers", APPROVED_TICKERS[:2])
        if str(ticker).strip()
    ]
    if not tickers:
        raise HTTPException(status_code=400, detail="At least one replay ticker is required.")

    mode = payload.get("mode", "historical_price_replay")
    if mode != "historical_price_replay":
        raise HTTPException(status_code=400, detail="Unsupported paper replay mode.")

    history = get_paper_portfolio_history(limit=200)
    run_number = len({
        item.get("run_id")
        for item in history
        if item.get("run_id")
    }) + 1
    start_date = payload.get("start_date", "2024-01-01")
    end_date = payload.get("end_date", "2024-02-15")
    metadata = {
        "run_id": f"paper-replay-{run_number:04d}",
        "run_number": run_number,
        "simulated_at": f"{end_date}T16:00:00",
        "mode": "historical_price_replay",
        "data_source": "historical Yahoo data",
    }
    try:
        allocation_percent = float(payload.get("allocation_percent"))
    except (TypeError, ValueError):
        allocation_percent = None
    if allocation_percent is None or allocation_percent <= 0 or allocation_percent > 100:
        # Equal-weight default across the requested tickers.
        allocation_percent = round(100 / len(tickers), 4)
    recommendations = [
        {
            "ticker": ticker,
            "action": "BUY",
            "confidence": 0,
            "reason": f"Deterministic replay snapshot for {ticker}.",
            "sector": "Replay",
            "status": "REPLAY_SNAPSHOT",
            "suggested_allocation": allocation_percent,
        }
        for ticker in tickers
    ]
    report = PaperTradingEngine().run_historical_price_replay(
        recommendations=recommendations,
        historical_rows=payload.get("historical_rows"),
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        starting_cash=payload.get("starting_cash", PaperTradingEngine.INITIAL_CASH),
        simulation_metadata=metadata,
        persist=True,
    )

    return report


def _latest_paper_portfolio_state(history):
    if not history:
        return {}

    latest = history[0]
    ordered_history = list(reversed(history))

    return {
        "cash": latest.get("cash", 0),
        "positions": latest.get("positions", {}),
        "realized_pl": latest.get("realized_pl", 0),
        "history": ordered_history,
        "trades": get_paper_trades(limit=200),
    }


def _portfolio_construction_report():
    source_data = get_discovery_source_data()
    recommendations = source_data.get("recommendations", [])
    engine = PortfolioConstructionEngine()
    if not recommendations:
        recommendations = engine.demo_recommendations()

    paper_history = source_data.get("paper_portfolio_history", [])
    paper_portfolio = (
        paper_history[0]
        if paper_history
        else engine.demo_portfolio()
    )
    macro = MacroEngine().analyze()
    probability_reports = [
        item.get("probability_report")
        for item in recommendations
        if isinstance(item.get("probability_report"), dict)
    ]

    if not probability_reports:
        probability_reports = ProbabilityEngine().estimate_many(
            recommendations,
            history=recommendations,
            case_studies=source_data.get("case_studies", []),
        )

    return engine.build(
        recommendations=recommendations,
        paper_portfolio=paper_portfolio,
        macro_state=macro,
        probabilities=probability_reports,
    )


def _system_health():
    forecast = _forecast_information()

    return {
        "backend_status": "Online",
        "database_status": "Connected",
        "forecast_provider": forecast["display_name"],
        "validation_status": "Ready",
        "backtesting_availability": "Available",
        "news_engine_status": "Available",
    }


def _forecast_information():
    kronos_available = KronosForecastProvider.is_available()
    provider = FORECAST_PROVIDER

    if provider == "kronos" and kronos_available:
        display_name = "Kronos"
    elif not kronos_available:
        display_name = "Mock (Kronos unavailable)"
    else:
        display_name = "Mock"

    return {
        "current_provider": provider,
        "display_name": display_name,
        "kronos_available": kronos_available,
    }


def _data_provider_health():
    return data_provider_health()


def _news_provider_health():
    try:
        engine = NewsEngine()
        health = engine.health_check()
        analysis = engine.analyze("AAPL")
        headline_available = analysis["headline_count"] > 0
        healthy = bool(health["healthy"]) and headline_available
        failure_message = ""

        if not headline_available:
            failure_message = getattr(engine.provider, "last_error", "")
            failure_message = failure_message or "No headlines available."

        return {
            "active_provider": analysis["provider"],
            "healthy": healthy,
            "headline_availability": headline_available,
            "failure_message": failure_message,
        }
    except Exception as error:
        return {
            "active_provider": "unknown",
            "healthy": False,
            "headline_availability": False,
            "failure_message": str(error),
        }


def _fundamental_provider_health():
    try:
        engine = FundamentalEngine()
        health = engine.health_check()
        analysis = engine.analyze("AAPL")
        data_available = analysis["revenue"] > 0 or analysis["market_cap"] > 0
        healthy = bool(health["healthy"]) and data_available
        failure_message = ""

        if not data_available:
            failure_message = getattr(engine.provider, "last_error", "")
            failure_message = failure_message or "No fundamentals available."

        return {
            "active_provider": analysis["provider"],
            "healthy": healthy,
            "data_availability": data_available,
            "failure_message": failure_message,
        }
    except Exception as error:
        return {
            "active_provider": "unknown",
            "healthy": False,
            "data_availability": False,
            "failure_message": str(error),
        }


def _pipeline_status():
    provider_health = _data_provider_health()
    forecast = _forecast_information()

    return {
        "pipeline_active": True,
        "execution_mode": "IntelligencePipeline",
        "data_provider": provider_health["active_provider"],
        "forecast_provider": forecast["display_name"],
        "validation_available": True,
        "benchmark_available": True,
    }


def _fusion_status():
    try:
        result = IntelligenceFusionEngine().fuse(
            technical=80,
            fundamentals=75,
            forecast=70,
            news=60,
            portfolio=65,
            risk=70,
        )

        return {
            "status": "PASS" if result["overall_conviction"] > 0 else "WARN",
            "overall_conviction": result["overall_conviction"],
            "message": result["fusion_summary"],
        }
    except Exception as error:
        return {
            "status": "FAIL",
            "overall_conviction": 0,
            "message": str(error),
        }


def _paper_trading_policy():
    return {
        "paper_only": True,
        "broker_integration": False,
        "real_money": False,
        "automatic_execution": False,
        "changes_recommendation_behavior": False,
    }
