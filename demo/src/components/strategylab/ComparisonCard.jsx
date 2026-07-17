import { memo } from 'react'
import Panel from '../ui/Panel'
import StatusPill from '../ui/StatusPill'
import { EmptyState } from '../ui/States'
import { formatCurrency, formatPercent } from '../../services/formatters'

const ACTION_TONES = {
  BUY: 'positive',
  HOLD: 'neutral',
  AVOID: 'negative',
  EXCLUDED: 'muted',
}

function titleize(key) {
  return String(key).replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function CandidatesTable({ candidates }) {
  if (!candidates.length) {
    return <EmptyState title="No candidates" message="This strategy produced no candidates." />
  }
  return (
    <div className="dv2-table-wrap">
      <table className="dv2-table">
        <thead>
          <tr>
            <th>Ticker</th>
            <th>Action</th>
            <th>Score</th>
            <th>Coverage</th>
            <th>Why</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((candidate) => (
            <tr key={candidate.ticker}>
              <td>{candidate.ticker}</td>
              <td>
                {candidate.action ? (
                  <StatusPill
                    status={candidate.action}
                    label={candidate.action}
                    tone={ACTION_TONES[candidate.action] ?? 'neutral'}
                  />
                ) : (
                  <StatusPill status="NOT_EVALUATED" label="NOT EVALUATED" />
                )}
              </td>
              <td>{candidate.score ?? '—'}</td>
              <td>{formatPercent(candidate.coverage_pct, { fallback: '—' })}</td>
              <td className="dv2-compare__why">
                {candidate.reason ?? candidate.explanation}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function PortfolioFit({ fit }) {
  if (!fit || fit.status !== 'EVALUATED') {
    return (
      <p className="dv2-compare__na">
        <StatusPill status="NOT_EVALUATED" label="NOT EVALUATED" />{' '}
        {fit?.reason ?? 'Portfolio fit unavailable.'}
      </p>
    )
  }
  const rows = fit.suggested_allocations ?? []
  return (
    <div className="dv2-table-wrap">
      <table className="dv2-table">
        <thead>
          <tr>
            <th>Ticker</th>
            <th>Suggested</th>
            <th>Current</th>
            <th>Capital</th>
            <th>Held</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.ticker}>
              <td>{row.ticker}</td>
              <td>{formatPercent(row.suggested_allocation, { fallback: '—' })}</td>
              <td>{formatPercent(row.current_allocation, { fallback: '—' })}</td>
              <td>{formatCurrency(row.capital_required, { fallback: '—' })}</td>
              <td>{row.already_held ? 'Yes' : 'No'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ExpectedRisks({ risks }) {
  if (!risks) return null
  return (
    <div className="dv2-compare__risks">
      {(risks.limit_checks ?? []).map((check) => (
        <span
          className={`dv2-stratcard__tag dv2-stratcard__tag--${check.within_limit ? 'ok' : 'breach'}`}
          key={check.assumption}
        >
          {titleize(check.assumption)}: {check.assumed} vs limit {check.risk_limit}
          {check.within_limit ? ' ✓' : ' ✗'}
        </span>
      ))}
      {(risks.notes ?? []).map((note) => (
        <p className="dv2-compare__note" key={note}>{note}</p>
      ))}
      {risks.correlation?.status === 'NOT_EVALUATED' ? (
        <p className="dv2-compare__na">
          <StatusPill status="NOT_EVALUATED" label="Correlation" />{' '}
          {risks.correlation.reason}
        </p>
      ) : null}
    </div>
  )
}

// One strategy's on-demand comparison result: status + reason, candidates,
// portfolio fit, expected risks, and top scoring drivers.
function ComparisonCard({ result }) {
  const drivers = result.explainability?.top_drivers ?? []
  const missingTickers = result.explainability?.missing_tickers ?? []

  return (
    <Panel
      eyebrow={result.strategy_id}
      title={result.name}
      className="dv2-compare"
      action={<StatusPill status={result.status} />}
    >
      {result.reason ? (
        <p className="dv2-compare__reason">{result.reason}</p>
      ) : null}

      {result.status === 'NOT_EVALUATED' ? (
        <EmptyState
          title="Not evaluated"
          message={result.reason ?? 'Inputs for this strategy are missing.'}
        />
      ) : (
        <>
          <span className="dv2-stratcard__block-label">Candidate recommendations</span>
          <CandidatesTable candidates={result.candidates ?? []} />

          <span className="dv2-stratcard__block-label">Portfolio fit (dry run)</span>
          <PortfolioFit fit={result.portfolio_fit} />

          <span className="dv2-stratcard__block-label">Expected risks (advisory)</span>
          <ExpectedRisks risks={result.expected_risks} />

          {drivers.length > 0 ? (
            <p className="dv2-compare__drivers">
              Top drivers:{' '}
              {drivers.map((driver) => titleize(driver.signal)).join(' · ')}
            </p>
          ) : null}
          {missingTickers.length > 0 ? (
            <p className="dv2-compare__note">
              No stored recommendation record for: {missingTickers.join(', ')}.
            </p>
          ) : null}
        </>
      )}
    </Panel>
  )
}

export default memo(ComparisonCard)
