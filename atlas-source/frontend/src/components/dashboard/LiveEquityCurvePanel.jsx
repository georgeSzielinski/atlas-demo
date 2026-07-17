import { memo, useMemo, useState } from 'react'
import Panel from '../ui/Panel'
import LineChart from '../charts/LineChart'
import StatusPill from '../ui/StatusPill'
import { EmptyState } from '../ui/States'
import { CHART_COLORS } from '../charts/chartTheme'
import { useDashboardData } from '../../context/DashboardDataProvider'
import {
  formatCurrency,
  formatSignedPercent,
  toneForDelta,
} from '../../services/formatters'
import { equityCurveRows, dayOf, todayKey } from '../../services/paperFundOps'

const RANGES = [
  { key: '7D', days: 7 },
  { key: '30D', days: 30 },
  { key: 'ALL', days: null },
]

function cutoffKey(days) {
  const date = new Date()
  date.setDate(date.getDate() - days)
  return todayKey(date)
}

// Large central live equity curve: hero portfolio value + return deltas over
// the paper fund's real snapshot history. Line tone follows the sign of total
// return (status encoding); a dashed reference marks starting cash.
function LiveEquityCurvePanel() {
  const { data } = useDashboardData()
  const fund = data?.paper_fund ?? {}
  const snapshot = fund.latest_snapshot ?? {}
  const [range, setRange] = useState('ALL')

  const allRows = useMemo(() => equityCurveRows(fund), [fund])
  const rows = useMemo(() => {
    const selected = RANGES.find((item) => item.key === range)
    if (!selected?.days) return allRows
    const cutoff = cutoffKey(selected.days)
    const filtered = allRows.filter((row) => dayOf(row.at) >= cutoff)
    // A range with under two points can't draw a curve; fall back to ALL.
    return filtered.length >= 2 ? filtered : allRows
  }, [allRows, range])

  const portfolioValue = snapshot.portfolio_value
  const totalReturn = snapshot.total_return
  const dailyReturn = snapshot.daily_return
  const startingCash = Number(fund.starting_cash ?? 0)
  const lineColor = Number(totalReturn) < 0 ? CHART_COLORS.negative : CHART_COLORS.positive

  return (
    <Panel
      eyebrow="Live Paper Equity"
      title="Portfolio Value"
      className="dv2-panel--equity"
      action={
        <div className="dv2-equity__controls">
          {RANGES.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`dv2-chip ${range === item.key ? 'dv2-chip--active' : ''}`}
              onClick={() => setRange(item.key)}
            >
              {item.key}
            </button>
          ))}
          <StatusPill status="EVALUATED" label="PAPER · SIMULATED" />
        </div>
      }
    >
      <div className="dv2-equity__hero">
        <span className="dv2-equity__value">
          {portfolioValue !== null && portfolioValue !== undefined
            ? formatCurrency(portfolioValue)
            : 'Not started'}
        </span>
        <span className={`dv2-stat__delta dv2-stat__delta--${toneForDelta(dailyReturn)}`}>
          {formatSignedPercent(dailyReturn, { fallback: '—' })} cycle
        </span>
        <span className={`dv2-stat__delta dv2-stat__delta--${toneForDelta(totalReturn)}`}>
          {formatSignedPercent(totalReturn, { fallback: '—' })} total
        </span>
      </div>

      {rows.length >= 2 ? (
        <LineChart
          data={rows}
          xKey="date"
          height={260}
          series={[
            { key: 'value', name: 'Portfolio Value', area: true, color: lineColor },
            { key: 'cash', name: 'Cash', color: CHART_COLORS.accent },
          ]}
          showLegend
          yFormatter={(value) => `$${Math.round(value / 1000)}k`}
          referenceLines={startingCash > 0 ? [{ y: startingCash, label: 'Start' }] : []}
        />
      ) : (
        <EmptyState
          title="Waiting for first simulated cycle"
          message="The live equity curve draws from real paper-fund snapshots. It appears after at least two validated cycles complete. No values are simulated ahead of time."
        />
      )}
    </Panel>
  )
}

export default memo(LiveEquityCurvePanel)
