import { memo, useState } from 'react'
import Panel from '../ui/Panel'
import StatusPill from '../ui/StatusPill'
import MeterBar from '../ui/MeterBar'
import { EmptyState, LoadingState } from '../ui/States'
import { getStrategy } from '../../services/api'
import { useAsyncResource } from '../../services/useAsyncResource'

function titleize(key) {
  return String(key).replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

// Lazy detail block: fetches GET /strategies/{id} only once the card expands.
function StrategyDetail({ strategyId }) {
  const { data, isLoading, error } = useAsyncResource(
    `strategies/${strategyId}`,
    () => getStrategy(strategyId),
  )

  if (isLoading && !data) return <LoadingState label="Loading strategy detail…" />
  if (error && !data) {
    return <EmptyState title="Detail unavailable" message={error.message} />
  }

  const universe = data?.universe_rules ?? {}
  const filters = universe.filters ?? {}

  return (
    <div className="dv2-stratcard__detail">
      <div className="dv2-stratcard__block">
        <span className="dv2-stratcard__block-label">Universe</span>
        <p>
          Source: <strong>{titleize(universe.source ?? 'unknown')}</strong>
          {Array.isArray(universe.tickers) && universe.tickers.length > 0
            ? ` · ${universe.tickers.join(', ')}`
            : ''}
        </p>
        {Object.keys(filters).length > 0 ? (
          <p>
            Filters: {Object.entries(filters)
              .map(([key, value]) => `${titleize(key)} = ${value}`)
              .join(' · ')}
          </p>
        ) : (
          <p>No universe filters.</p>
        )}
      </div>
      <div className="dv2-stratcard__block">
        <span className="dv2-stratcard__block-label">Why this strategy</span>
        <p>{data?.explanation}</p>
      </div>
      <div className="dv2-stratcard__block">
        <span className="dv2-stratcard__block-label">Validation</span>
        <p>
          {data?.valid
            ? 'Spec validates against the registry schema.'
            : `Problems: ${(data?.validation_problems ?? []).join('; ')}`}
          {' · '}hash <code>{String(data?.definition_hash ?? '').slice(0, 16)}</code>
        </p>
      </div>
    </div>
  )
}

// Registry card: identity, scoring weights, risk assumptions, and the
// research-only policy. Expanding fetches the single-strategy endpoint.
function StrategyCard({ strategy }) {
  const [expanded, setExpanded] = useState(false)
  const weights = strategy.scoring_logic?.weights ?? {}
  const bands = strategy.scoring_logic?.action_bands ?? {}
  const assumptions = strategy.risk_assumptions ?? {}
  const policy = strategy.policy ?? {}

  return (
    <Panel
      eyebrow={strategy.strategy_id}
      title={strategy.name}
      className="dv2-stratcard"
      action={
        <div className="dv2-stratcard__badges">
          {strategy.is_baseline ? (
            <StatusPill status="EVALUATED" label="BASELINE" />
          ) : null}
          <StatusPill status="NOT_EVALUATED" label="RESEARCH ONLY" />
        </div>
      }
    >
      <p className="dv2-stratcard__description">{strategy.description}</p>

      <div className="dv2-stratcard__block">
        <span className="dv2-stratcard__block-label">
          Scoring weights · BUY ≥ {bands.buy} · HOLD ≥ {bands.hold}
        </span>
        <div className="dv2-stratcard__weights">
          {Object.entries(weights)
            .sort((a, b) => b[1] - a[1])
            .map(([signal, weight]) => (
              <div className="dv2-stratcard__weight-row" key={signal}>
                <span className="dv2-stratcard__weight-label">{titleize(signal)}</span>
                <div className="dv2-stratcard__weight-track">
                  <MeterBar value={weight * 100} tone="accent" />
                </div>
                <span className="dv2-stratcard__weight-value">
                  {Math.round(weight * 100)}%
                </span>
              </div>
            ))}
        </div>
      </div>

      <div className="dv2-stratcard__block">
        <span className="dv2-stratcard__block-label">Risk assumptions</span>
        <div className="dv2-stratcard__tags">
          {Object.entries(assumptions).map(([key, value]) => (
            <span className="dv2-stratcard__tag" key={key}>
              {titleize(key)}: {String(value)}
            </span>
          ))}
        </div>
      </div>

      <div className="dv2-stratcard__foot">
        <span className="dv2-stratcard__meta">
          Holding: {strategy.expected_holding_period}
          {' · '}No execution: {policy.execution_enabled === false ? 'enforced' : '—'}
        </span>
        <button
          type="button"
          className="dv2-chip"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? 'Hide details' : 'Details'}
        </button>
      </div>

      {expanded ? <StrategyDetail strategyId={strategy.strategy_id} /> : null}
    </Panel>
  )
}

export default memo(StrategyCard)
