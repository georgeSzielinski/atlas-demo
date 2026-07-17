import { memo } from 'react'

function SectionHeading({ eyebrow, title }) {
  if (!eyebrow && !title) {
    return null
  }
  return (
    <div className="dv2-heading">
      {eyebrow ? <p className="dv2-heading__eyebrow">{eyebrow}</p> : null}
      {title ? <h3 className="dv2-heading__title">{title}</h3> : null}
    </div>
  )
}

export default memo(SectionHeading)
