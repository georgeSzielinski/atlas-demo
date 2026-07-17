import time


class MarketDataCache:
    """Deterministic in-memory cache for recent market responses.

    Tracks provider, timestamp, cache age, and whether a fallback was used. The
    clock is injectable so tests are deterministic.
    """

    DEFAULT_TTL_SECONDS = 300

    def __init__(self, ttl_seconds=None, clock=None):
        self.ttl_seconds = ttl_seconds or self.DEFAULT_TTL_SECONDS
        self._clock = clock or time.time
        self._store = {}

    def set(self, key, value, provider, fallback_used=False):
        self._store[key] = {
            "value": value,
            "provider": provider,
            "fallback_used": bool(fallback_used),
            "timestamp": self._clock(),
        }

    def get(self, key):
        entry = self._store.get(key)

        if entry is None:
            return None

        age = self._clock() - entry["timestamp"]

        if age > self.ttl_seconds:
            return None

        return self._decorate(entry, age)

    def peek(self, key):
        entry = self._store.get(key)

        if entry is None:
            return None

        return self._decorate(entry, self._clock() - entry["timestamp"])

    def entries(self):
        return [
            {"key": key, **self._decorate(entry, self._clock() - entry["timestamp"])}
            for key, entry in sorted(self._store.items())
        ]

    def clear(self):
        self._store = {}

    def stats(self):
        entries = self.entries()
        fresh = [entry for entry in entries if not entry["expired"]]

        return {
            "size": len(entries),
            "fresh_count": len(fresh),
            "expired_count": len(entries) - len(fresh),
            "ttl_seconds": self.ttl_seconds,
            "providers": sorted({entry["provider"] for entry in entries}),
            "fallback_entries": len([
                entry for entry in entries if entry["fallback_used"]
            ]),
            "latest_age": min(
                (entry["cache_age"] for entry in fresh),
                default=None,
            ),
        }

    def _decorate(self, entry, age):
        return {
            "value": entry["value"],
            "provider": entry["provider"],
            "fallback_used": entry["fallback_used"],
            "timestamp": entry["timestamp"],
            "cache_age": round(age, 4),
            "expired": age > self.ttl_seconds,
        }
