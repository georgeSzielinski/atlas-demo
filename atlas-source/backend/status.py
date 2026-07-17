import importlib
import sqlite3
import sys
from pathlib import Path

from core.settings import FORECAST_PROVIDER
from database.connection import get_connection
from engines.catalyst_engine import CatalystEngine
from engines.fundamental_engine import FundamentalEngine
from engines.intelligence_fusion_engine import IntelligenceFusionEngine
from engines.macro_engine import MacroEngine
from engines.news_engine import NewsEngine
from engines.sec_engine import SecEngine
from market.data import data_provider_health, historical_data_provider_health
from market.provider_registry import ProviderRegistry


DATABASE_PATH = Path("database/atlas.db")
REPORTS_PATH = Path("reports")

MODULES_TO_CHECK = [
    "atlas.application",
    "services.investment_platform",
    "engines.market_engine",
    "engines.recommendation_engine",
    "engines.forecast_engine",
    "engines.markdown_report_engine",
    "engines.performance_observatory",
    "engines.performance_analytics_engine",
    "engines.research_lab_engine",
    "engines.portfolio_construction_engine",
    "engines.executive_review_engine",
    "engines.historical_runner",
    "engines.daily_cycle_engine",
    "engines.runtime_engine",
    "engines.runtime_scheduler",
    "engines.runtime_state",
    "engines.knowledge_graph_engine",
    "engines.macro_engine",
    "engines.sec_engine",
    "market.provider_registry",
    "market.market_data_manager",
    "market.market_calendar",
    "market.data_validator",
    "market.data_cache",
    "database.repository",
]


def count_rows(table_name):
    if not DATABASE_PATH.exists():
        return 0

    # Use the shared hardened connection factory (busy timeout, foreign keys,
    # WAL) instead of a bare sqlite3.connect.
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
    except sqlite3.Error:
        count = 0
    finally:
        connection.close()

    return count


