import { memo } from 'react'
import { EmptyState } from './States'

// Vertical event timeline. Each event: { at, title, detail, tone }.
function Timeline({ events, emptyMessage = 'No recent events.', max = 12 }) {
  const list = Array.isArray(events) ? events.filter(Boolean) : []
  if (list.length === 0) {
    return <EmptyState title="No events" message={emptyMessage} />
  }
  return (
    <ol className="dv2-timeline">
      {list.slice(0, max).map((event, index) => (
        <li className="dv2-timeline__item" key={`${event.title}-${event.at}-${index}`}>
          <span className={`dv2-timeline__marker dv2-timeline__marker--${event.tone ?? 'neutral'}`} aria-hidden="true" />
          <div className="dv2-timeline__content">
            <div className="dv2-timeline__row">
              <span className="dv2-timeline__title">{event.title}</span>
              {event.at ? <span className="dv2-timeline__time">{event.at}</span> : null}
            </div>
            {event.detail ? <p className="dv2-timeline__detail">{event.detail}</p> : null}
          </div>
        </li>
      ))}
    </ol>
  )
}

export default memo(Timeline)
