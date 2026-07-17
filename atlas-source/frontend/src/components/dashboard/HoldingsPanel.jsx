import { memo, useMemo } from 'react'
import Panel from '../ui/Panel'
import StatusPill from '../ui/StatusPill'
import { EmptyState } from '../ui/States'
import { useDashboardData } from '../../context/DashboardDataProvider'
import {
  formatCurrency,
  formatNumber,
  formatPercent,
} from '../../services/formatters'

function positionValue(position) {
  const value =
    position?.current_value ??
    (Number(position?.quantity ?? 0) * Number(position?.current_price ?? position?.cost_basis ?? 0))
  return Number(value) || 0
}

function unrealized(position) {
  if (position?.unrealized_pl !== null && position?.unrealized_pl !== undefined) {
    return Number(position.unrealized_pl) || 0
  }
  const quantity = Number(position?.quantity ?? 0) || 0
  const price = Number(position?.current_price ?? 0) || 0
  const basis = Number(position?.cost_basis ?? 0) || 0
  return quantity * (price - basis)
}

function HoldingsPanel() {
  const { data } = useDashboardData()
  const fund = data?.paper_fund ?? {}
  const snapshot = fund.latest_snapshot ?? {}
  const portfolioValue = Number(snapshot.portfolio_value ?? 0) || 0

  const rows = useMemo(() => {
    const positions = fund.open_positions ?? {}
    return Object.entries(positions)
      .map(([ticker, position]) => {
        const value = positionValue(position)
        const pl = unrealized(position)
        return {
          ticker,
          quantity: Number(position?.quantity ?? 0) || 0,
          costBasis: position?.cost_basis,
          currentPrice: position?.current_price,
          value,
          weight: portfolioValue > 0 ? value / portfolioValue * 100 : null,
          unrealizedPl: pl,
        }
      })
      .sort((a, b) => b.value - a.value || a.ticker.localeCompare(b.ticker))
  }, [fund.open_positions, portfolioValue])

  const winner = rows.length > 0
    ? rows.reduce((best, row) => (row.unrealizedPl > best.unrealizedPl ? row : best), rows[0])
    : null
  const loser = rows.length > 0
    ? rows.reduce((worst, row) => (row.unrealizedPl < worst.unrealizedPl ? row : worst), rows[0])
    : null

  return (
    <Panel
      eyebrow="Portfolio"
      title="Current Holdings"
      action={<StatusPill status={rows.length > 0 ? 'EVALUATED' : 'NOT_EVALUATED'} label={`${rows.length} holding${rows.length === 1 ? '' : 's'}`} />}
    >
      {rows.length > 0 ? (
        <>
          <div className="dv2-winners">
            <div>
              <span>Largest winner</span>
              <strong>{winner?.ticker ?? 'n/a'}</strong>
              <small>{formatCurrency(winner?.unrealizedPl)}</small>
            </div>
            <div>
              <span>Largest loser</span>
              <strong>{loser?.ticker ?? 'n/a'}</strong>
              <small>{formatCurrency(loser?.unrealizedPl)}</small>
            </div>
          </div>
          <div className="dv2-table-wrap">
            <table className="dv2-table">
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Qty</th>
                  <th>Weight</th>
                  <th>Price</th>
                  <th>Value</th>
                  <th>Unrealized P/L</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.ticker}>
                    <td>{row.ticker}</td>
                    <td>{formatNumber(row.quantity, { digits: 4, fallback: '0' })}</td>
                    <td>{formatPercent(row.weight, { fallback: 'n/a' })}</td>
                    <td>{formatCurrency(row.currentPrice)}</td>
                    <td>{formatCurrency(row.value)}</td>
                    <td className={row.unrealizedPl < 0 ? 'dv2-table__negative' : 'dv2-table__positive'}>
                      {formatCurrency(row.unrealizedPl)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <EmptyState
          title="No holdings yet"
          message="Start the live paper fund from Paper Trading, then run a validated cycle. Holdings appear only after simulated orders pass risk validation."
        />
      )}
    </Panel>
  )
}

export default memo(HoldingsPanel)