def markdown_reports():
    if not REPORTS_PATH.exists():
        return []

    return sorted(
        REPORTS_PATH.glob("*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )


def import_status(module_name):
    try:
        importlib.import_module(module_name)
        return "PASS"
    except Exception:
        return "FAIL"


def pipeline_status():
    provider_health = data_provider_health()
    historical_provider_health = historical_data_provider_health()
    pipeline_available = (
        import_status("services.investment_platform") == "PASS"
    )
    validation_available = import_status("engines.validation_engine") == "PASS"
    benchmark_available = import_status("engines.benchmark_engine") == "PASS"
    construction_available = (
        import_status("engines.portfolio_construction_engine") == "PASS"
    )

    return {
        "pipeline_active": pipeline_available,
        "execution_mode": "IntelligencePipeline"
        if pipeline_available
        else "Unavailable",
        "data_provider": provider_health["active_provider"],
        "historical_provider": historical_provider_health["active_provider"],
        "catalyst_provider": catalyst_provider_status()["active_provider"],
        "sec_provider": sec_provider_status()["provider"],
        "macro_provider": macro_provider_status()["provider"],
        "forecast_provider": FORECAST_PROVIDER,
        "validation_available": validation_available,
        "benchmark_available": benchmark_available,
        "portfolio_construction_available": construction_available,
        "provider_registry": provider_registry_status()["summary"],
    }


def provider_registry_status():
    registry = ProviderRegistry()

    return {
        "summary": registry.summary(),
        "health": registry.health(),
        "offline_capability": registry.summary()["offline_capability"],
        "experimental_providers": registry.summary()["experimental_providers"],
    }


def status_label(passed):
    return "PASS" if passed else "FAIL"


def news_provider_status():
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


def fundamental_provider_status():
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


def catalyst_provider_status():
    try:
        engine = CatalystEngine()
        health = engine.health_check(
            tickers=["AAPL", "MSFT"],
            as_of_date="2026-06-30",
        )

        return {
            "active_provider": health["active_provider"],
            "healthy": health["healthy"],
            "events_available": health["events_available"],
            "date_range": health["date_range"],
            "failure_message": health["failure_message"],
        }
    except Exception as error:
        return {
            "active_provider": "unknown",
            "healthy": False,
            "events_available": 0,
            "date_range": {"start_date": None, "end_date": None},
            "failure_message": str(error),
        }


def sec_provider_status():
    try:
        health = SecEngine().health_check()
        return {
            "provider": health["provider"],
            "status": health["status"],
            "healthy": health["healthy"],
            "fallback_used": health["fallback_used"],
            "filing_types": health["filing_types"],
            "supports_offline": health["supports_offline"],
            "requires_api_key": health["requires_api_key"],
            "failure_message": health["failure_message"],
        }
    except Exception as error:
        return {
            "provider": "unknown",
            "status": "Unavailable",
            "healthy": False,
            "fallback_used": False,
            "filing_types": [],
            "supports_offline": False,
            "requires_api_key": False,
            "failure_message": str(error),
        }


def macro_provider_status():
    try:
        engine = MacroEngine()
        report = engine.analyze()
        health = report["health"]
        return {
            "provider": health["provider"],
            "status": health["status"],
            "healthy": health["healthy"],
            "fallback_used": health["fallback_used"],
            "indicator_count": health["indicator_count"],
            "indicators": health["indicators"],
            "supports_offline": health["supports_offline"],
            "requires_api_key": health["requires_api_key"],
            "macro_regime": report["current_macro_regime"],
            "macro_risk_score": report["macro_risk_score"],
            "failure_message": health["failure_message"],
        }
    except Exception as error:
        return {
            "provider": "unknown",
            "status": "Unavailable",
            "healthy": False,
            "fallback_used": False,
            "indicator_count": 0,
            "indicators": [],
            "supports_offline": False,
            "requires_api_key": False,
            "macro_regime": "Unavailable",
            "macro_risk_score": 0,
            "failure_message": str(error),
        }


def fusion_status():
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


def main():
    reports = markdown_reports()

    print("ATLAS STATUS")
    print()

    print("Database:")
    print(f"- database/atlas.db exists: {status_label(DATABASE_PATH.exists())}")
    print(f"- atlas_runs: {count_rows('atlas_runs')}")
    print(f"- recommendations: {count_rows('recommendations')}")
    print(f"- portfolio_snapshots: {count_rows('portfolio_snapshots')}")
    print()

    print("Reports:")
    print(f"- Markdown reports: {len(reports)}")
    if reports:
        print(f"- Most recent report: {reports[0].name}")
    else:
        print("- Most recent report: None")
    print()

    print("Environment:")
    print(f"- Python version: {sys.version.split()[0]}")
    print(f"- Current working directory: {Path.cwd()}")
    print()

    registry_status = provider_registry_status()
    registry_summary = registry_status["summary"]
    health_summary = registry_status["health"]["summary"]

    print("Provider Registry:")
    print(f"- Providers registered: {registry_summary['provider_count']}")
    print(
        "- Categories: "
        f"{', '.join(registry_summary['categories'])}"
    )
    print(
        "- Offline capable providers: "
        f"{health_summary['offline_capable_count']}"
    )
    print(
        "- Experimental providers: "
        f"{len(registry_status['experimental_providers'])}"
    )
    print(
        "- Mock default: "
        f"{registry_summary['offline_capability']['mock_default']}"
    )
    print()

    provider_health = data_provider_health()

    print("Data Provider:")
    print(f"- Active provider: {provider_health['active_provider']}")
    print(
        "- Supported tickers count: "
        f"{provider_health['supported_tickers_count']}"
    )
    print(
        "- Latest price availability: "
        f"{provider_health['latest_price_available']}"
    )
    print(f"- Healthy: {status_label(provider_health['healthy'])}")

    if not provider_health["healthy"]:
        print(f"- Failure message: {provider_health['failure_message']}")
    else:
        print("- Failure message: None")

    print()

    historical_health = historical_data_provider_health()

    print("Historical Provider:")
    print(f"- Requested provider: {historical_health['requested_provider']}")
    print(f"- Active provider: {historical_health['active_provider']}")
    print(f"- Healthy: {status_label(historical_health['healthy'])}")
    print(f"- Rows available: {historical_health['rows_available']}")
    print(
        "- Date range: "
        f"{historical_health['date_range']['start_date']} to "
        f"{historical_health['date_range']['end_date']}"
    )
    print(f"- Fallback used: {historical_health['fallback_used']}")

    if not historical_health["healthy"]:
        print(f"- Failure message: {historical_health['failure_message']}")
    elif historical_health["failure_message"]:
        print(f"- Failure message: {historical_health['failure_message']}")
    else:
        print("- Failure message: None")

    print()

    news_health = news_provider_status()

    print("News Provider:")
    print(f"- Active provider: {news_health['active_provider']}")
    print(f"- Healthy: {status_label(news_health['healthy'])}")
    print(
        "- Headline availability: "
        f"{news_health['headline_availability']}"
    )

    if not news_health["healthy"]:
        print(f"- Failure message: {news_health['failure_message']}")
    else:
        print("- Failure message: None")

    print()

    fundamental_health = fundamental_provider_status()

    print("Fundamental Provider:")
    print(f"- Active provider: {fundamental_health['active_provider']}")
    print(f"- Healthy: {status_label(fundamental_health['healthy'])}")
    print(
        "- Data availability: "
        f"{fundamental_health['data_availability']}"
    )

    if not fundamental_health["healthy"]:
        print(f"- Failure message: {fundamental_health['failure_message']}")
    else:
        print("- Failure message: None")

    print()

    catalyst_health = catalyst_provider_status()

    print("Catalyst Provider:")
    print(f"- Active provider: {catalyst_health['active_provider']}")
    print(f"- Healthy: {status_label(catalyst_health['healthy'])}")
    print(f"- Events available: {catalyst_health['events_available']}")
    print(
        "- Date range: "
        f"{catalyst_health['date_range']['start_date']} to "
        f"{catalyst_health['date_range']['end_date']}"
    )

    if not catalyst_health["healthy"]:
        print(f"- Failure message: {catalyst_health['failure_message']}")
    else:
        print("- Failure message: None")

    print()

    sec_health = sec_provider_status()

    print("SEC Provider:")
    print(f"- Active provider: {sec_health['provider']}")
    print(f"- Status: {sec_health['status']}")
    print(f"- Healthy: {status_label(sec_health['healthy'])}")
    print(f"- Filing types: {', '.join(sec_health['filing_types'])}")
    print(f"- Offline capable: {sec_health['supports_offline']}")
    print(f"- Requires API key: {sec_health['requires_api_key']}")

    if not sec_health["healthy"]:
        print(f"- Failure message: {sec_health['failure_message']}")
    else:
        print("- Failure message: None")

    print()

    macro_health = macro_provider_status()

    print("Macro Provider:")
    print(f"- Active provider: {macro_health['provider']}")
    print(f"- Status: {macro_health['status']}")
    print(f"- Healthy: {status_label(macro_health['healthy'])}")
    print(f"- Macro regime: {macro_health['macro_regime']}")
    print(f"- Macro risk score: {macro_health['macro_risk_score']}")
    print(f"- Indicators: {macro_health['indicator_count']}")
    print(f"- Offline capable: {macro_health['supports_offline']}")
    print(f"- Requires API key: {macro_health['requires_api_key']}")

    if not macro_health["healthy"]:
        print(f"- Failure message: {macro_health['failure_message']}")
    else:
        print("- Failure message: None")

    print()

    fusion = fusion_status()

    print("Fusion Engine:")
    print(f"- Status: {fusion['status']}")
    print(f"- Conviction probe: {fusion['overall_conviction']}")
    print(f"- Message: {fusion['message']}")
    print()

    pipeline = pipeline_status()

    print("Intelligence Pipeline:")
    print(f"- Pipeline active: {status_label(pipeline['pipeline_active'])}")
    print(f"- Execution mode: {pipeline['execution_mode']}")
    print(f"- Data provider: {pipeline['data_provider']}")
    print(f"- Historical provider: {pipeline['historical_provider']}")
    print(f"- Catalyst provider: {pipeline['catalyst_provider']}")
    print(f"- Forecast provider: {pipeline['forecast_provider']}")
    print(
        "- Validation available: "
        f"{status_label(pipeline['validation_available'])}"
    )
    print(
        "- Benchmark available: "
        f"{status_label(pipeline['benchmark_available'])}"
    )
    print()

    health_checks = [
        provider_health["healthy"],
        historical_health["healthy"],
        news_health["healthy"],
        fundamental_health["healthy"],
        catalyst_health["healthy"],
        sec_health["healthy"],
        macro_health["healthy"],
        fusion["status"] == "PASS",
        pipeline["pipeline_active"],
        pipeline["validation_available"],
        pipeline["benchmark_available"],
        DATABASE_PATH.exists(),
    ]
    overall = "PASS" if all(health_checks) else "WARN"

    print("Overall Health:")
    print(f"- Status: {overall}")
    print()

    print("Core:")
    for module_name in MODULES_TO_CHECK:
        print(f"- {module_name}: {import_status(module_name)}")


if __name__ == "__main__":
    main()
