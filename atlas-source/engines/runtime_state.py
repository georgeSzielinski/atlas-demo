import hashlib
import json
from datetime import datetime


class RuntimeState:
    STATES = [
        "INITIALIZING",
        "PRE_MARKET",
        "MARKET_OPEN",
        "MARKET_CLOSE",
        "POST_MARKET",
        "IDLE",
        "ERROR",
    ]

    @classmethod
    def build(
        cls,
        current_state,
        market_date,
        market_phase,
        last_cycle_time,
        next_cycle,
        provider_health,
        paper_portfolio_value,
        active_watchlist_size,
        open_positions,
        recommendations_today,
        alerts,
        tasks,
        operations_summary,
    ):
        if current_state not in cls.STATES:
            raise ValueError(f"Unsupported runtime state: {current_state}")

        health = cls.health(
            current_state,
            provider_health,
            alerts,
            paper_portfolio_value,
        )

        return {
            "runtime_id": cls.runtime_id(market_date, current_state),
            "current_state": current_state,
            "market_date": market_date,
            "market_phase": market_phase,
            "last_cycle_time": last_cycle_time,
            "next_cycle": next_cycle,
            "provider_health": provider_health,
            "paper_portfolio_value": paper_portfolio_value,
            "active_watchlist_size": active_watchlist_size,
            "open_positions": open_positions,
            "recommendations_today": recommendations_today,
            "alerts": alerts,
            "tasks": tasks,
            "operations_summary": operations_summary,
            "health": health,
            "policy": cls.policy(),
        }

    @classmethod
    def health(cls, current_state, provider_health, alerts, paper_value):
        if current_state == "ERROR":
            return {
                "status": "Offline",
                "explanation": "Runtime entered ERROR state.",
            }

        provider_ok = provider_health.get("healthy")
        if provider_ok is False:
            return {
                "status": "Degraded",
                "explanation": "Provider health check failed.",
            }

        warning_alerts = [
            alert for alert in alerts
            if "warning" in alert.lower()
            or "risk" in alert.lower()
            or "drawdown" in alert.lower()
        ]
        if warning_alerts:
            return {
                "status": "Warning",
                "explanation": warning_alerts[0],
            }

        if paper_value is None:
            return {
                "status": "Warning",
                "explanation": "Paper portfolio value is unavailable.",
            }

        return {
            "status": "Healthy",
            "explanation": "Runtime is paper-only and operating normally.",
        }

    @classmethod
    def runtime_id(cls, market_date, current_state):
        seed = json.dumps(
            {
                "market_date": market_date,
                "current_state": current_state,
            },
            sort_keys=True,
        )
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]

        return f"runtime-{digest}"

    @classmethod
    def policy(cls):
        return {
            "paper_only": True,
            "broker_integration": False,
            "real_money": False,
            "automatic_execution": False,
            "changes_recommendation_behavior": False,
            "human_approval_required_for_real_trading": True,
        }


def utc_now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat()
