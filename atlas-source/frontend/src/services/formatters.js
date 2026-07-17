// Shared, dependency-free formatting + normalization helpers.
// Single source of truth so pages stop copy-pasting these.

export const UNAVAILABLE = 'Unavailable'

export function formatValue(value, fallback = UNAVAILABLE) {
  if (value === null || value === undefined || value === '') {
    return fallback
  }
  return String(value)
}

export function formatNumber(value, { digits = 2, fallback = UNAVAILABLE } = {}) {
  if (value === null || value === undefined || value === '') {
    return fallback
  }
  const numberValue = Number(value)
  if (Number.isNaN(numberValue)) {
    return fallback
  }
  return numberValue
    .toFixed(digits)
    .replace(/\.0+$/, '')
    .replace(/(\.\d*?)0+$/, '$1')
}

export function formatMetric(value, suffix = '', options = {}) {
  const formatted = formatNumber(value, options)
  if (formatted === (options.fallback ?? UNAVAILABLE)) {
    return formatted
  }
  return `${formatted}${suffix}`
}

export function formatPercent(value, { digits = 2, fallback = UNAVAILABLE } = {}) {
  if (value === null || value === undefined || value === '') {
    return fallback
  }
  const numberValue = Number(value)
  if (Number.isNaN(numberValue)) {
    return fallback
  }
  return `${formatNumber(numberValue, { digits })}%`
}

export function formatCurrency(value, { fallback = UNAVAILABLE, currency = 'USD' } = {}) {
  if (value === null || value === undefined || value === '') {
    return fallback
  }
  const numberValue = Number(value)
  if (Number.isNaN(numberValue)) {
    return fallback
  }
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      maximumFractionDigits: 2,
    }).format(numberValue)
  } catch {
    return `$${formatNumber(numberValue)}`
  }
}

// Confidence may arrive as a 0-1 fraction or a 0-100 score; render honestly.
export function formatConfidence(value, { fallback = UNAVAILABLE } = {}) {
  if (value === null || value === undefined || value === '') {
    return fallback
  }
  const numberValue = Number(value)
  if (Number.isNaN(numberValue)) {
    return fallback
  }
  return formatPercent(numberValue <= 1 ? numberValue * 100 : numberValue, { fallback })
}

export function formatSignedPercent(value, options = {}) {
  const formatted = formatPercent(value, options)
  if (formatted === (options.fallback ?? UNAVAILABLE)) {
    return formatted
  }
  const numberValue = Number(value)
  return numberValue > 0 ? `+${formatted}` : formatted
}

// Tone helper for returns/deltas: positive / negative / neutral.
export function toneForDelta(value) {
  const numberValue = Number(value)
  if (Number.isNaN(numberValue) || numberValue === 0) {
    return 'neutral'
  }
  return numberValue > 0 ? 'positive' : 'negative'
}

export function asArray(value) {
  if (Array.isArray(value)) {
    return value
  }
  if (value === null || value === undefined || value === '') {
    return []
  }
  return [value]
}

// A section is "evaluated" when it is a dict without a NOT_EVALUATED/Unavailable
// status. Panels use this to decide between real content and an empty state.
export function isEvaluated(section) {
  if (!section || typeof section !== 'object') {
    return false
  }
  const status = section.status
  return status !== 'NOT_EVALUATED' && status !== 'Unavailable'
}

export function sectionReason(section, fallback = 'No data available yet.') {
  if (section && typeof section === 'object' && section.reason) {
    return String(section.reason)
  }
  return fallback
}
