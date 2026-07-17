import { memo, useEffect, useMemo, useRef, useState } from 'react'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { deriveLiveEvents, formatClock } from '../../services/paperFundOps'

// Floating profit/loss/system event popups, fed exclusively by stored records
// (simulated fills, snapshots, risk rejections, activity log) via
// deriveLiveEvents. On the FIRST payload everything is marked as already seen
// — popups only fire for events that appear in a LATER refresh, so nothing
// historical replays as if it just happened and no value is fabricated.

const MAX_VISIBLE = 4
const DISMISS_MS = 8000

function ToastCard({ event, onDismiss }) {
  return (
    <div className={`dv2-toast dv2-toast--${event.tone}`} role="status">
      <span className="dv2-toast__dot" aria-hidden="true" />
      <div className="dv2-toast__body">
        <div className="dv2-toast__row">
          <span className="dv2-toast__title">{event.title}</span>
          <span className="dv2-toast__time">{formatClock(event.at)}</span>
        </div>
        {event.detail ? <p className="dv2-toast__detail">{event.detail}</p> : null}
      </div>
      <button
        type="button"
        className="dv2-toast__close"
        aria-label="Dismiss notification"
        onClick={() => onDismiss(event.key)}
      >
        ×
      </button>
    </div>
  )
}

export const FloatingTradeEvent = memo(ToastCard)

function FloatingEventsLayer() {
  const { data } = useDashboardData()
  const fund = data?.paper_fund ?? {}
  const risk = data?.risk ?? {}
  const [toasts, setToasts] = useState([])
  const seenRef = useRef(null)

  const events = useMemo(() => deriveLiveEvents(fund, risk), [fund, risk])

  useEffect(() => {
    if (!data) return
    if (seenRef.current === null) {
      // First payload: baseline only. Historic events never pop.
      seenRef.current = new Set(events.map((event) => event.key))
      return
    }
    const fresh = events.filter((event) => !seenRef.current.has(event.key))
    if (fresh.length === 0) return
    for (const event of fresh) seenRef.current.add(event.key)
    setToasts((prev) => [...fresh.slice(0, MAX_VISIBLE), ...prev].slice(0, MAX_VISIBLE))
  }, [data, events])

  // Retire the oldest visible toast on a fixed cadence.
  useEffect(() => {
    if (toasts.length === 0) return undefined
    const id = setTimeout(
      () => setToasts((prev) => prev.slice(0, -1)),
      DISMISS_MS,
    )
    return () => clearTimeout(id)
  }, [toasts])

  if (toasts.length === 0) return null

  return (
    <div className="dv2-toasts" aria-live="polite">
      {toasts.map((event) => (
        <FloatingTradeEvent
          key={event.key}
          event={event}
          onDismiss={(key) => setToasts((prev) => prev.filter((toast) => toast.key !== key))}
        />
      ))}
    </div>
  )
}

export default memo(FloatingEventsLayer)
