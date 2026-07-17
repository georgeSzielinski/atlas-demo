import { memo } from 'react'
import StatusPill from '../ui/StatusPill'

// Compact memo card used by the Executive Briefing columns. Deliberately small:
// an eyebrow, a title, an optional status pill, and freeform body content.
function BriefingMemo({ eyebrow, title, status, statusLabel, statusTone, children }) {
  return (
    <section className="dv3-memo">
      <div className="dv3-memo__head">
        <div className="dv3-memo__titles">
          {eyebrow ? <span className="dv3-memo__eyebrow">{eyebrow}</span> : null}
          <h4 className="dv3-memo__title">{title}</h4>
        </div>
        {status ? <StatusPill status={status} tone={statusTone} label={statusLabel ?? status} /> : null}
      </div>
      <div className="dv3-memo__body">{children}</div>
    </section>
  )
}

export default memo(BriefingMemo)
