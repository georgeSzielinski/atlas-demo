import { useEffect, useState } from 'react'
import Panel from '../components/ui/Panel'
import StatTile from '../components/ui/StatTile'
import StatusPill from '../components/ui/StatusPill'
import { LoadingState, ErrorState, EmptyState } from '../components/ui/States'
import { getPerformanceLab } from '../services/api'
import {
  asArray,
  formatCurrency,
  formatNumber,
  formatPercent,
  formatSignedPercent,
  isEvaluated,
  sectionReason,
  toneForDelta,
} from '../services/formatters'

// A section may itself be a NOT_EVALUATED wrapper or an EVALUATED metric.
function metric(section, key = 'value', options) {
  if (!section || typeof section !== 'object') {
    return formatNumber(section, options)
  }
  if (section.status === 'NOT_EVALUATED') {
    return 'N/E'
  }
  return formatNumber(section[key], options)
}

// Minimal inline sparkline, matching the app's existing EquityCurve technique.
function Sparkline({ points }) {
  const rows = asArray(points)
  if (rows.length < 2) {
    return null
  }
  const width = 640
  const height = 160
  const values = rows.map((row) => Number(row.portfolio_value ?? 0))
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const step = width / (rows.length - 1)
  const polyline = rows
    .map((row, index) => {
      const value = Number(row.portfolio_value ?? 0)
      const x = index * step
      const y = height - ((value - min) / span) * (height - 20) - 10
      return `${x},${y}`
    })
    .join(' ')

  return (
    <svg aria-label="Equity curve" className="analytics-chart" viewBox={`0 0 ${width} ${height}`}>
      <polyline points={polyline} fill="none" stroke="currentColor" strokeWidth="2" />
    </svg>
  )
}

function NotEvaluated({ section, title = 'Not evaluated' }) {
  return <EmptyState title={title} message={sectionReason(section)} />
}

function PortfolioAnalytics({ portfolio }) {
  const equity = portfolio?.equity_curve
  const risk = portfolio?.risk_adjusted
  const benchmark = portfolio?.benchmark
  const beta = benchmark?.beta

  return (
    <Panel
      eyebrow="Portfolio"
      title="Portfolio Analytics"
      action={<StatusPill status={portfolio?.status ?? 'NOT_EVALUATED'} />}
    >
      <div className="pl-equity">
        <div className="pl-stats">
          <StatTile
            label="Latest Value"
            value={formatCurrency(equity?.latest_value)}
            hint={`from ${formatCurrency(equity?.start_value)}`}
          />
          <StatTile
            label="Cumulative Return"
            value={formatSignedPercent(equity?.cumulative_return)}
            deltaTone={toneForDelta(equity?.cumulative_return)}
          />
          <StatTile
            label="Alpha vs S&P 500"
            value={
              benchmark?.alpha_status === 'EVALUATED'
                ? formatSignedPercent(benchmark?.alpha)
                : 'N/E'
            }
            deltaTone={toneForDelta(benchmark?.alpha)}
          />
          <StatTile
            label="Beta"
            value={beta?.status === 'EVALUATED' ? formatNumber(beta?.value) : 'N/E'}
            hint={beta?.status === 'EVALUATED' ? `${beta?.sample_size} obs` : 'no benchmark series'}
          />
        </div>
        <Sparkline points={equity?.points} />
      </div>

      {isEvaluated(risk) ? (
        <div className="pl-stats pl-stats--wide">
          <StatTile label="Sharpe" value={formatNumber(risk?.sharpe)} />
          <StatTile label="Sortino" value={formatNumber(risk?.sortino)} />
          <StatTile label="Calmar" value={metric(risk?.calmar)} />
          <StatTile label="Volatility" value={formatNumber(risk?.volatility)} />
          <StatTile
            label="Max Drawdown"
            value={formatPercent(risk?.max_drawdown)}
            deltaTone="negative"
          />
          <StatTile label="Best Day" value={formatSignedPercent(risk?.best_day)} deltaTone="positive" />
          <StatTile label="Worst Day" value={formatSignedPercent(risk?.worst_day)} deltaTone="negative" />
        </div>
      ) : (
        <NotEvaluated section={risk} title="Risk metrics not evaluated" />
      )}
    </Panel>
  )
}

function TradeDigest({ label, trade, tone }) {
  if (!trade) {
    return <StatTile label={label} value="N/E" />
  }
  return (
    <StatTile
      label={`${label} · ${trade.ticker ?? '—'}`}
      value={formatCurrency(trade.profit_loss)}
      deltaTone={tone}
      hint={trade.holding_period != null ? `${trade.holding_period}d held` : undefined}
    />
  )
}

function TradeAnalytics({ trade }) {
  if (!isEvaluated(trade)) {
    return (
      <Panel eyebrow="Trades" title="Trade Analytics" action={<StatusPill status="NOT_EVALUATED" />}>
        <NotEvaluated section={trade} />
      </Panel>
    )
  }
  return (
    <Panel
      eyebrow="Trades"
      title="Trade Analytics"
      action={<StatusPill status="EVALUATED" label={`${trade.closed_trades} closed`} />}
    >
      <div className="pl-stats pl-stats--wide">
        <StatTile label="Win Rate" value={formatPercent(trade.win_rate)} hint={`${trade.wins}W / ${trade.losses}L`} />
        <StatTile label="Avg Winner" value={formatCurrency(trade.average_winner)} deltaTone="positive" />
        <StatTile label="Avg Loser" value={formatCurrency(trade.average_loser)} deltaTone="negative" />
        <StatTile label="Profit Factor" value={metric(trade.profit_factor)} />
        <StatTile label="Expectancy" value={formatCurrency(trade.expectancy)} deltaTone={toneForDelta(trade.expectancy)} />
        <StatTile
          label="Avg Holding"
          value={trade.average_holding_period != null ? `${formatNumber(trade.average_holding_period)}d` : 'N/E'}
        />
        <TradeDigest label="Best" trade={trade.best_trade} tone="positive" />
        <TradeDigest label="Worst" trade={trade.worst_trade} tone="negative" />
      </div>
    </Panel>
  )
}

