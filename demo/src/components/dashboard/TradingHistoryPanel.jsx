import { memo } from 'react'
import Panel from '../ui/Panel'
import LineChart from '../charts/LineChart'
import { EmptyState } from '../ui/States'
import { useDashboardData } from '../../context/DashboardDataProvider'
import {
  formatCurrency,
  formatPercent,
  formatValue,
} from '../../services/formatters'

function shortDate(value) {
  if (!value) return ''
  return String(value).slice(0, 10)
}

function statLabel(stat, suffix = '%') {
  if (!stat || stat.status === 'NOT_EVALUATED') return 'Not enough history'
  return suffix === '$'
    ? formatCurrency(stat.value)
    : formatPercent(stat.value, { fallback: 'Unavailable' })
}

function latestPeriod(section) {
  const items = Array.isArray(section?.items) ? section.items : []
  return items[items.length - 1] ?? null
}

function TradingHistoryPanel() {
  const { data } = useDashboardData()
  const history = data?.paper_fund?.trading_history ?? {}
  const curve = Array.isArray(history.equity_curve) ? history.equity_curve : []
  const chartRows = curve.map((point) => ({
    date: shortDate(point.date),
    value: Number(point.portfolio_value ?? 0),
    cash: Number(point.cash ?? 0),
  })).filter((point) => point.value > 0)
  const stats = history.statistics ?? {}
  const daily = latestPeriod(history.daily_pl)
  const weekly = latestPeriod(history.weekly_pl)
  const monthly = latestPeriod(history.monthly_pl)

  return (
    <Panel eyebrow="Trading History" title="Paper Fund Performance" className="dv2-panel--wide">
      <LineChart
        data={chartRows}
        xKey="date"
        height={220}
        series={[
          { key: 'value', name: 'Portfolio Value', area: true },
          { key: 'cash', name: 'Cash' },
        ]}
        showLegend
        yFormatter={(value) => formatCurrency(value)}
        emptyMessage="Equity and cash history appear after completed paper-fund cycles create snapshots."
      />

      {chartRows.length ? (
        <div className="dv2-history-grid">
          <div>
            <span>Daily P/L</span>
            <strong>{daily ? formatCurrency(daily.pl) : 'Not enough history'}</strong>
            <small>{daily ? formatValue(daily.period) : 'Needs snapshots'}</small>
          </div>
          <div>
            <span>Weekly P/L</span>
            <strong>{weekly ? formatCurrency(weekly.pl) : 'Not enough history'}</strong>
            <small>{weekly ? formatValue(weekly.period) : 'Needs snapshots'}</small>
          </div>
          <div>
            <span>Monthly P/L</span>
            <strong>{monthly ? formatCurrency(monthly.pl) : 'Not enough history'}</strong>
            <small>{monthly ? formatValue(monthly.period) : 'Needs snapshots'}</small>
          </div>
          <div>
            <span>CAGR</span>
            <strong>{statLabel(stats.cagr)}</strong>
            <small>{stats.cagr?.reason ?? 'annualized'}</small>
          </div>
          <div>
            <span>Max Drawdown</span>
            <strong>{statLabel(stats.drawdown)}</strong>
            <small>{stats.drawdown?.reason ?? 'from snapshots'}</small>
          </div>
          <div>
            <span>Win Rate</span>
            <strong>{statLabel(stats.win_rate)}</strong>
            <small>{stats.win_rate?.periods ? `${stats.win_rate.periods} return periods` : stats.win_rate?.reason}</small>
          </div>
          <div>
            <span>Sharpe</span>
            <strong>{stats.sharpe?.status === 'EVALUATED' ? formatValue(stats.sharpe.value) : 'Not enough history'}</strong>
            <small>{stats.sharpe?.reason ?? 'risk-adjusted return'}</small>
          </div>
        </div>
      ) : (
        <EmptyState
          title="No trading history"
          message="Start the live paper fund and let a validated cycle complete. Atlas will not fabricate P/L or risk statistics before snapshots exist."
        />
      )}
    </Panel>
  )
}

export default memo(TradingHistoryPanel)
