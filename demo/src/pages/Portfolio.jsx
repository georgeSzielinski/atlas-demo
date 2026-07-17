import { useEffect, useState } from 'react'
import DonutChart from '../components/charts/DonutChart'
import LineChart from '../components/charts/LineChart'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States'
import { getDashboardV2 } from '../services/api'
import {
  formatCurrency,
  formatNumber,
  formatPercent,
  formatSignedPercent,
  toneForDelta,
} from '../services/formatters'

function shortDate(value) {
  if (!value) return ''
  return String(value).slice(0, 10)
}

function positionRows(fund) {
  const snapshot = fund?.latest_snapshot ?? {}
  const portfolioValue = Number(snapshot.portfolio_value ?? 0) || 0
  return Object.entries(fund?.open_positions ?? {}).map(([symbol, position]) => {
    const quantity = Number(position?.quantity ?? 0)
    const price = Number(position?.current_price ?? position?.cost_basis ?? 0)
    const value = Number(position?.current_value ?? quantity * price) || 0
    const basis = Number(position?.cost_basis ?? 0)
    const unrealized = position?.unrealized_pl ?? value - quantity * basis
    return {
      symbol,
      quantity,
      allocation: portfolioValue > 0 ? value / portfolioValue * 100 : null,
      costBasis: basis,
      currentPrice: price,
      currentValue: value,
      unrealized,
      realized: null,
    }
  }).sort((a, b) => b.currentValue - a.currentValue || a.symbol.localeCompare(b.symbol))
}

function sectorRows(portfolio) {
  const items = portfolio?.sector_exposure_summary?.items
  if (!Array.isArray(items)) return []
  return items
    .filter((item) => Number(item.exposure_value ?? item.current_value) > 0)
    .map((item) => ({
      name: item.sector,
      value: Number(item.exposure_value ?? item.current_value),
    }))
}

function cashHistory(fund) {
  const history = fund?.trading_history?.cash_history
  if (!Array.isArray(history)) return []
  return history.map((point) => ({
    date: shortDate(point.date),
    cash: Number(point.cash ?? 0),
  })).filter((point) => point.cash >= 0)
}

function Portfolio() {
  const [data, setData] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let isCurrent = true

    async function loadPortfolio() {
      try {
        const payload = await getDashboardV2()
        if (isCurrent) {
          setData(payload)
          setError('')
        }
      } catch (loadError) {
        if (isCurrent) {
          setError(loadError.message || 'Atlas API is offline.')
        }
      } finally {
        if (isCurrent) {
          setIsLoading(false)
        }
      }
    }

    loadPortfolio()

    return () => {
      isCurrent = false
    }
  }, [])

  const fund = data?.paper_fund ?? {}
  const portfolio = data?.portfolio ?? {}
  const snapshot = fund.latest_snapshot ?? {}
  const rows = positionRows(fund)
  const sectors = sectorRows(portfolio)
  const cashRows = cashHistory(fund)
  const fundStatus = fund.fund_status ?? 'OFF'
  const portfolioValue = snapshot.portfolio_value ?? fund.cash ?? fund.starting_cash
  const cash = snapshot.cash ?? fund.cash
  const invested = snapshot.current_value
  const dailyReturn = snapshot.daily_return
  const totalReturn = snapshot.total_return

  if (isLoading) {
    return <LoadingState label="Loading paper-fund portfolio…" />
  }

  if (error) {
    return <ErrorState message={error} />
  }

  return (
    <div className="portfolio-page portfolio-page--live">
      <section className="portfolio-card-grid" aria-label="Paper fund metrics">
        <article className="portfolio-card portfolio-card--accent">
          <span className="portfolio-card__title">Portfolio Value</span>
          <strong className="portfolio-card__value">{formatCurrency(portfolioValue)}</strong>
          <span className={`portfolio-card__detail portfolio-card__detail--${toneForDelta(totalReturn)}`}>
            {formatSignedPercent(totalReturn, { fallback: 'No return yet' })}
          </span>
        </article>
        <article className="portfolio-card">
          <span className="portfolio-card__title">Cash</span>
          <strong className="portfolio-card__value">{formatCurrency(cash)}</strong>
          <span className="portfolio-card__detail">
            {formatCurrency(invested, { fallback: 'No invested value yet' })} invested
          </span>
        </article>
        <article className="portfolio-card">
          <span className="portfolio-card__title">Daily P/L</span>
          <strong className="portfolio-card__value">{formatSignedPercent(dailyReturn, { fallback: 'Not enough history' })}</strong>
          <span className="portfolio-card__detail">from latest paper snapshot</span>
        </article>
        <article className="portfolio-card portfolio-card--warning">
          <span className="portfolio-card__title">Fund Status</span>
          <strong className="portfolio-card__value">{fundStatus}</strong>
          <span className="portfolio-card__detail">{fund.cycle_state?.state ?? 'Idle'}</span>
        </article>
      </section>

      <section className="portfolio-detail-grid portfolio-detail-grid--live">
        <section className="portfolio-panel portfolio-panel--wide">
          <div className="section-heading">
            <p className="eyebrow">Holdings</p>
            <h2>Current Paper Positions</h2>
          </div>
          {rows.length ? (
            <div className="dv2-table-wrap">
              <table className="dv2-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Shares</th>
                    <th>Allocation</th>
                    <th>Cost Basis</th>
                    <th>Current Price</th>
                    <th>Unrealized P/L</th>
                    <th>Realized P/L</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.symbol}>
                      <td>{row.symbol}</td>
                      <td>{formatNumber(row.quantity, { digits: 4 })}</td>
                      <td>{formatPercent(row.allocation, { fallback: 'n/a' })}</td>
                      <td>{formatCurrency(row.costBasis)}</td>
                      <td>{formatCurrency(row.currentPrice)}</td>
                      <td className={Number(row.unrealized) >= 0 ? 'dv2-table__positive' : 'dv2-table__negative'}>
                        {formatCurrency(row.unrealized)}
                      </td>
                      <td>Not tracked per position</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title="No paper holdings"
              message="Start the live paper fund and let a validated simulated cycle pass risk checks. Holdings will appear here after fills are persisted."
            />
          )}
        </section>

        <section className="portfolio-panel">
          <div className="section-heading">
            <p className="eyebrow">Allocation</p>
            <h2>Sector Exposure</h2>
          </div>
          <DonutChart
            data={sectors}
            emptyMessage={portfolio?.sector_exposure_summary?.reason ?? 'Sector allocation appears when construction or learning metadata includes sector information.'}
          />
        </section>

        <section className="portfolio-panel">
          <div className="section-heading">
            <p className="eyebrow">Liquidity</p>
            <h2>Cash History</h2>
          </div>
          <LineChart
            data={cashRows}
            xKey="date"
            height={240}
            series={[{ key: 'cash', name: 'Cash', area: true }]}
            yFormatter={(value) => formatCurrency(value)}
            emptyMessage="Cash history appears after completed paper-fund snapshots."
          />
        </section>
      </section>
    </div>
  )
}

export default Portfolio