function CommitteeAttribution({ committee }) {
  if (!isEvaluated(committee)) {
    return (
      <Panel eyebrow="Committee" title="Committee Attribution" action={<StatusPill status="NOT_EVALUATED" />}>
        <NotEvaluated section={committee} />
      </Panel>
    )
  }
  const members = asArray(committee.members)
  const rolling = asArray(committee.rolling_accuracy?.points)
  return (
    <Panel
      eyebrow="Committee"
      title="Committee & Strategy Attribution"
      action={<StatusPill status="EVALUATED" label={`${committee.trades_with_votes} trades`} />}
    >
      <div className="dv2-table-wrap">
        <table className="dv2-table">
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Judged</th>
              <th>Correct</th>
              <th>Accuracy</th>
            </tr>
          </thead>
          <tbody>
            {members.map((row) => (
              <tr key={row.member_id}>
                <td>{row.member_name}</td>
                <td>{row.evaluated}</td>
                <td>{row.correct}</td>
                <td className={row.accuracy >= 50 ? 'dv2-table__positive' : 'dv2-table__negative'}>
                  {formatPercent(row.accuracy)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rolling.length > 0 ? (
        <p className="pl-note">
          Rolling accuracy (window {committee.rolling_accuracy?.window}): latest{' '}
          {formatPercent(rolling[rolling.length - 1]?.rolling_accuracy)} over {rolling.length} trades.
        </p>
      ) : null}
      <p className="pl-note pl-note--muted">{committee.note}</p>
    </Panel>
  )
}

function ResearchAttribution({ research }) {
  const signals = asArray(research?.signals)
  return (
    <Panel
      eyebrow="Research"
      title="Research Signal Attribution"
      action={<StatusPill status={research?.status ?? 'NOT_EVALUATED'} />}
    >
      {signals.length === 0 ? (
        <NotEvaluated section={research} />
      ) : (
        <div className="dv2-table-wrap">
          <table className="dv2-table">
            <thead>
              <tr>
                <th>Signal</th>
                <th>Winner Avg</th>
                <th>Loser Avg</th>
                <th>Lift</th>
                <th>Verdict</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((row) => (
                <tr key={row.field}>
                  <td>{row.signal}</td>
                  <td>{row.status === 'EVALUATED' ? formatNumber(row.winner_average) : '—'}</td>
                  <td>{row.status === 'EVALUATED' ? formatNumber(row.loser_average) : '—'}</td>
                  <td className={row.lift > 0 ? 'dv2-table__positive' : 'dv2-table__negative'}>
                    {row.status === 'EVALUATED' ? formatSignedPercent(row.lift) : '—'}
                  </td>
                  <td>
                    <StatusPill
                      status={row.status === 'EVALUATED' ? row.verdict : 'NOT_EVALUATED'}
                      label={row.status === 'EVALUATED' ? row.verdict : 'N/E'}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {research?.status === 'EVALUATED' && research?.note ? (
        <p className="pl-note pl-note--muted">{research.note}</p>
      ) : null}
    </Panel>
  )
}

function PerformanceLab() {
  const [report, setReport] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let isCurrent = true
    async function load() {
      setIsLoading(true)
      try {
        const data = await getPerformanceLab()
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
    return <LoadingState label="Loading Performance Lab…" />
  }
  if (error && !report) {
    return <ErrorState message={error} />
  }

  const notEvaluated = asArray(report?.not_evaluated)

  return (
    <div className="dv2-page pl-page">
      <section className="pl-hero">
        <div>
          <p className="dv2-heading__eyebrow">Performance Lab</p>
          <h2>Why the paper fund makes or loses money</h2>
          <p className="pl-hero__sub">
            Deterministic, read-only attribution over persisted paper evidence. No broker, no real
            money, no trading logic. Insufficient evidence is reported as NOT_EVALUATED, never
            fabricated.
          </p>
        </div>
        <div className="pl-hero__badges">
          <StatusPill status="EVALUATED" label="READ-ONLY" />
          <StatusPill status="EVALUATED" label="DETERMINISTIC" />
          <StatusPill status="RUNNING" label="PAPER ONLY" />
          {report?.demo_data ? <StatusPill status="PARTIAL" label="DEMO DATA" /> : null}
        </div>
      </section>

      <PortfolioAnalytics portfolio={report?.portfolio_analytics} />
      <TradeAnalytics trade={report?.trade_analytics} />
      <div className="dv2-row dv2-row--2">
        <CommitteeAttribution committee={report?.committee_attribution} />
        <ResearchAttribution research={report?.research_attribution} />
      </div>

      {notEvaluated.length > 0 ? (
        <Panel eyebrow="Coverage" title="Not Evaluated">
          <ul className="pl-ne-list">
            {notEvaluated.map((item) => (
              <li key={item.area}>
                <strong>{item.area}</strong>: {item.reason}
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}
    </div>
  )
}

export default PerformanceLab
