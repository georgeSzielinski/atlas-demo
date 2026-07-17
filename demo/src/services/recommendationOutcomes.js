// Pure, read-only selectors for recommendation outcome evidence. The shared
// records endpoint returns one row per exact recommendation/horizon pair; these
// helpers index once by recommendation_id and never infer identity from ticker.

export const OUTCOME_RECORD_LIMIT = 10000
export const OUTCOME_RESOURCE_KEY = `recommendation-intelligence/records?limit=${OUTCOME_RECORD_LIMIT}`
export const OUTCOME_HORIZONS = [7, 30, 90, 180, 365]

const STATUS_MAP = new Map([
  ['succeeded', 'Succeeded'],
  ['failed', 'Failed'],
  ['expired', 'Expired'],
  ['deferred', 'Deferred'],
  ['pending', 'Pending'],
])
const COMPLETED = new Set(['Succeeded', 'Failed', 'Expired'])

function objectOrNull(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : null
}

function textOrNull(value) {
  if (value === null || value === undefined) return null
  const text = String(value).trim()
  return text || null
}

function finiteNumber(value) {
  if (value === null || value === undefined || value === '' || typeof value === 'boolean') {
    return null
  }
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function positiveInteger(value) {
  const number = finiteNumber(value)
  return number !== null && Number.isInteger(number) && number > 0 ? number : null
}

function timeValue(value) {
  if (!value) return Number.NEGATIVE_INFINITY
  const parsed = Date.parse(value)
  return Number.isNaN(parsed) ? Number.NEGATIVE_INFINITY : parsed
}

export function normalizeOutcomeStatus(value) {
  const key = textOrNull(value)?.toLowerCase()
  return key ? (STATUS_MAP.get(key) ?? 'Unavailable') : 'Unavailable'
}

export function outcomeResult(status) {
  switch (normalizeOutcomeStatus(status)) {
    case 'Succeeded':
      return 'Correct'
    case 'Failed':
      return 'Incorrect'
    case 'Expired':
      return 'Expired'
    case 'Deferred':
      return 'Deferred'
    case 'Pending':
      return 'Pending'
    default:
      return 'Unavailable'
  }
}

export function outcomeTone(value) {
  const key = String(value ?? '')
  if (key === 'Succeeded' || key === 'Correct') return 'positive'
  if (key === 'Failed' || key === 'Incorrect') return 'negative'
  if (key === 'Pending' || key === 'Deferred') return 'warn'
  if (key === 'Expired') return 'neutral'
  return 'muted'
}

export function normalizeOutcomeRow(row) {
  const source = objectOrNull(row)
  if (!source) return null

  const recommendationId = positiveInteger(source.recommendation_id)
  if (recommendationId === null) return null

  const outcomeId = positiveInteger(source.outcome_id ?? source.id)
  const horizonDays = positiveInteger(source.horizon_days ?? source.holding_period)
  const rawStatus = textOrNull(source.status)
  const rawReturn = finiteNumber(source.percentage_return)
  const evaluationAt = textOrNull(source.evaluation_at ?? source.evaluation_timestamp)
  const hasOutcomeEvidence =
    outcomeId !== null ||
    horizonDays !== null ||
    rawStatus !== null ||
    rawReturn !== null ||
    evaluationAt !== null

  return {
    outcomeId,
    recommendationId,
    ticker: textOrNull(source.ticker),
    action: textOrNull(source.action ?? source.recommendation),
    status: normalizeOutcomeStatus(rawStatus),
    result: outcomeResult(rawStatus),
    horizonDays,
    rawReturn,
    evaluationAt,
    entryAt: textOrNull(source.entry_at ?? source.recommendation_timestamp),
    evaluationSource: textOrNull(source.evaluation_source),
    paperOrderId: textOrNull(source.paper_order_id),
    startingPrice: finiteNumber(source.starting_price),
    endingPrice: finiteNumber(source.ending_price),
    completed: COMPLETED.has(normalizeOutcomeStatus(rawStatus)),
    hasOutcomeEvidence,
  }
}

function outcomeSignature(row) {
  return [
    row.outcomeId,
    row.recommendationId,
    row.horizonDays,
    row.evaluationSource,
    row.evaluationAt,
    row.status,
    row.rawReturn,
    row.action,
  ].map((value) => String(value ?? '')).join('|')
}

function completeness(row) {
  return [
    row.outcomeId,
    row.horizonDays,
    row.evaluationSource,
    row.evaluationAt,
    row.entryAt,
    row.rawReturn,
    row.action,
  ].filter((value) => value !== null).length
}

function preferredDuplicate(left, right) {
  const completenessDelta = completeness(left) - completeness(right)
  if (completenessDelta !== 0) return completenessDelta > 0 ? left : right
  return outcomeSignature(left).localeCompare(outcomeSignature(right)) >= 0 ? left : right
}

function compareOutcomeRows(left, right) {
  return (
    timeValue(left.evaluationAt) - timeValue(right.evaluationAt) ||
    (left.outcomeId ?? -1) - (right.outcomeId ?? -1) ||
    (left.horizonDays ?? -1) - (right.horizonDays ?? -1) ||
    outcomeSignature(left).localeCompare(outcomeSignature(right))
  )
}

function duplicateKey(row) {
  if (row.outcomeId !== null) return `id:${row.outcomeId}`
  return `row:${outcomeSignature(row)}`
}

export function indexOutcomeRows(rows) {
  const list = Array.isArray(rows) ? rows : []
  const deduped = new Map()

  for (const sourceRow of list) {
    const row = normalizeOutcomeRow(sourceRow)
    if (!row?.hasOutcomeEvidence) continue
    if (!deduped.has(row.recommendationId)) deduped.set(row.recommendationId, new Map())
    const recommendationRows = deduped.get(row.recommendationId)
    const key = duplicateKey(row)
    const existing = recommendationRows.get(key)
    recommendationRows.set(key, existing ? preferredDuplicate(existing, row) : row)
  }

  const index = new Map()
  for (const [recommendationId, recommendationRows] of deduped) {
    index.set(recommendationId, [...recommendationRows.values()].sort(compareOutcomeRows))
  }
  return index
}

function sourceRows(payload) {
  if (Array.isArray(payload)) return { rows: payload, available: true }
  const source = objectOrNull(payload)
  if (!source) return { rows: [], available: false }
  for (const key of ['recommendation_intelligence_records', 'recommendation_outcomes', 'outcomes']) {
    if (Array.isArray(source[key])) return { rows: source[key], available: true }
  }
  return { rows: [], available: false }
}

export function outcomeSourceMeta(payload) {
  const source = sourceRows(payload)
  const meta = objectOrNull(payload?.meta) ?? {}
  const sourceTotal = finiteNumber(meta.source_total_row_count ?? meta.total)
  const analyzed = finiteNumber(meta.analyzed_row_count) ?? source.rows.length
  const truncated = Boolean(meta.truncated)
  const backendWarning = textOrNull(meta.warning)
  const warning = truncated
    ? backendWarning ?? (
      `Outcome evidence is truncated: ${analyzed} of ${sourceTotal ?? 'an unknown number of'} ` +
      'source rows were analyzed. Reported outcome summaries may be incomplete.'
    )
    : backendWarning

  return {
    available: source.available,
    analyzedRowCount: analyzed,
    sourceTotalRowCount: sourceTotal,
    truncated,
    warning,
    readOnly: meta.read_only === true,
  }
}

function identityKey(runId, ticker) {
  const run = positiveInteger(runId)
  const symbol = textOrNull(ticker)?.toUpperCase()
  return run !== null && symbol ? `${run}:${symbol}` : null
}

export function indexRecommendationIdentities(records) {
  const candidates = new Map()
  for (const row of Array.isArray(records) ? records : []) {
    const source = objectOrNull(row)
    const recommendationId = positiveInteger(source?.recommendation_id)
    const key = identityKey(source?.run_id, source?.ticker)
    if (recommendationId === null || !key) continue
    if (!candidates.has(key)) candidates.set(key, new Set())
    candidates.get(key).add(recommendationId)
  }

  const index = new Map()
  for (const [key, recommendationIds] of candidates) {
    if (recommendationIds.size === 1) index.set(key, [...recommendationIds][0])
  }
  return index
}

function emptyBadge(horizonDays, result) {
  return {
    horizonDays,
    label: `${horizonDays}d`,
    status: result,
    result,
    rawReturn: null,
    evaluationAt: null,
  }
}

function latestRow(rows) {
  return rows.length ? rows[rows.length - 1] : null
}

function badgeForHorizon(rows, horizonDays, missingResult) {
  const matching = rows.filter((row) => row.horizonDays === horizonDays)
  const row = latestRow(matching)
  return row
    ? {
        horizonDays,
        label: `${horizonDays}d`,
        status: row.status,
        result: row.result,
        rawReturn: row.rawReturn,
        evaluationAt: row.evaluationAt,
      }
    : emptyBadge(horizonDays, missingResult)
}

export function buildOutcomeEvidence(
  recommendationId,
  outcomeIndex,
  { available = true, incomplete = false } = {},
) {
  const normalizedId = positiveInteger(recommendationId)
  const indexedRows = normalizedId !== null && outcomeIndex instanceof Map
    ? outcomeIndex.get(normalizedId) ?? []
    : []
  const rows = indexedRows.map((row) => ({ ...row }))
  const latest = latestRow(rows)
  const completedRows = rows.filter((row) => row.completed)
  const latestCompleted = latestRow(completedRows)
  const missingResult = available && !incomplete ? 'Not evaluated' : 'Unavailable'
  const sources = [...new Set(rows.map((row) => row.evaluationSource).filter(Boolean))].sort()
  const evaluatedHorizons = [...new Set(
    completedRows.map((row) => row.horizonDays).filter((value) => value !== null),
  )].sort((left, right) => left - right)

  return {
    recommendationId: normalizedId,
    available,
    incomplete,
    hasOutcomes: rows.length > 0,
    outcomeStatus: latest?.status ?? missingResult,
    latestResult: latestCompleted?.result ?? latest?.result ?? missingResult,
    latestCompletedResult: latestCompleted?.result ?? missingResult,
    latestCompletedHorizon: latestCompleted?.horizonDays ?? null,
    latestRawReturn: latestCompleted?.rawReturn ?? null,
    latestEvaluationAt: latest?.evaluationAt ?? null,
    latestCompletedEvaluationAt: latestCompleted?.evaluationAt ?? null,
    entryAt: latestCompleted?.entryAt ?? latest?.entryAt ?? rows.find((row) => row.entryAt)?.entryAt ?? null,
    evaluationSource: sources.length ? sources.join(', ') : null,
    horizonsEvaluated: evaluatedHorizons,
    counts: {
      total: rows.length,
      completed: completedRows.length,
      pending: rows.filter((row) => row.status === 'Pending').length,
      deferred: rows.filter((row) => row.status === 'Deferred').length,
      expired: rows.filter((row) => row.status === 'Expired').length,
    },
    horizonBadges: OUTCOME_HORIZONS.map((horizon) =>
      badgeForHorizon(rows, horizon, missingResult),
    ),
    outcomes: rows,
  }
}

function recordPresence(records) {
  const map = new Map()
  for (const sourceRow of Array.isArray(records) ? records : []) {
    const recommendationId = positiveInteger(sourceRow?.recommendation_id)
    if (recommendationId === null) continue
    const normalized = normalizeOutcomeRow(sourceRow)
    const current = map.get(recommendationId) ?? { hasOutcomes: false, explicitEmpty: false }
    if (normalized?.hasOutcomeEvidence) current.hasOutcomes = true
    else current.explicitEmpty = true
    map.set(recommendationId, current)
  }
  return map
}

export function enrichRecommendationRows(rows, payload) {
  const list = Array.isArray(rows) ? rows : []
  const source = sourceRows(payload)
  const meta = outcomeSourceMeta(payload)
  const outcomeIndex = indexOutcomeRows(source.rows)
  const identityIndex = indexRecommendationIdentities(source.rows)
  const presence = recordPresence(source.rows)

  return list.map((row) => {
    const directId = positiveInteger(row?.recommendationId ?? row?.recommendation_id)
    const matchedId = identityIndex.get(identityKey(row?.runId ?? row?.run_id, row?.ticker)) ?? null
    const recommendationId = directId ?? matchedId
    const recommendationPresence = presence.get(recommendationId)
    const identityAvailable = source.available && recommendationId !== null
    const explicitlyEmpty = Boolean(
      recommendationPresence?.explicitEmpty && !recommendationPresence?.hasOutcomes,
    )
    const incomplete = meta.truncated && !explicitlyEmpty
    return {
      ...row,
      recommendationId,
      outcomeEvidence: buildOutcomeEvidence(recommendationId, outcomeIndex, {
        available: identityAvailable,
        incomplete,
      }),
    }
  })
}

export function buildDrawerOutcomeModel(payload, fallbackEvidence = null, recommendationIdOverride = null) {
  const source = sourceRows(payload)
  const metaRecommendationId = positiveInteger(payload?.meta?.recommendation_id)
  const firstRecommendationId = positiveInteger(source.rows[0]?.recommendation_id)
  const recommendationId =
    metaRecommendationId ??
    firstRecommendationId ??
    positiveInteger(fallbackEvidence?.recommendationId) ??
    positiveInteger(recommendationIdOverride)

  if (source.available && recommendationId !== null) {
    return buildOutcomeEvidence(recommendationId, indexOutcomeRows(source.rows), { available: true })
  }
  if (fallbackEvidence && typeof fallbackEvidence === 'object') {
    return {
      ...fallbackEvidence,
      counts: { ...fallbackEvidence.counts },
      horizonBadges: (fallbackEvidence.horizonBadges ?? []).map((badge) => ({ ...badge })),
      outcomes: (fallbackEvidence.outcomes ?? []).map((row) => ({ ...row })),
    }
  }
  return buildOutcomeEvidence(recommendationId, new Map(), { available: false })
}
