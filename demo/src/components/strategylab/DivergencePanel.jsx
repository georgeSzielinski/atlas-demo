import { memo } from 'react'
import Panel from '../ui/Panel'
import StatusPill from '../ui/StatusPill'
import { EmptyState } from '../ui/States'
import { formatPercent } from '../../services/formatters'

// How each strategy's candidate actions diverge from the named baseline.
function DivergencePanel({ divergence }) {
  const evaluated = divergence?.status === 'EVALUATED'

  return (
    <Panel
      eyebrow="Comparison"
      title="Baseline Divergence"
      action={<StatusPill status={divergence?.status ?? 'NOT_EVALUATED'} />}
    >
      {!evaluated ? (
        <EmptyState
          title="Not evaluated"
          message={divergence?.reason ?? 'Baseline divergence is unavailable.'}
        />
      ) : (
        <div className="dv2-divergence">
          <p className="dv2-compare__note">
            Baseline: <strong>{divergence.baseline_strategy_id}</strong>
          </p>
          {(divergence.rows ?? []).map((row) => (
            <div className="dv2-divergence__row" key={row.strategy_id}>
              <div className="dv2-divergence__head">
                <span className="dv2-divergence__name">{row.strategy_id}</span>
                <span className="dv2-divergence__agreement">
                  {row.agreement_pct !== null && row.agreement_pct !== undefined
                    ? `${formatPercent(row.agreement_pct)} agreement over ${row.compared_tickers} tickers`
                    : 'No comparable tickers'}
                </span>
              </div>
              {(row.divergent_actions ?? []).length > 0 ? (
                <ul className="dv2-divergence__list">
                  {row.divergent_actions.map((item) => (
                    <li key={item.ticker}>
                      {item.ticker}: baseline {item.baseline_action} → {item.strategy_action}
                    </li>
                  ))}
                </ul>
              ) : row.compared_tickers > 0 ? (
                <p className="dv2-compare__note">Fully agrees with the baseline.</p>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </Panel>
  )
}

export default memo(DivergencePanel)
