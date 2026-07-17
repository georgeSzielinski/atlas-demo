import { memo } from 'react'
import SectionHeading from './SectionHeading'

// Generic dashboard panel: heading + optional action + body.
function Panel({ eyebrow, title, action, className = '', children }) {
  return (
    <section className={`dv2-panel ${className}`.trim()}>
      {(title || eyebrow || action) && (
        <div className="dv2-panel__head">
          <SectionHeading eyebrow={eyebrow} title={title} />
          {action ? <div className="dv2-panel__action">{action}</div> : null}
        </div>
      )}
      <div className="dv2-panel__body">{children}</div>
    </section>
  )
}

export default memo(Panel)
