import { useEffect, useState } from 'react'
import Panel from '../components/ui/Panel'
import StatTile from '../components/ui/StatTile'
import StatusPill from '../components/ui/StatusPill'
import { LoadingState, ErrorState, EmptyState } from '../components/ui/States'
import { getSelfImprovement } from '../services/api'
import { asArray, formatPercent } from '../services/formatters'

const DOMAIN_LABELS = {
  strategy_performance: 'Strategy Performance',
  committee_performance: 'Committee Performance',
  signal_predictive_power: 'Signal Predictive Power',
  sector_performance: 'Sector Performance',
  regime_performance: 'Market Regime Performance',
  portfolio_construction: 'Portfolio Construction',
  risk_decisions: 'Risk Decisions',
  drawdowns: 'Drawdowns',
  trade_quality: 'Winning vs Losing Trades',
}

function domainLabel(key) {
  return DOMAIN_LABELS[key] ?? String(key ?? '').replace(/_/g, ' ')
}

function confidenceTone(label) {
  if (label === 'High') return 'positive'
  if (label === 'Moderate') return 'warn'
  return 'muted'
}

// A finding's statistics is a free-form bag of supporting numbers. Show the
// scalar (non-object, non-array) members deterministically in key order so the
// evidence is visible without hard-coding every domain's shape.
function scalarStatistics(statistics) {
  if (!statistics || typeof statistics !== 'object') {
    return []
  }
  return Object.entries(statistics).filter(([, value]) => {
    return value !== null && typeof value !== 'object'
  })
}

function humanizeKey(key) {
  return String(key).replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

function FindingCard({ finding }) {
  const stats = scalarStatistics(finding.statistics)
  const confidencePercent = formatPercent((finding.confidence ?? 0) * 100)

  return (
    <Panel
      eyebrow={domainLabel(finding.category)}
      title={finding.title}
      action={
        <div className="si-badges">
          <StatusPill status={finding.confidence_label} tone={confidenceTone(finding.confidence_label)} label={`${finding.confidence_label} · ${confidencePercent}`} />
          <span className="si-chip">n = {finding.sample_size}</span>
        </div>
      }
    >
      <p className="si-explanation">{finding.explanation}</p>

      {stats.length > 0 ? (
        <div className="si-stats">
          {stats.map(([key, value]) => (
            <StatTile key={key} label={humanizeKey(key)} value={String(value)} />
          ))}
        </div>
      ) : null}

      <div className="si-reco">
        <span className="si-reco__tag">Research opportunity</span>
        <p className="si-reco__text">{finding.recommendation}</p>
      </div>
    </Panel>
  )
}

function CoveragePanel({ notEvaluated }) {
  const rows = asArray(notEvaluated)
  if (rows.length === 0) {
    return null
  }
  return (
    <Panel eyebrow="Coverage" title="Not Evaluated" action={<StatusPill status="NOT_EVALUATED" label={`${rows.length} domains`} />}>
      <ul className="si-ne-list">
        {rows.map((item) => (
          <li key={item.domain}>
            <strong>{domainLabel(item.domain)}</strong>: {item.reason}
          </li>
        ))}
      </ul>
    </Panel>
  )
}

function SelfImprovement() {
  const [report, setReport] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let isCurrent = true
    async function load() {
      setIsLoading(true)
      try {
        const data = await getSelfImprovement()
        if (!isCurrent) return
        setReport(data)
        setError('')
      } catch (requestError) {
        if (!isCurrent) return
        setError(requestError.message)
        setReport(null)
      } finally {
        if (isCurrent) setIsLoading(false)
      }
    }
    load()
    return () => {
      isCurrent = false
    }
  }, [])

  if (isLoading && !report) {
    return <LoadingState label="Loading Self-Improvement Engine…" />
  }
  if (error && !report) {
    return <ErrorState message={error} />
  }

  const findings = asArray(report?.findings)
  const counts = report?.source_counts ?? {}

  return (
    <div className="dv2-page si-page">
      <section className="si-hero">
        <div>
          <p className="dv2-heading__eyebrow">Self-Improvement Engine</p>
          <h2>Evidence-backed research opportunities</h2>
          <p className="si-hero__sub">
            Deterministic analysis of historical evidence that proposes what to research next. It
            never changes strategies, weights, the committee, risk limits, or trading behavior, calls
            no LLM, and uses no randomness. Domains without enough evidence are reported as
            NOT_EVALUATED, never fabricated.
          </p>
          {report?.headline ? <p className="si-headline">{report.headline}</p> : null}
        </div>
        <div className="si-hero__badges">
          <StatusPill status="EVALUATED" label="RESEARCH-ONLY" />
          <StatusPill status="EVALUATED" label="DETERMINISTIC" />
          <StatusPill status="NOT_EVALUATED" label="NO LLM" />
          <StatusPill status="RUNNING" label="NO LIVE CHANGES" />
        </div>
      </section>

      <div className="si-summary">
        <StatTile label="Opportunities" value={String(findings.length)} />
        <StatTile label="Closed Trades" value={String(counts.closed_trades ?? 0)} />
        <StatTile label="Risk Decisions" value={String(counts.risk_decisions ?? 0)} />
        <StatTile label="Construction Reports" value={String(counts.construction_reports ?? 0)} />
      </div>

      {findings.length === 0 ? (
        <Panel eyebrow="Findings" title="Research Opportunities" action={<StatusPill status="NOT_EVALUATED" />}>
          <EmptyState
            title="No opportunities yet"
            message="Not enough historical evidence has accumulated to propose a research opportunity. Run more paper-fund cycles and check back."
          />
        </Panel>
      ) : (
        <div className="si-findings">
          {findings.map((finding) => (
            <FindingCard key={finding.id} finding={finding} />
          ))}
        </div>
      )}

      <CoveragePanel notEvaluated={report?.not_evaluated} />
    </div>
  )
}

export default SelfImprovement
