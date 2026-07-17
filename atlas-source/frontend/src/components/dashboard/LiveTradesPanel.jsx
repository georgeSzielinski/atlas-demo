import { memo, useMemo } from 'react'
import Panel from '../ui/Panel'
import StatusPill from '../ui/StatusPill'
import { EmptyState } from '../ui/States'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { formatCurrency } from '../../services/formatters'
import { liveTradeRows, formatClock } from '../../services/paperFundOps'

// Right-rail feed of the latest simulated fills. BUY reads green, SELL reads
// blue (per-order realized P/L is not recorded, so sells stay neutral —
// nothing is inferred).
function LiveTradesPanel() {
  const { data } = useDashboardData()
  const fund = data?.paper_fund ?? {}

  const trades = useMemo(() => liveTradeRows(fund, 12), [fund])

  return (
    <Panel
      eyebrow="Execution"
      title="Live Trades"
      action={<StatusPill status="EVALUATED" label="Simulated only" />}
    >
      {trades.length > 0 ? (
        <ul className="dv2-trades">
          {trades.map((trade) => (
            <li className="dv2-trades__row" key={trade.id}>
              <span
                className={`dv2-trades__side dv2-trades__side--${trade.side === 'BUY' ? 'buy' : 'sell'}`}
              >
                {trade.side}
              </span>
              <span className="dv2-trades__main">
                <span className="dv2-trades__symbol">
                  {trade.quantity} × {trade.ticker}
                </span>
                <span className="dv2-trades__price">
                  @ {formatCurrency(trade.fillPrice)}
                </span>
              </span>
              <span className="dv2-trades__meta">
                <span className="dv2-trades__time">{formatClock(trade.at)}</span>
                <span className="dv2-trades__tag">{String(trade.status).replace(/_/g, ' ')}</span>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState
          title="Waiting for first simulated cycle"
          message="Simulated fills appear here once a paper-fund cycle proposes orders that pass the risk gate. No broker. No real money."
        />
      )}
    </Panel>
  )
}

export default memo(LiveTradesPanel)
