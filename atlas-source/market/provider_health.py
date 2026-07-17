HEALTHY = "Healthy"
UNAVAILABLE = "Unavailable"
OFFLINE = "Offline"
MOCK = "Mock"
EXPERIMENTAL = "Experimental"
DEPRECATED = "Deprecated"

HEALTH_STATUSES = [
    HEALTHY,
    UNAVAILABLE,
    OFFLINE,
    MOCK,
    EXPERIMENTAL,
    DEPRECATED,
]


def provider_health(status, healthy=False, message=""):
    if status not in HEALTH_STATUSES:
        status = UNAVAILABLE

    return {
        "status": status,
        "healthy": bool(healthy),
        "message": message,
    }


def data_freshness(age_seconds, stale_threshold_seconds=300):
    """Deterministic freshness label from a cache/data age in seconds."""
    if age_seconds is None:
        return {
            "age_seconds": None,
            "label": "Unknown",
            "is_stale": True,
        }

    age = max(0, round(age_seconds, 4))

    if age <= 60:
        label = "Fresh"
    elif age <= stale_threshold_seconds:
        label = "Recent"
    else:
        label = "Stale"

    return {
        "age_seconds": age,
        "label": label,
        "is_stale": age > stale_threshold_seconds,
    }


def summarize_provider_health(providers):
    counts = {status: 0 for status in HEALTH_STATUSES}

    for provider in providers:
        status = provider.get("health", {}).get(
            "status",
            provider.get("status", UNAVAILABLE),
        )
        if status not in counts:
            status = UNAVAILABLE
        counts[status] += 1

    return {
        "total_providers": len(providers),
        "healthy_count": len([
            provider for provider in providers
            if provider.get("health", {}).get("healthy") is True
        ]),
        "offline_capable_count": len([
            provider for provider in providers
            if provider.get("supports_offline") is True
        ]),
        "requires_api_key_count": len([
            provider for provider in providers
            if provider.get("requires_api_key") is True
        ]),
        "status_counts": counts,
    }
