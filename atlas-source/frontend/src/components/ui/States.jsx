import { memo } from 'react'

// Consistent loading / empty / error placeholders shared by all panels.

function LoadingStateBase({ label = 'Loading…' }) {
  return (
    <div className="dv2-state dv2-state--loading" role="status">
      <span className="dv2-spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}

function EmptyStateBase({ title = 'No data yet', message }) {
  return (
    <div className="dv2-state dv2-state--empty">
      <p className="dv2-state__title">{title}</p>
      {message ? <p className="dv2-state__message">{message}</p> : null}
    </div>
  )
}

function ErrorStateBase({ message = 'Something went wrong.' }) {
  return (
    <div className="dv2-state dv2-state--error" role="alert">
      <p className="dv2-state__title">Unavailable</p>
      <p className="dv2-state__message">{message}</p>
    </div>
  )
}

export const LoadingState = memo(LoadingStateBase)
export const EmptyState = memo(EmptyStateBase)
export const ErrorState = memo(ErrorStateBase)
