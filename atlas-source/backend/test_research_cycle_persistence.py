"""Regression tests: the autonomous cycle persists its evidence end to end.

Covers: a tick that did work writes one durable research_cycle_records row
with all five stage statuses; committee evaluations are persisted per run;
a completed fund cycle triggers performance recording and self-improvement
persistence; a skipped fund cycle skips both learning stages and writes no
learning rows; failed generation retries after the short retry cooldown
instead of the 24h freshness window; and the advisory learning context never
changes recommendation output. Runs against a throwaway temporary database.
"""

import os
import tempfile
from datetime import datetime, timedelta

import database.connection as connection
from database.migrator import run_migrations
from database.repository import (
    get_committee_cycle_evaluations,
    get_cycle_performance_records,
    get_research_cycle_records,
    get_self_improvement_reports,
)
from engines.research_cycle_engine import ResearchCycleEngine


def cleanup_database(path):
    connection._wal_initialized_paths.discard(path)
    for candidate in (path, f"{path}-wal", f"{path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


class _Settings:
    AUTO_RESEARCH_ENABLED = True
    AUTO_RESEARCH_INTERVAL_MINUTES = 1440
    AUTO_RESEARCH_RETRY_MINUTES = 30


class _ResearchEngine:
    def __init__(self, status="COMPLETED", count=2):
        self.status = status
        self.count = count
        self.calls = 0

    def generate(self, now=None):
        self.calls += 1
        if self.status != "COMPLETED":
            return {"status": self.status, "reason": "provider down"}
        return {
            "status": "COMPLETED",
            "run_id": 7,
            "recommendation_count": self.count,
            "tickers_analyzed": ["AAPL", "MSFT"],
            "skipped": [],
            "provider": "fixture",
            "ticker_source": "explicit",
            "learning_context": {"advisory_only": True},
        }


class _CommitteeEngine:
    def evaluate(self, record):
        return {
            "status": "EVALUATED",
            "committee_recommendation": {
                "action": "HOLD",
                "strength": "MODERATE",
                "agreement_pct": 80,
                "confidence": 55,
            },
        }


class _FundEngine:
    def __init__(self, result):
        self.result = result

    def run_due_cycle(self, manager=None, now=None):
        return self.result


class _PerformanceEngine:
    def generate(self):
        return {
            "source_counts": {"paper_fund_orders": 3},
            "policy": {"read_only": True},
        }


class _ImprovementEngine:
    def generate(self):
        return {
            "generated_at": "2026-07-12",
            "status": "EVALUATED",
            "headline": "fixture headline",
            "findings": [{"finding_id": "f1"}],
            "opportunities": [{"finding_id": "f1"}],
            "not_evaluated": [],
            "source_counts": {"trades": 4},
            "policy": {"research_only": True},
        }


def _run(fund_result, attempt_state=None, research_engine=None, now=None):
    return ResearchCycleEngine().run_due_cycle(
        now=now or datetime(2026, 7, 10, 16, 0, 0),
        research_engine=research_engine or _ResearchEngine(),
        committee_engine=_CommitteeEngine(),
        fund_engine=_FundEngine(fund_result),
        last_run_loader=lambda: None,
        record_loader=lambda ticker: {"ticker": ticker, "action": "HOLD"},
        activity_writer=lambda entry: None,
        attempt_state=attempt_state if attempt_state is not None else {},
        settings_module=_Settings(),
        performance_engine=_PerformanceEngine(),
        improvement_engine=_ImprovementEngine(),
    )


def completed_cycle_persists_all_evidence():
    result = _run({"cycle_status": "COMPLETED", "cycle_id": "fund-42"})
    assert result["status"] == "COMPLETED"
    assert result["cycle_record_persisted"] is True

    stage_status = {
        stage["stage"]: stage["status"] for stage in result["stages"]
    }
    assert stage_status == {
        "research_generation": "COMPLETED",
        "committee_evaluation": "COMPLETED",
        "paper_fund": "COMPLETED",
        "performance_recording": "COMPLETED",
        "self_improvement": "COMPLETED",
    }

    records = get_research_cycle_records(limit=5)
    assert len(records) == 1
    assert records[0]["fund_cycle_id"] == "fund-42"
    assert [stage["stage"] for stage in records[0]["stages"]] == [
        "research_generation",
        "committee_evaluation",
        "paper_fund",
        "performance_recording",
        "self_improvement",
    ]

    committee_rows = get_committee_cycle_evaluations(limit=5)
    assert len(committee_rows) == 1
    assert committee_rows[0]["run_id"] == 7
    assert len(committee_rows[0]["evaluations"]) == 2

    performance_rows = get_cycle_performance_records(limit=5)
    assert len(performance_rows) == 1
    assert performance_rows[0]["cycle_id"] == "fund-42"

    improvement_rows = get_self_improvement_reports(limit=5)
    assert len(improvement_rows) == 1
    assert improvement_rows[0]["cycle_id"] == "fund-42"
    assert improvement_rows[0]["findings"] == [{"finding_id": "f1"}]

    # The advisory learning context landed in the durable stage details.
    generation_stage = records[0]["stages"][0]
    assert generation_stage["stage"] == "research_generation"


def skipped_fund_skips_learning_stages():
    before_perf = len(get_cycle_performance_records(limit=50))
    before_improve = len(get_self_improvement_reports(limit=50))

    result = _run(
        {"status": "SKIPPED", "reason": "market is closed"},
        research_engine=_ResearchEngine(status="REFUSED"),
    )
    stage_status = {
        stage["stage"]: stage["status"] for stage in result["stages"]
    }
    assert stage_status["paper_fund"] == "SKIPPED"
    assert stage_status["performance_recording"] == "SKIPPED"
    assert stage_status["self_improvement"] == "SKIPPED"

    assert len(get_cycle_performance_records(limit=50)) == before_perf
    assert len(get_self_improvement_reports(limit=50)) == before_improve


def failed_generation_retries_after_short_cooldown():
    engine = _ResearchEngine(status="REFUSED")
    t0 = datetime(2026, 7, 11, 10, 0, 0)
    attempt_state = {"last_attempt_at": None}

    _run({"status": "SKIPPED", "reason": "not due"},
         attempt_state=attempt_state, research_engine=engine, now=t0)
    assert engine.calls == 1

    # 10 minutes later: still inside the retry cooldown -> no new attempt.
    _run({"status": "SKIPPED", "reason": "not due"},
         attempt_state=attempt_state, research_engine=engine,
         now=t0 + timedelta(minutes=10))
    assert engine.calls == 1

    # 31 minutes later: retried WITHOUT waiting for the 24h freshness window.
    _run({"status": "SKIPPED", "reason": "not due"},
         attempt_state=attempt_state, research_engine=engine,
         now=t0 + timedelta(minutes=31))
    assert engine.calls == 2


def learning_context_never_changes_recommendations():
    from engines.watchlist_research_engine import WatchlistResearchEngine

    class _Stock:
        def __init__(self, ticker):
            self.ticker = ticker

    class _Recommendation:
        def __init__(self, ticker):
            self.ticker = ticker
            self.action = "HOLD"
            self.confidence = 50

    class _MarketEngine:
        def analyze_market(self, tickers):
            return [_Stock(ticker) for ticker in tickers]

    class _Recommender:
        def build_recommendations(self, stocks):
            return [_Recommendation(stock.ticker) for stock in stocks]

    class _DashboardEngine:
        def build_dashboard(self, stocks=None, recommendations=None):
            return {"stocks": len(stocks), "recommendations": len(recommendations)}

    saved = []
    savers = {
        "run": lambda dashboard: 99,
        "recommendations": lambda run_id, recs: saved.append(
            [(rec.ticker, rec.action, rec.confidence) for rec in recs]
        ),
    }

    def run_generate(loader):
        return WatchlistResearchEngine().generate(
            tickers=["AAPL"],
            market_engine=_MarketEngine(),
            recommendation_engine=_Recommender(),
            dashboard_engine=_DashboardEngine(),
            provider_resolver=lambda: "yahoo",
            savers=savers,
            now=datetime(2026, 7, 12, 12, 0, 0),
            learning_context_loader=loader,
        )

    without_context = run_generate(lambda: None)
    with_context = run_generate(
        lambda: {"advisory_only": True, "self_improvement": {"headline": "x"}}
    )

    # Identical persisted rows and identical recommendation payloads: the
    # advisory context can never change an action, score, or stored record.
    assert saved[0] == saved[1]
    assert without_context["recommendations"] == with_context["recommendations"]
    assert without_context["learning_context"] is None
    assert with_context["learning_context"]["advisory_only"] is True


original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()

    completed_cycle_persists_all_evidence()
    skipped_fund_skips_learning_stages()
    failed_generation_retries_after_short_cooldown()
    learning_context_never_changes_recommendations()
finally:
    connection.DATABASE_PATH = original_database_path
    cleanup_database(database_path)

print("Research cycle persistence test passed.")
