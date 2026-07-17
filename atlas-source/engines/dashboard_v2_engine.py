from datetime import datetime


class DashboardV2Engine:
    """Deterministic, read-only composition of Atlas' operational dashboard.

    DashboardV2Engine computes no analytics of its own. It composes the existing
    read-only engines (OperationsEngine, ReliabilityEngine, the paper-fund
    analytics engines, LivePaperFundEngine, and the read-only risk surface) into
    one unified payload for a single API call, replacing the fan-out of many
    separate dashboard requests.

    The shared paper-fund dataset (state, snapshots, orders, risk decisions,
    learning, activity) is loaded exactly once and injected into every analytics
    engine, so the snapshots, orders, learning, activity, and risk-decision
    tables are never read more than once per report. NOT_EVALUATED results from
    child engines are preserved verbatim and missing values are never
    fabricated. Every collaborator is injectable for deterministic offline
    tests, each section degrades to ``Unavailable`` instead of raising, and the
    engine never writes to the database, changes recommendations, portfolios,
    the scheduler, the paper fund, or connects a broker.
    """

    VERSION = "dashboard-v2"
    DEFAULT_LIMIT = 200

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def report(
        self,
        operations=None,
        reliability=None,
        fund=None,
        portfolio_engine=None,
        performance_engine=None,
        scenarios_engine=None,
        correlation_engine=None,
        learning_engine=None,
        paper_fund_data=None,
        loaders=None,
        risk_limits=None,
        risk_decisions=None,
        now=None,
        limit=None,
    ):
        moment = self._moment(now)
        limit = limit or self.DEFAULT_LIMIT

        # Load the shared paper-fund dataset EXACTLY ONCE, then inject it into
        # every analytics engine below so no list table is read twice.
        shared = self._fetch(
            lambda: self._load_shared(paper_fund_data, loaders, limit)
        )
        shared_data = shared["value"] if shared["ok"] else self._empty_shared()

        operations_section = self._safe(
            lambda: self._operations_report(operations)
        )
        reliability_section = self._safe(
            lambda: self._reliability_report(reliability)
        )
        paper_fund_section = self._safe(lambda: self._fund_status(fund))

        portfolio_section = self._safe(
            lambda: self._portfolio(portfolio_engine, shared_data, limit)
        )
        performance_section = self._safe(
            lambda: self._performance(performance_engine, shared_data, limit)
        )
        scenarios_section = self._safe(
            lambda: self._scenarios(scenarios_engine, shared_data, limit)
        )
        correlation_section = self._safe(
            lambda: self._correlation(correlation_engine, shared_data, limit)
        )
        learning_section = self._safe(
            lambda: self._learning(learning_engine, shared_data, limit)
        )
        risk_section = self._safe(
            lambda: self._risk(risk_limits, risk_decisions, shared_data)
        )

        market_section = self._derived_section(
            operations_section, "market_data"
        )
        scheduler_section = self._derived_section(
            operations_section, "scheduler"
        )
        research_cycle_section = self._safe(
            lambda: self._research_cycle(shared_data)
        )

        return {
            "generated_at": moment.isoformat(),
            "version": self.VERSION,
            "operations": operations_section,
            "reliability": reliability_section,
            "paper_fund": paper_fund_section,
            "portfolio": portfolio_section,
            "performance": performance_section,
            "scenarios": scenarios_section,
            "correlation": correlation_section,
            "learning": learning_section,
            "risk": risk_section,
            "market": market_section,
            "scheduler": scheduler_section,
            "research_cycle": research_cycle_section,
            "notifications": [],
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Shared paper-fund dataset (loaded once)
    # ------------------------------------------------------------------
    def _load_shared(self, paper_fund_data, loaders, limit):
        if paper_fund_data is not None:
            return {**self._empty_shared(), **paper_fund_data}

        getters = self._resolve_loaders(loaders)
        return {
            "state": getters["state"](),
            "snapshots": getters["snapshots"](limit),
            "orders": getters["orders"](limit),
            "risk_decisions": getters["risk_decisions"](limit),
            "learning": getters["learning"](limit),
            "activity": getters["activity"](limit),
        }

    def _resolve_loaders(self, loaders):
        if loaders:
            return loaders
        from database.repository import (
            get_latest_paper_fund_state,
            get_paper_fund_activity,
            get_paper_fund_learning,
            get_paper_fund_orders,
            get_paper_fund_snapshots,
            get_recent_risk_decisions,
        )

        return {
            "state": get_latest_paper_fund_state,
            "snapshots": get_paper_fund_snapshots,
            "orders": get_paper_fund_orders,
            "risk_decisions": get_recent_risk_decisions,
            "learning": get_paper_fund_learning,
            "activity": get_paper_fund_activity,
        }

    def _empty_shared(self):
        return {
            "state": None,
            "snapshots": [],
            "orders": [],
            "risk_decisions": [],
            "learning": [],
            "activity": [],
        }

    # ------------------------------------------------------------------
    # Section builders (compose only; no new analytics)
    # ------------------------------------------------------------------
    def _operations_report(self, operations):
        if operations is None:
            from engines.operations_engine import OperationsEngine

            return OperationsEngine().report()
        if isinstance(operations, dict):
            return operations
        return operations.report()

    def _reliability_report(self, reliability):
        if reliability is None:
            from engines.reliability_engine import ReliabilityEngine

            return ReliabilityEngine().report()
        if isinstance(reliability, dict):
            return reliability
        return reliability.report()

    def _fund_status(self, fund):
        if fund is None:
            from engines.live_paper_fund_engine import LivePaperFundEngine

            return LivePaperFundEngine().status()
        if isinstance(fund, dict):
            return fund
        return fund.status()

    def _portfolio(self, engine, shared, limit):
        engine = engine or self._default_engine("portfolio_intelligence_engine",
                                                 "PortfolioIntelligenceEngine")
        return engine.generate(
            state=shared["state"],
            snapshots=shared["snapshots"],
            risk_decisions=shared["risk_decisions"],
            learning=shared["learning"],
            activity=shared["activity"],
            limit=limit,
        )

    def _performance(self, engine, shared, limit):
        engine = engine or self._default_engine("performance_attribution_engine",
                                                 "PerformanceAttributionEngine")
        return engine.generate(
            state=shared["state"],
            snapshots=shared["snapshots"],
            orders=shared["orders"],
            risk_decisions=shared["risk_decisions"],
            learning=shared["learning"],
            activity=shared["activity"],
            limit=limit,
        )

    def _scenarios(self, engine, shared, limit):
        engine = engine or self._default_engine("scenario_analysis_engine",
                                                 "ScenarioAnalysisEngine")
        return engine.generate(
            state=shared["state"],
            snapshots=shared["snapshots"],
            orders=shared["orders"],
            risk_decisions=shared["risk_decisions"],
            learning=shared["learning"],
            activity=shared["activity"],
            limit=limit,
        )

    def _correlation(self, engine, shared, limit):
        engine = engine or self._default_engine("correlation_engine",
                                                 "CorrelationEngine")
        return engine.generate(
            state=shared["state"],
            snapshots=shared["snapshots"],
            limit=limit,
        )

    def _learning(self, engine, shared, limit):
        engine = engine or self._default_engine("self_learning_analytics_engine",
                                                 "SelfLearningAnalyticsEngine")
        return engine.generate(
            learning=shared["learning"],
            orders=shared["orders"],
            snapshots=shared["snapshots"],
            risk_decisions=shared["risk_decisions"],
            limit=limit,
        )

    def _risk(self, risk_limits, risk_decisions, shared):
        from engines.risk_management_engine import RiskManagementEngine

        limits = risk_limits if risk_limits is not None else dict(
            RiskManagementEngine.DEFAULT_LIMITS
        )
        # Reuse the risk decisions already loaded in the shared dataset so the
        # risk-decisions table is never read a second time.
        decisions = (
            risk_decisions if risk_decisions is not None else shared["risk_decisions"]
        )
        return {
            "limits": limits,
            "decisions": decisions,
            "count": len(decisions),
            "read_only": True,
            **RiskManagementEngine.SAFETY_FIELDS,
        }

    def _research_cycle(self, shared):
        """Autonomous research cycle view, composed from recorded activity.

        Projects the newest RECOMMENDATIONS_GENERATED and COMMITTEE_EVALUATED
        activity entries (written by ResearchCycleEngine only when those
        stages actually did work) into per-stage status, timestamp, and
        duration, alongside the current AUTO_RESEARCH gates. NOT_EVALUATED
        with a reason when no autonomous research has ever been recorded —
        nothing is fabricated.
        """
        from core import settings

        activity = shared.get("activity") or []
        generated = next(
            (
                entry for entry in activity
                if entry.get("activity_type") == "RECOMMENDATIONS_GENERATED"
            ),
            None,
        )
        committee = next(
            (
                entry for entry in activity
                if entry.get("activity_type") == "COMMITTEE_EVALUATED"
            ),
            None,
        )

        def stage(name, entry, missing_reason):
            if entry is None:
                return {
                    "stage": name,
                    "status": "NOT_EVALUATED",
                    "reason": missing_reason,
                    "at": None,
                    "duration_seconds": None,
                    "details": {},
                }
            details = entry.get("details") or {}
            return {
                "stage": name,
                "status": "COMPLETED",
                "reason": None,
                "at": entry.get("at"),
                "duration_seconds": details.get("duration_seconds"),
                "details": details,
                "message": entry.get("message"),
            }

        stages = [
            stage(
                "research_generation",
                generated,
                "No autonomous recommendation generation has been recorded.",
            ),
            stage(
                "committee_evaluation",
                committee,
                "No autonomous committee evaluation has been recorded.",
            ),
        ]
        evaluated = generated is not None or committee is not None

        # Tiny read-only due-ness snapshot from the research orchestrator
        # (settings + newest atlas_runs timestamp); degrades to None fields.
        try:
            from engines.research_cycle_engine import ResearchCycleEngine

            runtime = ResearchCycleEngine().status()
        except Exception:
            runtime = {}

        return {
            "status": "EVALUATED" if evaluated else "NOT_EVALUATED",
            "reason": None if evaluated else (
                "No autonomous research cycle has recorded activity yet. "
                "Enable AUTO_RESEARCH_ENABLED with a real market data "
                "provider, or trigger POST /recommendations/generate."
            ),
            "enabled": bool(getattr(settings, "AUTO_RESEARCH_ENABLED", False)),
            "interval_minutes": int(
                getattr(settings, "AUTO_RESEARCH_INTERVAL_MINUTES", 1440)
            ),
            "research_due": runtime.get("research_due"),
            "last_recommendation_run_time": runtime.get(
                "last_recommendation_run_time"
            ),
            "stages": stages,
        }

    def _derived_section(self, operations_section, name):
        # Project the market/scheduler view from the already-composed operations
        # report instead of re-calling MarketDataManager or the scheduler.
        if isinstance(operations_section, dict):
            section = operations_section.get(name)
            if isinstance(section, dict):
                return section
        return {
            "status": "NOT_EVALUATED",
            "reason": (
                f"The {name} view is unavailable because the operations report "
                "could not be composed."
            ),
        }

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _default_engine(self, module_name, class_name):
        module = __import__(f"engines.{module_name}", fromlist=[class_name])
        return getattr(module, class_name)()

    def _safe(self, producer):
        try:
            return producer()
        except Exception as error:  # never propagate a section failure
            return {"status": "Unavailable", "reason": str(error)}

    def _fetch(self, producer):
        try:
            return {"ok": True, "value": producer()}
        except Exception as error:
            return {"ok": False, "error": str(error)}

    def _moment(self, now):
        if isinstance(now, datetime):
            return now
        if now:
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(str(now)[:len(fmt) + 2].strip(), fmt)
                except ValueError:
                    continue
            try:
                return datetime.fromisoformat(str(now))
            except ValueError:
                pass
        return datetime.now()

    def policy(self):
        return {
            "read_only": True,
            "deterministic": True,
            "composition_only": True,
            "writes": False,
            "broker_integration": False,
            "real_money": False,
            "modifies_scheduler": False,
            "modifies_recommendations": False,
            "modifies_portfolio": False,
            "modifies_paper_fund": False,
        }
