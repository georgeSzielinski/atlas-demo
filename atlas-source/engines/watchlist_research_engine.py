import inspect
import math
from datetime import datetime


class WatchlistResearchEngine:
    """Explicit, deterministic watchlist research runs.

    Runs the EXISTING deterministic recommendation pipeline (MarketEngine ->
    RecommendationEngine, both unchanged and LLM-free) over the live paper
    fund's watchlist and persists ordinary atlas_runs + recommendations rows,
    so /committee/evaluate/{ticker}, /strategies/compare, and Strategy Lab
    operate on real stored records.

    Ticker resolution: an explicit list overrides everything; otherwise the
    current paper-fund watchlist; otherwise APPROVED_TICKERS.

    Safety: generation is manual-only (no scheduler hook), gated on a real
    market data provider — mock/test/unknown providers are REFUSED and nothing
    is written. Tickers whose market analysis fails are skipped with recorded
    reasons, never emitted as fabricated recommendations. This engine never
    touches the live paper fund, portfolio construction, risk management, or
    any execution path, and unlike the full IntelligencePipeline it saves no
    demo portfolio snapshot and exports no report.
    """

    VERSION = "watchlist-research-v1"

    # Providers that must never back persisted research records.
    UNSAFE_PROVIDERS = {"mock", "unknown", "test", ""}

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def generate(
        self,
        tickers=None,
        market_engine=None,
        recommendation_engine=None,
        dashboard_engine=None,
        provider_resolver=None,
        state_loader=None,
        approved_tickers=None,
        savers=None,
        now=None,
        learning_context_loader=None,
    ):
        moment = self._moment(now)

        provider = self._provider(provider_resolver)
        if not self._provider_is_real(provider):
            return self._refused(
                moment,
                provider,
                (
                    f"Market data provider '{provider or 'unset'}' is not a real "
                    "provider; research records are never generated from "
                    "mock/test/unknown data. Set MARKET_DATA_PROVIDER=yahoo "
                    "and try again."
                ),
            )

        resolved, source = self._resolve_tickers(
            tickers, state_loader, approved_tickers
        )
        if not resolved:
            return self._not_evaluated(
                moment,
                provider,
                source,
                (
                    "No tickers to analyze: no explicit list was provided, the "
                    "paper-fund watchlist is unavailable or empty, and no "
                    "approved tickers are configured."
                ),
            )

        engine = market_engine or self._default_market_engine()
        stocks = engine.analyze_market(resolved)
        analyzed = {str(stock.ticker).upper() for stock in stocks}
        skipped = [
            {
                "ticker": ticker,
                "reason": (
                    "Market analysis unavailable: no or insufficient price "
                    "history from the provider."
                ),
            }
            for ticker in resolved
            if ticker not in analyzed
        ]

        if not stocks:
            return self._not_evaluated(
                moment,
                provider,
                source,
                (
                    "No requested ticker could be analyzed with the available "
                    "market data; nothing was persisted."
                ),
                tickers_requested=resolved,
                skipped=skipped,
            )

        recommender = recommendation_engine or self._default_recommendation_engine()
        recommendations = recommender.build_recommendations(stocks)

        run_id, recommendation_ids = self._persist(
            stocks, recommendations, dashboard_engine, savers, provider, moment
        )

        return {
            "generated_at": moment.isoformat(),
            "version": self.VERSION,
            "status": "COMPLETED",
            "reason": None,
            # Advisory evidence from the closed learning loop, attached AFTER
            # the recommendation records were built and persisted: it can
            # never change an action, score, or stored row. Research context
            # only.
            "learning_context": self._learning_context(learning_context_loader),
            "run_id": run_id,
            "recommendation_ids": recommendation_ids,
            "provider": provider,
            "ticker_source": source,
            "tickers_requested": resolved,
            "tickers_analyzed": sorted(analyzed),
            "skipped": skipped,
            "recommendation_count": len(recommendations),
            "recommendations": [
                {
                    "ticker": recommendation.ticker,
                    "action": recommendation.action,
                    "confidence": recommendation.confidence,
                }
                for recommendation in recommendations
            ],
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Ticker resolution
    # ------------------------------------------------------------------
    def _resolve_tickers(self, tickers, state_loader, approved_tickers):
        explicit = self._clean_tickers(tickers)
        if explicit:
            return explicit, "explicit"

        state = self._fetch(state_loader or self._default_state_loader)
        watchlist = self._clean_tickers((state or {}).get("watchlist"))
        if watchlist and (state or {}).get("fund_status") != "OFF":
            return watchlist, "paper_fund_watchlist"

        if approved_tickers is None:
            approved_tickers = self._fetch(self._default_approved_tickers) or []
        approved = self._clean_tickers(approved_tickers)
        if approved:
            return approved, "approved_tickers"

        return [], "none"

    def _clean_tickers(self, tickers):
        if not tickers:
            return []
        return sorted({
            str(ticker).strip().upper()
            for ticker in tickers
            if str(ticker).strip()
        })

    # ------------------------------------------------------------------
    # Provider gate
    # ------------------------------------------------------------------
    def _provider(self, provider_resolver):
        if provider_resolver is not None:
            return provider_resolver()

        import os

        from core.settings import DATA_PROVIDER

        return os.environ.get("MARKET_DATA_PROVIDER") or DATA_PROVIDER

    def _provider_is_real(self, provider):
        name = str(provider or "").strip().lower()
        if name in self.UNSAFE_PROVIDERS:
            return False
        return not any(token in name for token in ("mock", "test", "unknown"))

    # ------------------------------------------------------------------
    # Persistence (ordinary run + recommendation rows; nothing else)
    # ------------------------------------------------------------------
    def _persist(self, stocks, recommendations, dashboard_engine, savers, provider=None, moment=None):
        builder = dashboard_engine or self._default_dashboard_engine()
        dashboard = builder.build_dashboard(
            stocks=stocks, recommendations=recommendations
        )

        if savers is None:
            from database.repository import (
                save_dashboard_run,
                save_recommendations,
            )

            savers = {
                "run": save_dashboard_run,
                "recommendations": save_recommendations,
            }

        run_id = savers["run"](dashboard)
        # Entry context is passed THROUGH the saver so injected/mock savers (which
        # never persist) simply ignore it — nothing else touches the database.
        entry_contexts = self._entry_contexts(stocks, provider, moment)
        recommendation_saver = savers["recommendations"]
        if self._accepts_entry_contexts(recommendation_saver):
            recommendation_ids = recommendation_saver(
                run_id, recommendations, entry_contexts=entry_contexts
            )
        else:
            recommendation_ids = recommendation_saver(run_id, recommendations)
        return run_id, recommendation_ids

    def _accepts_entry_contexts(self, saver):
        """Whether an injected saver supports the additive keyword argument."""
        try:
            parameters = inspect.signature(saver).parameters.values()
        except (TypeError, ValueError):
            return False
        return any(
            (
                parameter.name == "entry_contexts"
                and parameter.kind
                in (
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                )
            )
            or parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in parameters
        )

    def _entry_contexts(self, stocks, provider, moment):
        """Build per-ticker entry context from the prices the cycle ALREADY holds.

        No second market fetch: StockAnalysis.price, the price used to build the
        recommendation, is the outcome baseline. The cycle gate establishes an
        accepted real provider plus a positive finite analyzed price, but exposes
        no per-price fallback flag; that unsupported lineage stays null. A usable
        price becomes OBSERVED/PENDING, while a missing or invalid price becomes
        DEFERRED with null price lineage. Regime/sector/horizon also stay null
        because this cycle computes none of them.
        """
        observed_at = moment.isoformat() if moment is not None else None
        contexts = {}
        for stock in stocks or []:
            ticker = str(getattr(stock, "ticker", "") or "").upper()
            if not ticker:
                continue
            price = getattr(stock, "price", None)
            observed = (
                isinstance(price, (int, float))
                and not isinstance(price, bool)
                and math.isfinite(price)
                and price > 0
            )
            if observed:
                contexts[ticker] = {
                    "created_at": observed_at,
                    "entry_at": observed_at,
                    "entry_price": float(price),
                    "entry_price_source": provider,
                    "entry_validated": True,
                    # The research analyzer exposes no per-price fallback flag.
                    "entry_fallback_used": None,
                    "entry_status": "OBSERVED",
                    "market_regime": None,
                    "sector": None,
                    "expected_horizon_days": None,
                    "outcome_state": "PENDING",
                    "outcome_schema_version": 1,
                }
            else:
                contexts[ticker] = {
                    "created_at": observed_at,
                    "entry_at": None,
                    "entry_price": None,
                    "entry_price_source": None,
                    "entry_validated": None,
                    "entry_fallback_used": None,
                    "entry_status": "DEFERRED",
                    "market_regime": None,
                    "sector": None,
                    "expected_horizon_days": None,
                    "outcome_state": "DEFERRED",
                    "outcome_schema_version": 1,
                }
        return contexts

    # ------------------------------------------------------------------
    # Refusal / degradation results (nothing written)
    # ------------------------------------------------------------------
    def _refused(self, moment, provider, reason):
        return {
            "generated_at": moment.isoformat(),
            "version": self.VERSION,
            "status": "REFUSED",
            "reason": reason,
            "run_id": None,
            "provider": provider,
            "ticker_source": None,
            "tickers_requested": [],
            "tickers_analyzed": [],
            "skipped": [],
            "recommendation_count": 0,
            "recommendations": [],
            "policy": self.policy(),
        }

    def _not_evaluated(
        self,
        moment,
        provider,
        source,
        reason,
        tickers_requested=None,
        skipped=None,
    ):
        return {
            "generated_at": moment.isoformat(),
            "version": self.VERSION,
            "status": "NOT_EVALUATED",
            "reason": reason,
            "run_id": None,
            "provider": provider,
            "ticker_source": source,
            "tickers_requested": tickers_requested or [],
            "tickers_analyzed": [],
            "skipped": skipped or [],
            "recommendation_count": 0,
            "recommendations": [],
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Defaults (lazy imports; every collaborator injectable)
    # ------------------------------------------------------------------
    def _default_market_engine(self):
        from engines.market_engine import MarketEngine

        return MarketEngine()

    def _default_recommendation_engine(self):
        from engines.recommendation_engine import RecommendationEngine

        return RecommendationEngine()

    def _default_dashboard_engine(self):
        from engines.dashboard_engine import DashboardEngine

        return DashboardEngine()

    def _default_state_loader(self):
        from database.repository import get_latest_paper_fund_state

        return get_latest_paper_fund_state()

    def _default_approved_tickers(self):
        from core.settings import APPROVED_TICKERS

        return APPROVED_TICKERS

    # ------------------------------------------------------------------
    # Advisory learning context (research evidence only)
    # ------------------------------------------------------------------
    def _learning_context(self, loader):
        """Latest persisted learning evidence, attached as research context.

        Composes the newest stored Self-Improvement findings and the most
        recent paper-fund lessons. Strictly advisory: it is read AFTER
        recommendations are built and persisted, so it cannot influence any
        action, score, threshold, or stored record. Best-effort — missing
        evidence yields None, never an error.
        """
        try:
            if loader is not None:
                return loader()

            from database.repository import (
                get_latest_self_improvement_report,
                get_paper_fund_learning,
            )

            report = get_latest_self_improvement_report()
            lessons = get_paper_fund_learning(limit=5)
            if not report and not lessons:
                return None

            return {
                "advisory_only": True,
                "self_improvement": {
                    "generated_at": report.get("generated_at"),
                    "status": report.get("status"),
                    "headline": report.get("headline"),
                    "opportunities": report.get("opportunities", [])[:5],
                } if report else None,
                "recent_lessons": [
                    {"at": lesson.get("at"), "lesson": lesson.get("lesson")}
                    for lesson in lessons
                ],
            }
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Utilities & policy
    # ------------------------------------------------------------------
    def _fetch(self, producer):
        try:
            return producer()
        except Exception:
            return None

    def _moment(self, now):
        if isinstance(now, datetime):
            return now
        if now:
            try:
                return datetime.fromisoformat(str(now))
            except ValueError:
                pass
        return datetime.now()

    def policy(self):
        return {
            "deterministic": True,
            "llm_decisions": False,
            "manual_only": True,
            "paper_only": True,
            "real_money": False,
            "broker_integration": False,
            "writes_recommendations_only": True,
            "modifies_live_paper_fund": False,
            "modifies_portfolio_construction": False,
            "modifies_risk_management": False,
            "modifies_trading_execution": False,
            "requires_real_provider": True,
        }
