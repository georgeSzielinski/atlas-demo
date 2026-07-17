"""Deterministic, paper-only recommendation outcome evaluation."""

import math
import threading
from datetime import datetime

from engines.validation_engine import ValidationEngine


_OUTCOME_LOCK = threading.Lock()


class OutcomeEvaluationEngine:
    """Evaluate due recommendation evidence without changing trading behavior."""

    EVALUATION_SOURCE = "paper"
    MAX_PRICE_AGE_SECONDS = 300
    CYCLE_IN_PROGRESS_REASON = "another outcome evaluation is already running"
    UNSAFE_PROVIDERS = {"", "mock", "test", "unknown"}

    def run_due_cycle(self, **kwargs):
        settings_module = kwargs.pop("settings_module", None) or self._settings()
        if not bool(getattr(settings_module, "AUTO_OUTCOME_ENABLED", False)):
            return self._empty_summary(
                self._moment(kwargs.get("now")),
                status="SKIPPED",
                reason="automatic outcome evaluation is disabled",
            )
        return self.evaluate(**kwargs)

    def evaluate(
        self,
        manager=None,
        now=None,
        candidate_loader=None,
        result_writer=None,
        activity_writer=None,
        validation_engine=None,
        clock=None,
    ):
        moment = self._moment(now)
        started = (clock or datetime.now)()
        if not _OUTCOME_LOCK.acquire(blocking=False):
            return self._empty_summary(
                moment, status="SKIPPED", reason=self.CYCLE_IN_PROGRESS_REASON
            )

        try:
            validator = validation_engine or ValidationEngine()
            horizons = list(validator.VALIDATION_WINDOWS)
            loader = candidate_loader or self._pending
            writer = result_writer or self._save_result
            market = manager or self._manager()
            candidates = loader(moment, horizons, self.EVALUATION_SOURCE)
            provider = getattr(market, "provider_name", None)
            summary = self._empty_summary(moment, provider=provider)

            if not candidates:
                summary["status"] = "SKIPPED"
                summary["reason"] = "no outcome evaluations are due"
                return self._finish(summary, started, clock, activity_writer)

            tickers = sorted({str(item.get("ticker") or "").upper() for item in candidates if item.get("ticker")})
            try:
                price_report = market.latest_prices(tickers, use_cache=True)
            except Exception as error:
                price_report = {"results": {}, "requested_provider": provider}
                summary["errors"].append(f"price batch failed: {type(error).__name__}: {error}")

            summary["provider"] = price_report.get("requested_provider") or provider
            results = price_report.get("results") or {}
            for candidate in candidates:
                try:
                    price_result = results.get(str(candidate.get("ticker") or "").upper())
                    unsafe_reason = self._unsafe_entry_reason(candidate)
                    unsafe_reason = unsafe_reason or self._unsafe_price_reason(
                        price_result, price_report, moment
                    )
                    if unsafe_reason:
                        write = writer(self._deferred_result(candidate, price_result, moment, unsafe_reason))
                        if write.get("action") == "skipped_completed":
                            summary["skipped_completed"] += 1
                        else:
                            summary["deferred"] += 1
                    else:
                        outcome = validator.evaluate_completed_recommendation(
                            recommendation={
                                "id": candidate["recommendation_id"],
                                "ticker": candidate["ticker"],
                                "action": candidate["action"],
                            },
                            starting_price=candidate["entry_price"],
                            ending_price=float(price_result["price"]),
                            holding_period=candidate["horizon_days"],
                            recommendation_timestamp=candidate["entry_at"],
                            evaluation_timestamp=moment.isoformat(),
                            notes="Deterministic paper outcome evaluation.",
                        )
                        outcome.update(self._lineage(candidate, price_result))
                        write = writer(outcome)
                        if write.get("action") == "skipped_completed":
                            summary["skipped_completed"] += 1
                        elif outcome["status"] == validator.SUCCEEDED:
                            summary["evaluated"] += 1
                            summary["succeeded"] += 1
                        else:
                            summary["evaluated"] += 1
                            summary["failed"] += 1
                except Exception as error:
                    summary["errors"].append(
                        f"recommendation {candidate.get('recommendation_id')} horizon "
                        f"{candidate.get('horizon_days')}: {type(error).__name__}: {error}"
                    )

            summary["status"] = "COMPLETED" if not summary["errors"] else "PARTIAL"
            return self._finish(summary, started, clock, activity_writer)
        finally:
            _OUTCOME_LOCK.release()

    def status(self, now=None, settings_module=None, candidate_loader=None, deferred_counter=None, activity_loader=None):
        moment = self._moment(now)
        settings_module = settings_module or self._settings()
        validator = ValidationEngine()
        status_errors = []
        try:
            pending = (candidate_loader or self._pending)(
                moment, validator.VALIDATION_WINDOWS, self.EVALUATION_SOURCE
            )
        except Exception as error:
            pending = []
            status_errors.append(f"pending read failed: {type(error).__name__}: {error}")
        try:
            deferred_count = (deferred_counter or self._deferred_count)()
        except Exception as error:
            deferred_count = 0
            status_errors.append(f"outcome read failed: {type(error).__name__}: {error}")
        try:
            last_run = (activity_loader or self._latest_activity)()
        except Exception as error:
            last_run = None
            status_errors.append(f"activity read failed: {type(error).__name__}: {error}")
        details = (last_run or {}).get("details") or {}
        errors = details.get("errors") or []
        status = {
            "enabled": bool(getattr(settings_module, "AUTO_OUTCOME_ENABLED", False)),
            "last_run": last_run,
            "pending_count": len(pending),
            "deferred_count": deferred_count,
            "most_recent_error": errors[-1] if errors else (status_errors[-1] if status_errors else None),
            "provider": details.get("provider") or self._manager().provider_name,
            "status": "Unavailable" if status_errors else "EVALUATED",
            "policy": self.policy(),
        }
        status.update({
            "pending": status["pending_count"],
            "evaluated": details.get("evaluated", 0),
            "deferred": status["deferred_count"],
            "last_error": status["most_recent_error"],
            "deterministic": True,
            "paper_only": True,
            "does_not_place_orders": True,
        })
        return status

    def _unsafe_entry_reason(self, candidate):
        price = candidate.get("entry_price")
        if (
            isinstance(price, bool)
            or not isinstance(price, (int, float))
            or not math.isfinite(price)
            or price <= 0
        ):
            return "stored entry price must be positive and finite"
        if candidate.get("entry_validated") not in (True, 1):
            return "stored entry price is not validated"
        provider = str(candidate.get("entry_price_source") or "").strip().lower()
        if provider in self.UNSAFE_PROVIDERS or any(
            token in provider for token in ("mock", "test", "unknown")
        ):
            return f"unsafe entry price provider: {provider or 'unset'}"
        return None

    def _unsafe_price_reason(self, result, report, moment):
        if not isinstance(result, dict):
            return "current price unavailable"
        provider = str(result.get("provider") or "").strip().lower()
        if provider in self.UNSAFE_PROVIDERS or any(token in provider for token in ("mock", "test", "unknown")):
            return f"unsafe price provider: {provider or 'unset'}"
        if result.get("fallback_used") is not False or report.get("fallback_used") is True:
            return "fallback price refused"
        if result.get("validated") is not True:
            return "price failed validation"
        if report.get("validated") is False:
            return "price batch failed validation"
        price = result.get("price")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            return "price must be positive and finite"
        cache_age = result.get("cache_age")
        if cache_age is not None:
            try:
                if float(cache_age) > self.MAX_PRICE_AGE_SECONDS:
                    return "price is stale"
            except (TypeError, ValueError):
                return "price freshness is invalid"
        as_of = self._parse_time(report.get("as_of"))
        if as_of is not None:
            try:
                age = moment.timestamp() - as_of.timestamp()
            except (OSError, ValueError):
                return "price timestamp is invalid"
            if age > self.MAX_PRICE_AGE_SECONDS:
                return "price is stale"
        return None

    def _deferred_result(self, candidate, price_result, moment, reason):
        result = price_result or {}
        return {
            "recommendation_id": candidate.get("recommendation_id"),
            "ticker": candidate.get("ticker"),
            "recommendation": candidate.get("action"),
            "recommendation_timestamp": candidate.get("entry_at"),
            "evaluation_timestamp": moment.isoformat(),
            "holding_period": candidate.get("horizon_days"),
            "starting_price": candidate.get("entry_price"),
            "ending_price": None,
            "status": "Deferred",
            "notes": reason,
            "deferred_reason": reason,
            **self._lineage(candidate, result),
        }

    def _lineage(self, candidate, price_result):
        return {
            "horizon_days": candidate.get("horizon_days"),
            "entry_price_source": candidate.get("entry_price_source"),
            "entry_validated": candidate.get("entry_validated"),
            "eval_price_source": price_result.get("provider"),
            "eval_validated": price_result.get("validated"),
            "eval_fallback_used": price_result.get("fallback_used"),
            "evaluation_source": self.EVALUATION_SOURCE,
            "schema_version": 1,
        }

    def _finish(self, summary, started, clock, activity_writer):
        completed = (clock or datetime.now)()
        summary["duration_seconds"] = round(max(0.0, (completed - started).total_seconds()), 3)
        summary["completed_at"] = completed.isoformat()
        writer = activity_writer or self._save_activity
        try:
            writer({
                "at": summary["completed_at"],
                "cycle_id": None,
                "activity_type": "OUTCOME_EVALUATION",
                "message": f"Outcome evaluation {summary['status'].lower()}.",
                "details": dict(summary),
            })
        except Exception as error:
            summary["errors"].append(
                f"activity persistence failed: {type(error).__name__}: {error}"
            )
            summary["status"] = "PARTIAL"
        return summary

    def _empty_summary(self, moment, status="NOT_EVALUATED", reason=None, provider=None):
        return {
            "status": status,
            "reason": reason,
            "started_at": moment.isoformat(),
            "completed_at": None,
            "evaluated": 0,
            "succeeded": 0,
            "failed": 0,
            "deferred": 0,
            "skipped_completed": 0,
            "errors": [],
            "duration_seconds": 0.0,
            "provider": provider,
            "policy": self.policy(),
        }

    def policy(self):
        return {
            "deterministic": True,
            "paper_only": True,
            "read_write_scope": "recommendation outcome evidence only",
            "does_not_place_orders": True,
            "does_not_change_recommendations": True,
            "broker_integration": False,
            "market_open_required": False,
        }

    def _moment(self, value):
        return value if isinstance(value, datetime) else self._parse_time(value) or datetime.now()

    def _parse_time(self, value):
        if value is None:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    def _pending(self, now, horizons, source):
        from database.repository import get_pending_evaluations
        return get_pending_evaluations(now, horizons, source)

    def _save_result(self, result):
        from database.repository import save_validation_result
        return save_validation_result(result, update_recommendation_status=False)

    def _save_activity(self, entry):
        from database.repository import add_paper_fund_activity
        return add_paper_fund_activity(entry)

    def _deferred_count(self):
        from database.repository import count_outcomes
        return count_outcomes(status="Deferred", evaluation_source=self.EVALUATION_SOURCE)

    def _latest_activity(self):
        from database.repository import get_latest_paper_fund_activity
        return get_latest_paper_fund_activity("OUTCOME_EVALUATION")

    def _manager(self):
        from market.market_data_manager import MarketDataManager
        return MarketDataManager()

    def _settings(self):
        from core import settings
        return settings
