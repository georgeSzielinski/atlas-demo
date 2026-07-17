from datetime import datetime


class OperationsEngine:
    """Deterministic, read-only Atlas Operations Center aggregator.

    OperationsEngine composes one operational picture of Atlas from existing
    read-only surfaces: the backend scheduler runtime, the Market Data Manager,
    the Live Paper Fund status, and read-only database row counts. It owns no
    business logic of its own; every section is a thin projection over an engine
    or endpoint that already exists.

    It is strictly observational. It never writes to the database, never runs a
    scheduler tick or a paper-fund cycle, never changes recommendations, risk,
    providers, or thresholds, and never connects a broker. Every collaborator is
    injectable so tests can drive deterministic, offline reports, and every
    section degrades to an ``Unavailable`` sub-report instead of raising when a
    dependency is missing: ``report`` never raises because one subsystem is
    unavailable.
    """

    VERSION = "operations-center-v1"

    # Health severity, least to most severe. The overall level is the most
    # severe signal observed across subsystems.
    HEALTH_LEVELS = ["Healthy", "Warning", "Degraded", "Offline"]

    DEFAULT_TABLES = [
        "atlas_runs",
        "recommendations",
        "portfolio_snapshots",
        "paper_fund_snapshots",
        "paper_fund_orders",
        "paper_fund_activity",
        "runtime_states",
    ]

    # Deterministic ordering for merged error sources.
    ERROR_SOURCE_ORDER = [
        "scheduler",
        "market_data",
        "paper_fund",
        "learning",
        "database",
    ]

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def report(
        self,
        scheduler=None,
        market_manager=None,
        fund=None,
        settings=None,
        now=None,
        row_counter=None,
        db_path=None,
        tables=None,
    ):
        settings = settings if settings is not None else self._default_settings()
        moment = self._moment(now)

        scheduler_raw = self._fetch(
            lambda: (scheduler or self._default_scheduler()).status()
        )
        market_raw = self._fetch(lambda: self._market_raw(market_manager))
        fund_raw = self._fetch(lambda: (fund or self._default_fund()).status())
        database_raw = self._fetch(
            lambda: self._database_raw(row_counter, db_path, tables)
        )

        scheduler_section = self._scheduler_section(scheduler_raw, settings)
        market_section = self._market_section(market_raw)
        fund_section = self._fund_section(fund_raw)
        learning_section = self._learning_section(fund_raw)
        database_section = self._database_section(database_raw)
        uptime_section = self._uptime_section(
            scheduler_section, fund_section, moment
        )

        recent_errors = self._recent_errors(
            scheduler_section, market_section, fund_section, database_section
        )
        warnings = self._warnings(
            scheduler_section, market_section, fund_section, settings
        )
        operational_mode = self._operational_mode(market_section, settings)
        overall_health = self._overall_health(
            [
                scheduler_section,
                market_section,
                fund_section,
                database_section,
            ],
            fund_section,
            recent_errors,
            warnings,
        )
        operational_recommendations = self._operational_recommendations(
            overall_health,
            scheduler_section,
            market_section,
            fund_section,
            operational_mode,
            settings,
        )

        return {
            "generated_at": moment.isoformat(),
            "version": self.VERSION,
            "overall_health": overall_health,
            "scheduler": scheduler_section,
            "market_data": market_section,
            "paper_fund": fund_section,
            "learning": learning_section,
            "database": database_section,
            "uptime": uptime_section,
            "recent_errors": recent_errors,
            "operational_recommendations": operational_recommendations,
            "warnings": warnings,
            "operational_mode": operational_mode,
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------
    def _scheduler_section(self, fetched, settings):
        if not fetched["ok"]:
            return self._unavailable(fetched["error"])

        status = fetched["value"] or {}
        return {
            "status": "EVALUATED",
            "enabled": status.get("enabled"),
            "running": status.get("running"),
            "owned": status.get("owned"),
            "interval_seconds": status.get("interval_seconds"),
            "started_at": status.get("started_at"),
            "tick_count": status.get("tick_count"),
            "last_tick_at": status.get("last_tick_at"),
            "last_status": status.get("last_status"),
            "last_reason": status.get("last_reason"),
            "error_count": status.get("error_count"),
            "last_error_at": status.get("last_error_at"),
            "auto_fund_enabled": bool(
                getattr(settings, "AUTO_FUND_ENABLED", False)
            ),
        }

    def _market_section(self, fetched):
        if not fetched["ok"]:
            return self._unavailable(fetched["error"])

        value = fetched["value"] or {}
        health = value.get("health", {}) or {}
        snapshot = value.get("snapshot", {}) or {}
        freshness = value.get("freshness", {}) or {}
        stats = value.get("cache_stats", {}) or {}
        return {
            "status": "EVALUATED",
            "requested_provider": health.get("requested_provider"),
            "active_provider": health.get("active_provider"),
            "healthy": health.get("healthy"),
            "fallback_used": health.get("fallback_used"),
            "offline_capable": health.get("offline_capable"),
            "last_error": health.get("last_error"),
            "validated": snapshot.get("validated"),
            "ticker_count": snapshot.get("ticker_count"),
            "market_session": (snapshot.get("market_status") or {}).get("session"),
            "market_is_open": (snapshot.get("market_status") or {}).get("is_open"),
            "data_freshness": freshness,
            "cache_entries": stats.get("entries"),
        }

    def _fund_section(self, fetched):
        if not fetched["ok"]:
            return self._unavailable(fetched["error"])

        status = fetched["value"] or {}
        latest = status.get("latest_snapshot") or {}
        return {
            "status": "EVALUATED",
            "fund_status": status.get("fund_status", "OFF"),
            "watchlist_size": len(status.get("watchlist") or []),
            "cash": status.get("cash"),
            "realized_pl": status.get("realized_pl"),
            "interval_minutes": status.get("interval_minutes"),
            "last_update": status.get("last_update"),
            "next_update": status.get("next_update"),
            "last_error": status.get("last_error"),
            "price_provider": status.get("price_provider"),
            "open_position_count": len(status.get("open_positions") or {}),
            "snapshot_count": len(status.get("snapshots") or []),
            "portfolio_value": latest.get("portfolio_value"),
            "total_return": latest.get("total_return"),
        }

    def _learning_section(self, fetched):
        if not fetched["ok"]:
            return self._unavailable(fetched["error"])

        status = fetched["value"] or {}
        learning_log = status.get("learning_log") or []
        latest = learning_log[0] if learning_log else {}
        return {
            "status": "EVALUATED",
            "learning_active": bool(learning_log),
            "learning_entries": len(learning_log),
            "latest_lesson": latest.get("lesson"),
            "latest_learning_at": latest.get("at"),
        }

    def _database_section(self, fetched):
        if not fetched["ok"]:
            return self._unavailable(fetched["error"])

        value = fetched["value"] or {}
        counts = value.get("counts", {}) or {}
        return {
            "status": "EVALUATED",
            "exists": bool(value.get("exists")),
            "table_count": len(counts),
            "row_counts": counts,
            "total_rows": sum(counts.values()),
        }

    def _uptime_section(self, scheduler_section, fund_section, moment):
        started_at, source = self._uptime_origin(scheduler_section, fund_section)
        if not started_at:
            return {
                "status": "NOT_STARTED",
                "source": None,
                "started_at": None,
                "uptime_seconds": None,
                "uptime_human": None,
                "reason": "No scheduler or paper-fund start time is available yet.",
            }

        origin = self._parse_time(started_at)
        if origin is None:
            return {
                "status": "NOT_STARTED",
                "source": source,
                "started_at": started_at,
                "uptime_seconds": None,
                "uptime_human": None,
                "reason": "Start time could not be parsed.",
            }

        seconds = max(0, int((moment - origin).total_seconds()))
        return {
            "status": "EVALUATED",
            "source": source,
            "started_at": started_at,
            "uptime_seconds": seconds,
            "uptime_human": self._humanize_seconds(seconds),
        }

    # ------------------------------------------------------------------
    # Cross-cutting derivations
    # ------------------------------------------------------------------
    def _recent_errors(
        self, scheduler_section, market_section, fund_section, database_section
    ):
        errors = []

        for name, section in (
            ("scheduler", scheduler_section),
            ("market_data", market_section),
            ("paper_fund", fund_section),
            ("database", database_section),
        ):
            if section.get("status") == "Unavailable":
                errors.append({
                    "source": name,
                    "message": section.get("reason")
                    or "Subsystem is unavailable.",
                    "at": None,
                })

        if scheduler_section.get("status") == "EVALUATED":
            error_count = scheduler_section.get("error_count") or 0
            if error_count:
                errors.append({
                    "source": "scheduler",
                    "message": (
                        f"{error_count} scheduler tick error(s) recorded."
                    ),
                    "at": scheduler_section.get("last_error_at"),
                })

        if market_section.get("status") == "EVALUATED":
            last_error = market_section.get("last_error")
            if last_error:
                errors.append({
                    "source": "market_data",
                    "message": str(last_error),
                    "at": None,
                })

        if fund_section.get("status") == "EVALUATED":
            if fund_section.get("fund_status") == "ERROR" or fund_section.get(
                "last_error"
            ):
                errors.append({
                    "source": "paper_fund",
                    "message": fund_section.get("last_error")
                    or "Live paper fund is in an ERROR state.",
                    "at": fund_section.get("last_update"),
                })

        return self._dedupe_errors(errors)

    def _warnings(self, scheduler_section, market_section, fund_section, settings):
        warnings = set()

        if market_section.get("status") == "EVALUATED":
            if market_section.get("fallback_used"):
                warnings.add(
                    "Market data fell back to a non-primary provider."
                )
            provider = market_section.get("active_provider")
            if provider in {"mock", None}:
                warnings.add("Mock market data provider is active (offline mode).")
            if market_section.get("validated") is False:
                warnings.add("Latest market prices are not validated.")
            if (market_section.get("data_freshness") or {}).get("is_stale"):
                warnings.add("Market data cache is stale.")

        if scheduler_section.get("status") == "EVALUATED":
            if scheduler_section.get("enabled") is False:
                warnings.add("Automatic scheduler is disabled.")

        if not bool(getattr(settings, "AUTO_FUND_ENABLED", False)):
            warnings.add("Automatic paper-fund operation is disabled.")

        if fund_section.get("status") == "EVALUATED":
            fund_status = fund_section.get("fund_status")
            if fund_status in {"OFF", "PAUSED"}:
                warnings.add(
                    f"Live paper fund is not running (status={fund_status})."
                )

        return sorted(warnings)

    def _operational_mode(self, market_section, settings):
        provider = None
        if market_section.get("status") == "EVALUATED":
            provider = market_section.get("active_provider") or market_section.get(
                "requested_provider"
            )
        if not provider:
            provider = getattr(settings, "DATA_PROVIDER", None)

        auto_fund = bool(getattr(settings, "AUTO_FUND_ENABLED", False))
        scheduler_enabled = bool(
            getattr(settings, "ATLAS_SCHEDULER_ENABLED", False)
        )
        real_provider = str(provider or "").strip().lower() not in {
            "mock",
            "test",
            "unknown",
            "",
        }
        mode = "LIVE_PAPER" if (auto_fund and real_provider) else "OFFLINE_MOCK"

        return {
            "mode": mode,
            "data_provider": provider,
            "auto_fund_enabled": auto_fund,
            "scheduler_enabled": scheduler_enabled,
            "paper_only": True,
            "broker_integration": False,
            "real_money": False,
        }

    def _overall_health(self, sections, fund_section, recent_errors, warnings):
        unavailable = [s for s in sections if s.get("status") == "Unavailable"]

        if unavailable and len(unavailable) == len(sections):
            return self._health(
                "Offline",
                "All monitored subsystems are unavailable.",
            )

        degraded = bool(recent_errors) or bool(unavailable) or (
            fund_section.get("status") == "EVALUATED"
            and fund_section.get("fund_status") == "ERROR"
        )
        if degraded:
            return self._health(
                "Degraded",
                "One or more subsystems reported errors or are unavailable.",
            )

        if warnings:
            return self._health(
                "Warning",
                "All subsystems are up, but non-fatal warnings are present.",
            )

        return self._health(
            "Healthy",
            "All monitored subsystems are healthy.",
        )

    def _operational_recommendations(
        self,
        overall_health,
        scheduler_section,
        market_section,
        fund_section,
        operational_mode,
        settings,
    ):
        recommendations = []

        if (
            fund_section.get("status") == "EVALUATED"
            and fund_section.get("fund_status") == "ERROR"
        ):
            recommendations.append(
                "Investigate the live paper fund error and resume the fund "
                "once the underlying issue is resolved."
            )

        if (
            scheduler_section.get("status") == "EVALUATED"
            and (scheduler_section.get("error_count") or 0) > 0
        ):
            recommendations.append(
                "Review recorded scheduler tick errors (see recent_errors)."
            )

        if (
            market_section.get("status") == "EVALUATED"
            and market_section.get("active_provider") in {"mock", None}
        ):
            recommendations.append(
                "Set MARKET_DATA_PROVIDER=yahoo to use validated real prices "
                "before enabling live paper operation."
            )

        if bool(getattr(settings, "AUTO_FUND_ENABLED", False)) and not bool(
            getattr(settings, "ATLAS_SCHEDULER_ENABLED", False)
        ):
            recommendations.append(
                "Enable ATLAS_SCHEDULER_ENABLED to run automatic paper-fund "
                "cycles on the configured interval."
            )

        for section, name in (
            (scheduler_section, "scheduler"),
            (market_section, "market data"),
            (fund_section, "paper fund"),
        ):
            if section.get("status") == "Unavailable":
                recommendations.append(
                    f"Restore the {name} subsystem; it is currently unavailable."
                )

        if not recommendations and overall_health["status"] == "Healthy":
            recommendations.append("No operational action required.")

        return recommendations

    # ------------------------------------------------------------------
    # Raw fetch helpers (each read-only)
    # ------------------------------------------------------------------
    def _market_raw(self, market_manager):
        from market.provider_health import data_freshness

        manager = market_manager or self._default_market_manager()
        health = manager.health()
        cache = manager.cache_status()
        snapshot = manager.snapshot()
        stats = cache.get("stats", {}) or {}
        return {
            "health": health,
            "cache_stats": {"entries": len(cache.get("entries", []) or [])},
            "snapshot": snapshot,
            "freshness": data_freshness(stats.get("latest_age")),
        }

    def _database_raw(self, row_counter, db_path, tables):
        counter = row_counter or self._default_row_counter()
        path = db_path if db_path is not None else self._default_db_path()
        table_names = list(tables or self.DEFAULT_TABLES)
        counts = {name: int(counter(name)) for name in table_names}
        return {"exists": self._path_exists(path), "counts": counts}

    # ------------------------------------------------------------------
    # Defaults (lazy imports avoid heavy/circular imports at module load)
    # ------------------------------------------------------------------
    def _default_scheduler(self):
        from api.scheduler_runtime import scheduler_runtime

        return scheduler_runtime

    def _default_market_manager(self):
        from market.market_data_manager import MarketDataManager

        return MarketDataManager()

    def _default_fund(self):
        from engines.live_paper_fund_engine import LivePaperFundEngine

        return LivePaperFundEngine()

    def _default_settings(self):
        from core import settings

        return settings

    def _default_row_counter(self):
        from backend.status import count_rows

        return count_rows

    def _default_db_path(self):
        from backend.status import DATABASE_PATH

        return DATABASE_PATH

    # ------------------------------------------------------------------
    # Small utilities
    # ------------------------------------------------------------------
    def _fetch(self, producer):
        try:
            return {"ok": True, "value": producer()}
        except Exception as error:  # never propagate a subsystem failure
            return {"ok": False, "error": str(error)}

    def _unavailable(self, reason):
        return {"status": "Unavailable", "reason": reason}

    def _health(self, status, reason):
        return {"status": status, "reason": reason}

    def _dedupe_errors(self, errors):
        seen = set()
        unique = []
        for error in errors:
            key = (error["source"], error["message"])
            if key in seen:
                continue
            seen.add(key)
            unique.append(error)

        order = {name: index for index, name in enumerate(self.ERROR_SOURCE_ORDER)}
        unique.sort(
            key=lambda error: (
                order.get(error["source"], len(order)),
                error["message"],
            )
        )
        return unique

    def _uptime_origin(self, scheduler_section, fund_section):
        if scheduler_section.get("status") == "EVALUATED":
            started_at = scheduler_section.get("started_at")
            if started_at:
                return started_at, "scheduler"

        if fund_section.get("status") == "EVALUATED":
            last_update = fund_section.get("last_update")
            if last_update:
                return last_update, "paper_fund"

        return None, None

    def _parse_time(self, value):
        text = str(value)
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            pass
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(text[:len(fmt) + 2].strip(), fmt)
            except ValueError:
                continue
        return None

    def _humanize_seconds(self, seconds):
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, secs = divmod(remainder, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")
        return " ".join(parts)

    def _path_exists(self, path):
        try:
            if hasattr(path, "exists"):
                return bool(path.exists())
            import os

            return os.path.exists(str(path))
        except Exception:
            return False

    def _moment(self, now):
        if isinstance(now, datetime):
            return now
        if now:
            parsed = self._parse_time(now)
            if parsed is not None:
                return parsed
        return datetime.now()

    def policy(self):
        return {
            "read_only": True,
            "deterministic": True,
            "paper_only": True,
            "writes": False,
            "broker_integration": False,
            "real_money": False,
            "modifies_scheduler": False,
            "modifies_paper_fund": False,
            "modifies_recommendations": False,
            "modifies_risk": False,
        }
