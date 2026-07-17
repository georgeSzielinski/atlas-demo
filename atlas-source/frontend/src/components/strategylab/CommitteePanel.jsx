import { memo, useState } from 'react'
import Panel from '../ui/Panel'
import StatusPill from '../ui/StatusPill'
import MeterBar from '../ui/MeterBar'
import { EmptyState, LoadingState, ErrorState } from '../ui/States'
import { getCommitteeMembers, getCommitteeEvaluation } from '../../services/api'
import { useAsyncResource } from '../../services/useAsyncResource'

const ACTION_TONES = {
  BUY: 'positive',
  HOLD: 'neutral',
  AVOID: 'negative',
}

const STRENGTH_TONES = {
  STRONG: 'positive',
  MODERATE: 'neutral',
  WEAK: 'warn',
  SPLIT: 'negative',
  NOT_EVALUATED: 'muted',
}

function titleize(key) {
  return String(key).replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function ActionPill({ action }) {
  if (!action) return <StatusPill status="NOT_EVALUATED" label="ABSTAIN" />
  return (
    <StatusPill status={action} label={action} tone={ACTION_TONES[action] ?? 'neutral'} />
  )
}

// Roster strip: the six research-only members convened from the registry.
function MembersStrip({ roster }) {
  return (
    <div className="dv2-committee__members">
      {(roster?.members ?? []).map((member) => (
        <div className="dv2-committee__member" key={member.member_id}>
          <span className="dv2-committee__member-name">
            {member.name}
            {member.is_baseline ? (
              <StatusPill status="EVALUATED" label="BASELINE" />
            ) : null}
          </span>
          <span className="dv2-committee__member-meta">
            holds {member.expected_holding_period}
          </span>
        </div>
      ))}
    </div>
  )
}

function VotesTable({ votes }) {
  return (
    <div className="dv2-table-wrap">
      <table className="dv2-table">
        <thead>
          <tr>
            <th>Member</th>
            <th>Vote</th>
            <th>Score</th>
            <th>Confidence</th>
            <th>Coverage</th>
            <th>Top Drivers</th>
            <th>Missing Inputs</th>
          </tr>
        </thead>
        <tbody>
          {votes.map((vote) => (
            <tr key={vote.member_id}>
              <td>{vote.member_name}</td>
              <td><ActionPill action={vote.action} /></td>
              <td>{vote.score ?? '—'}</td>
              <td>{vote.confidence ?? '—'}</td>
              <td>{vote.coverage_pct != null ? `${vote.coverage_pct}%` : '—'}</td>
              <td className="dv2-compare__why">
                {(vote.drivers ?? [])
                  .slice(0, 2)
                  .map((driver) => titleize(driver.signal))
                  .join(', ') || '—'}
              </td>
              <td className="dv2-compare__why">
                {(vote.missing_inputs ?? [])
                  .map((signal) => titleize(signal))
                  .join(', ') || 'None'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function EvaluationResult({ result }) {
  const recommendation = result.committee_recommendation ?? {}
  const agreement = result.agreement ?? {}
  const majority = result.majority_report ?? {}
  const minority = result.minority_report ?? {}
  const drivers = result.driver_summary ?? []
  const maxDriver = Math.max(
    1,
    ...drivers.map((item) => Number(item.total_contribution) || 0),
  )

  if (result.status === 'NOT_EVALUATED') {
    return (
      <EmptyState
        title={`${result.ticker ?? 'Ticker'} — NOT EVALUATED`}
        message={result.reason ?? 'The committee could not evaluate this ticker.'}
      />
    )
  }

  return (
    <div className="dv2-committee__result">
      <div className="dv2-committee__consensus">
        <div className="dv2-committee__consensus-main">
          <span className="dv2-committee__ticker">{result.ticker}</span>
          <ActionPill action={recommendation.action} />
          <StatusPill
            status={recommendation.strength}
            label={recommendation.strength}
            tone={STRENGTH_TONES[recommendation.strength] ?? 'neutral'}
          />
        </div>
        <div className="dv2-committee__consensus-stats">
          <span>Agreement <strong>{recommendation.agreement_pct}%</strong></span>
          <span>Weighted confidence <strong>{recommendation.confidence}</strong></span>
          <span>
            Voting {agreement.voting_members}/{(agreement.voting_members ?? 0) + (agreement.abstaining_members ?? 0)}
            {' '}(quorum {agreement.quorum})
          </span>
        </div>
        <p className="dv2-committee__explanation">{recommendation.explanation}</p>
      </div>

      <VotesTable votes={result.votes ?? []} />

      <div className="dv2-committee__reports">
        <div className="dv2-committee__report">
          <span className="dv2-stratcard__block-label">Majority report</span>
          <p>{majority.summary}</p>
        </div>
        <div className="dv2-committee__report">
          <span className="dv2-stratcard__block-label">Minority report</span>
          <p>{minority.summary}</p>
        </div>
      </div>

      {drivers.length > 0 ? (
        <div className="dv2-committee__drivers">
          <span className="dv2-stratcard__block-label">Driver summary</span>
          {drivers.map((item) => (
            <div className="dv2-stratcard__weight-row" key={item.signal}>
              <span className="dv2-stratcard__weight-label">{titleize(item.signal)}</span>
              <div className="dv2-stratcard__weight-track">
                <MeterBar
                  value={(Number(item.total_contribution) || 0) / maxDriver * 100}
                  tone="accent"
                />
              </div>
              <span className="dv2-stratcard__weight-value">{item.members}×</span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}

// Investment Committee: convene the six research-only registry strategies on
// one ticker's latest stored recommendation. Read-only — no trading actions,
// no activation, no broker, no real money.
function CommitteePanel() {
  const roster = useAsyncResource('committee/members', getCommitteeMembers)
  const [ticker, setTicker] = useState('')
  const [result, setResult] = useState(null)
  const [isEvaluating, setIsEvaluating] = useState(false)
  const [error, setError] = useState(null)

  const cleanTicker = ticker.trim().toUpperCase()
  const isValid = /^[A-Z][A-Z0-9.-]{0,9}$/.test(cleanTicker)

  async function handleSubmit(event) {
    event.preventDefault()
    if (!isValid || isEvaluating) return
    setIsEvaluating(true)
    setError(null)
    try {
      setResult(await getCommitteeEvaluation(cleanTicker))
    } catch (requestError) {
      setError(requestError)
      setResult(null)
    } finally {
      setIsEvaluating(false)
    }
  }

  return (
    <Panel
      eyebrow="Committee"
      title="Investment Committee"
      className="dv2-panel--wide"
      action={
        <div className="dv2-lab__policy">
          <StatusPill status="NOT_EVALUATED" label="RESEARCH ONLY" />
          <StatusPill status="EVALUATED" label="NO BROKER" />
          <StatusPill status="EVALUATED" label="NO REAL MONEY" />
        </div>
      }
    >
      {roster.isLoading && !roster.data ? (
        <LoadingState label="Convening committee members…" />
      ) : roster.error && !roster.data ? (
        <ErrorState message={roster.error.message} />
      ) : (
        <>
          <p className="dv2-committee__intro">
            Six deterministic registry strategies vote on a ticker&apos;s latest
            stored recommendation. Quorum {roster.data?.quorum}; ties resolve to
            the most conservative action. No orders are ever created.
          </p>
          <MembersStrip roster={roster.data} />
        </>
      )}

      <form className="dv2-committee__form" onSubmit={handleSubmit}>
        <input
          className="dv2-committee__input"
          value={ticker}
          onChange={(event) => setTicker(event.target.value)}
          placeholder="Ticker, e.g. AAPL"
          aria-label="Ticker to evaluate"
          maxLength={10}
        />
        <button
          className="dv2-button"
          type="submit"
          disabled={!isValid || isEvaluating}
        >
          {isEvaluating ? 'Convening…' : 'Convene committee'}
        </button>
      </form>

      {error ? <ErrorState message={error.message} /> : null}
      {isEvaluating ? <LoadingState label={`Evaluating ${cleanTicker}…`} /> : null}
      {!isEvaluating && result ? <EvaluationResult result={result} /> : null}
      {!isEvaluating && !result && !error ? (
        <EmptyState
          title="No evaluation yet"
          message="Enter a ticker to convene the committee on its latest stored recommendation. If none exists, the committee reports NOT_EVALUATED — data is never fabricated."
        />
      ) : null}
    </Panel>
  )
}

export default memo(CommitteePanel)
