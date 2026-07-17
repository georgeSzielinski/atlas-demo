// Read-only projection of GET /institutional-report/{ticker} into the drawer's
// view model. Pure functions only: every field is read straight from the report
// payload. The report engine defaults missing fields to '' / 0 / [] /
// 'Unavailable', so we treat those as "not evaluated" and gate each section on
// whether it carries any real signal — analysis is never fabricated.

const UNAVAILABLE = 'Unavailable'

function sectionMap(report) {
  const map = {}
  for (const section of report?.sections ?? []) {
    if (section && section.title) map[section.title] = section
  }
  return map
}

function data(section) {
  return section && typeof section.data === 'object' && section.data !== null
    ? section.data
    : {}
}

// A meaningful string: present and not the engine's Unavailable sentinel.
function text(value) {
  if (value === null || value === undefined) return null
  const str = String(value).trim()
  if (!str || str === UNAVAILABLE) return null
  return str
}

// A meaningful number: present and non-zero (the engine uses 0 as its
// "unavailable" default across scores/confidence).
function score(value) {
  const number = Number(value)
  if (Number.isNaN(number) || number === 0) return null
  return number
}

function list(value) {
  return Array.isArray(value) ? value.filter((item) => item !== null && item !== undefined && item !== '') : []
}

export function buildReportModel(report, card) {
  const sections = sectionMap(report)
  const exec = sections['Executive Summary']
  const rec = data(sections['Recommendation'])
  const confidence = data(sections['Confidence'])
  const committee = data(sections['Investment Committee'])
  const risk = data(sections['Risk Assessment'])
  const technical = data(sections['Technical Analysis'])
  const forecast = data(sections['Forecast Analysis'])
  const fundamental = data(sections['Fundamental Analysis'])
  const sec = data(sections['SEC Highlights'])
  const portfolio = data(sections['Portfolio Impact'])
  const appendix = data(sections['Appendix'])
  const probability = data(sections['Probability Distribution'])

  // Header prefers the committee card the user actually clicked (always
  // present), enriched with report values where the card is silent.
  const action = card?.action ?? text(rec.action) ?? text(data(exec).action)
  const hasRecommendation = Boolean(text(rec.action)) || Boolean(card?.action)

  return {
    ticker: report?.ticker ?? card?.ticker ?? null,
    recommendationId: card?.recommendationId ?? null,
    hasRecommendation,
    header: {
      ticker: report?.ticker ?? card?.ticker ?? null,
      action,
      confidence: card?.confidence ?? score(confidence.confidence) ?? score(data(exec).confidence),
      agreementPct: card?.agreementPct ?? score(committee.agreement),
      strength: card?.strength ?? null,
      generatedAt: report?.metadata?.generation_time ?? null,
    },
    executiveSummary: {
      summary: text(exec?.summary),
      secFilings: score(data(exec).sec_filings),
    },
    thesis: {
      rating: text(rec.rating),
      overallScore: score(rec.overall_score),
      validationStatus: text(rec.validation_status),
      confidenceExplanation: text(sections['Confidence']?.summary),
      signalLabel: text(confidence.signal_label),
      signalQuality: score(confidence.signal_quality_score),
      evidence: list(appendix.evidence_breakdown),
      probabilities: probability,
    },
    bullCase: list(sections['Bull Case']?.data),
    bearCase: list(sections['Bear Case']?.data),
    catalysts: list(sections['Catalyst Timeline']?.data),
    risks: {
      score: score(risk.risk_score),
      items: list(risk.risks),
      falsePositives: list(risk.false_positive_warnings),
    },
    technical: {
      technicalScore: score(technical.technical_score),
      score: score(technical.score),
      forecastDirection: text(forecast.forecast_direction),
      forecastConfidence: score(forecast.forecast_confidence),
      expectedChange: score(forecast.expected_change),
    },
    fundamental: {
      fundamentalScore: score(fundamental.fundamental_score),
      strongestFactor: fundamental.strongest_positive_factor,
      filingCount: score(sec.filing_count),
      formTypeCounts: sec.form_type_counts && typeof sec.form_type_counts === 'object' ? sec.form_type_counts : {},
      sectionCoverage: list(sec.section_coverage),
      secProvider: text(appendix.sec_provider),
    },
    committee: {
      agreement: score(committee.agreement),
      members: [
        ...list(committee.bullish_members).map((m) => ({ name: memberName(m), vote: 'Bullish' })),
        ...list(committee.bearish_members).map((m) => ({ name: memberName(m), vote: 'Bearish' })),
        ...list(committee.neutral_members).map((m) => ({ name: memberName(m), vote: 'Neutral' })),
      ],
      summary: text(sections['Investment Committee']?.summary),
    },
    construction: {
      portfolioScore: score(portfolio.portfolio_score),
      overallConviction: score(portfolio.overall_conviction),
      summary: text(sections['Portfolio Impact']?.summary),
    },
    audit: {
      generatedAt: report?.metadata?.generation_time ?? null,
      reportVersion: report?.metadata?.report_version ?? null,
      dataSources: list(report?.metadata?.data_sources_used),
      activeProviders: list(report?.metadata?.active_providers),
      secProvider: text(appendix.sec_provider),
      policy: report?.policy ?? {},
    },
  }
}

export function voteTone(vote) {
  const key = String(vote ?? '').toLowerCase()
  if (key === 'bullish') return 'positive'
  if (key === 'bearish') return 'negative'
  return 'neutral'
}

function memberName(member) {
  if (typeof member === 'string') return member
  if (member && typeof member === 'object') {
    return member.member_name ?? member.member ?? member.name ?? member.role ?? 'Member'
  }
  return String(member)
}
