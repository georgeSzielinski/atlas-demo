import { memo } from 'react'
import { EmptyState } from './States'

// Renders a list of alert/incident/recommendation strings or objects.
function AlertList({ items, emptyTitle = 'All clear', emptyMessage, tone = 'neutral', max = 6 }) {
  const list = Array.isArray(items) ? items.filter(Boolean) : []
  if (list.length === 0) {
    return <EmptyState title={emptyTitle} message={emptyMessage} />
  }
  return (
    <ul className="dv2-alertlist">
      {list.slice(0, max).map((item, index) => {
        const severity = (item && typeof item === 'object' && item.severity) || tone
        const text =
          typeof item === 'string'
            ? item
            : item.message ?? item.reason ?? item.summary ?? JSON.stringify(item)
        const label = item && typeof item === 'object' ? item.subsystem ?? item.source : null
        return (
          <li className="dv2-alertlist__item" key={`${text}-${index}`}>
            <span className={`dv2-dot dv2-dot--${String(severity).toLowerCase()}`} aria-hidden="true" />
            <span className="dv2-alertlist__text">{text}</span>
            {label ? <span className="dv2-alertlist__tag">{label}</span> : null}
          </li>
        )
      })}
    </ul>
  )
}

export default memo(AlertList)
