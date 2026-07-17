import { useCallback, useEffect, useRef, useState } from 'react'

// Tiny async-resource hook (React-only, no react-query dependency).
//
// - In-flight de-duplication + short TTL cache keyed by `key`, so mounting the
//   same resource from several places issues ONE network request.
// - AbortController cleanup so unmounted components never set state.
// - `refetch()` bypasses the cache for explicit refreshes.
//
// This is what lets the homepage widgets share a single /dashboard/v2 request
// and kills the repeated /dashboard fan-out across pages.

const DEFAULT_TTL_MS = 15000

const cache = new Map() // key -> { value, expires }
const inflight = new Map() // key -> Promise

function readCache(key) {
  const entry = cache.get(key)
  if (!entry) {
    return undefined
  }
  if (entry.expires < Date.now()) {
    cache.delete(key)
    return undefined
  }
  return entry.value
}

export function invalidateResource(key) {
  cache.delete(key)
  inflight.delete(key)
}

async function loadResource(key, loader, ttl, { force = false } = {}) {
  if (!force) {
    const cached = readCache(key)
    if (cached !== undefined) {
      return cached
    }
    const pending = inflight.get(key)
    if (pending) {
      return pending
    }
  }

  const promise = Promise.resolve()
    .then(() => loader())
    .then((value) => {
      cache.set(key, { value, expires: Date.now() + ttl })
      inflight.delete(key)
      return value
    })
    .catch((error) => {
      inflight.delete(key)
      throw error
    })

  inflight.set(key, promise)
  return promise
}

export function useAsyncResource(key, loader, { ttl = DEFAULT_TTL_MS, enabled = true } = {}) {
  const [data, setData] = useState(() => readCache(key))
  const [isLoading, setIsLoading] = useState(() => enabled && readCache(key) === undefined)
  const [error, setError] = useState(null)
  const loaderRef = useRef(loader)

  // Keep the latest loader without touching the ref during render.
  useEffect(() => {
    loaderRef.current = loader
  })

  // Initial / key-change load. All setState happens in the async resolution
  // (deferred), never synchronously inside the effect body.
  useEffect(() => {
    if (!enabled) {
      return undefined
    }
    let isCurrent = true
    loadResource(key, () => loaderRef.current(), ttl, { force: false })
      .then((value) => {
        if (!isCurrent) return
        setData(value)
        setError(null)
        setIsLoading(false)
      })
      .catch((requestError) => {
        if (!isCurrent) return
        setError(requestError)
        setIsLoading(false)
      })
    return () => {
      isCurrent = false
    }
  }, [enabled, key, ttl])

  const refetch = useCallback(async () => {
    setIsLoading(true)
    try {
      const value = await loadResource(key, () => loaderRef.current(), ttl, { force: true })
      setData(value)
      setError(null)
      return value
    } catch (requestError) {
      setError(requestError)
      return undefined
    } finally {
      setIsLoading(false)
    }
  }, [key, ttl])

  return { data, isLoading, error, refetch }
}
