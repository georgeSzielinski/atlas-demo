import { memo } from 'react'
import { EmptyState } from '../ui/States'

// A titled report block. When `available` is false it renders a calm
// NOT_EVALUATED empty state instead of the children, so the report never shows
// fabricated or zero-filled analysis.
function ReportSection({ title, eyebrow, available = true, emptyMessage, children }) {
  return (
    <section className="dv3-report__section">
      <div className="dv3-report__section-head">
        {eyebrow ? <span className="dv3-report__eyebrow">{eyebrow}</span> : null}
        <h3 className="dv3-report__section-title">{title}</h3>
      </div>
      {available ? (
        children
      ) : (
        <EmptyState
          title="Not evaluated"
          message={emptyMessage ?? 'No supporting data is available for this section yet.'}
        />
      )}
    </section>
  )
}

export default memo(ReportSection)
