"""Read-only readiness preflight for opt-in live paper mode.

Run:

    venv/bin/python -m backend.live_paper_preflight

Reports GO / NO-GO for enabling the automatic Live Paper Fund with a real market
data provider. It is strictly read-only: it never calls setup_database, never
runs a tick or cycle, never writes to the database, and never creates a
simulated order. It only reads config flags, probes provider health in memory,
reads the calendar-based market status, and reads the current fund state.

Because Atlas is disabled by default, the expected default verdict is NO-GO.

Enabling real (still paper-only) trading later
----------------------------------------------
1. Pick a real provider:   export MARKET_DATA_PROVIDER=yahoo   (mock is rejected)
2. Start the fund:         POST /paper-fund/start {"watchlist": [...]}  -> READY
3. Enable the gates:       export AUTO_FUND_ENABLED=true
                           export ATLAS_SCHEDULER_ENABLED=true
4. Launch the API:         venv/bin/python -m backend.run_api
5. Verify:                 GET /paper-fund/preflight  (until verdict is GO)

Even when GO, execution stays simulated only: fills are virtual, the broker is
disabled, real_money is always false, and bad/fallback prices fail the cycle
loudly into ERROR instead of trading. A human decision is required before any
real broker execution is ever added.
"""

import sys


def _is_real_provider(name):
    from engines.live_paper_fund_engine import LivePaperFundEngine

    if not name:
        return False
    normalized = str(name).strip().lower()
    if normalized in LivePaperFundEngine.UNSAFE_AUTO_PROVIDERS:
        return False

    return not any(token in normalized for token in ("mock", "test", "unknown"))


def _read_fund_state():
    # Read-only: never calls setup_database. On a fresh database the table may
    # not exist yet; treat that as "no fund" rather than creating anything.
    from database.repository import get_latest_paper_fund_state

    try:
        return get_latest_paper_fund_state(), None
    except Exception as error:
        return None, str(error)


def build_preflight_report(manager=None, engine=None, fund_state_reader=None):
    """Compose the read-only readiness report. No writes, ticks, or cycles."""
    from core import settings
    from engines.live_paper_fund_engine import LivePaperFundEngine
    from market.market_data_manager import MarketDataManager

    engine = engine or LivePaperFundEngine()
    manager = manager or MarketDataManager()
    fund_state_reader = fund_state_reader or _read_fund_state

    scheduler_enabled = bool(settings.ATLAS_SCHEDULER_ENABLED)
    auto_fund_enabled = bool(settings.AUTO_FUND_ENABLED)
    market_hours_only = bool(settings.AUTO_FUND_MARKET_HOURS_ONLY)

    # Provider realness: the configured provider must be safe, and the provider
    # that actually answers must be real with no fallback. health() probes a
    # price into the in-memory cache only (no database write).
    provider_configured_safe = engine.can_auto_run(manager)
    health = manager.health()
    active_provider = health.get("active_provider")
    fallback_used = bool(health.get("fallback_used"))
    provider_healthy = bool(health.get("healthy"))
    provider_active_real = _is_real_provider(active_provider) and not fallback_used

    state, fund_read_error = fund_state_reader()
    fund_status = (state or {}).get("fund_status")
    fund_ready = fund_status in {"READY", "RUNNING"}

    market = manager.market_status()

    checks = {
        "scheduler_enabled": scheduler_enabled,
        "auto_fund_enabled": auto_fund_enabled,
        "provider_configured_real": bool(provider_configured_safe),
        "provider_active_real": bool(provider_active_real),
        "provider_healthy": provider_healthy,
        "fund_ready": fund_ready,
    }
    ready = all(checks.values())

    return {
        "ready": ready,
        "verdict": "GO" if ready else "NO-GO",
        "read_only": True,
        "checks": checks,
        "flags": {
            "ATLAS_SCHEDULER_ENABLED": scheduler_enabled,
            "AUTO_FUND_ENABLED": auto_fund_enabled,
            "AUTO_FUND_MARKET_HOURS_ONLY": market_hours_only,
        },
        "provider": {
            "requested": manager.provider_name,
            "active": active_provider,
            "fallback_used": fallback_used,
            "healthy": provider_healthy,
            "configured_safe": bool(provider_configured_safe),
        },
        "fund": {
            "fund_status": fund_status,
            "read_error": fund_read_error,
        },
        "market": {
            "is_open": market.get("is_open"),
            "session": market.get("session"),
            "is_holiday": market.get("is_holiday"),
            "is_early_close": market.get("is_early_close"),
        },
        "safety": {
            "paper_only": True,
            "broker_integration": False,
            "real_money": False,
            "execution": "simulated_only",
            "human_approval_required_for_real_trading": True,
        },
        "next_steps": _next_steps(checks),
    }


def _next_steps(checks):
    steps = []
    if not checks["scheduler_enabled"]:
        steps.append("Set ATLAS_SCHEDULER_ENABLED=true.")
    if not checks["auto_fund_enabled"]:
        steps.append("Set AUTO_FUND_ENABLED=true.")
    if not checks["provider_configured_real"]:
        steps.append("Set MARKET_DATA_PROVIDER to a real provider (e.g. yahoo).")
    if not checks["provider_active_real"] or not checks["provider_healthy"]:
        steps.append(
            "Ensure the real provider is reachable (install yfinance / check "
            "network) so prices are validated with no fallback."
        )
    if not checks["fund_ready"]:
        steps.append("Start the fund via POST /paper-fund/start so it is READY.")

    return steps


def main():
    report = build_preflight_report()

    print("Live Paper Fund preflight (read-only; no cycle, no trade)")
    print(f"  requested provider : {report['provider']['requested']}")
    print(f"  active provider    : {report['provider']['active']}")
    print(f"  fallback used      : {report['provider']['fallback_used']}")
    print(f"  fund status        : {report['fund']['fund_status']}")
    print(
        "  market             : "
        f"{report['market']['session']} (open={report['market']['is_open']})"
    )
    print()
    for name, ok in report["checks"].items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if report["next_steps"]:
        print()
        print("  Next steps:")
        for step in report["next_steps"]:
            print(f"    - {step}")
    print()
    print(f"VERDICT: {report['verdict']}")

    return 0 if report["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
