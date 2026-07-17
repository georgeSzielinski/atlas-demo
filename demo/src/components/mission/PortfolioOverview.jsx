import { memo } from 'react'
import Panel from '../ui/Panel'
import DonutChart from '../charts/DonutChart'
import MeterBar from '../ui/MeterBar'
import { EmptyState } from '../ui/States'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { portfolioOverview } from '../../services/missionOps'
import { formatCurrency, formatPercent } from '../../services/formatters'

function Metric({ label, value, hint }) {
  return (
    <div className="dv3-portfolio__metric">
      <span className="dv3-portfolio__k">{label}</span>
      <strong className="dv3-portfolio__v">{value}</strong>
      {hint ? <small className="dv3-portfolio__hint">{hint}</small> : null}
    </div>
  )
}

// Row 5 — allocation + cash + sector exposure + largest position. When the fund
// holds no positions we show a deliberate empty state instead of a broken chart.
function PortfolioOverview() {
  const { data } = useDashboardData()
  const view = portfolioOverview(data)

  if (!view.hasPositions) {
    return (
      <Panel eyebrow="Portfolio" title="Portfolio Overview" className="dv2-panel--wide">
        <EmptyState
          title="No open positions"
          message="The paper fund holds no positions yet. Once a simulated cycle allocates capital, allocation, sector exposure and concentration appear here."
        />
      </Panel>
    )
  }

  return (
    <Panel eyebrow="Portfolio" title="Portfolio Overview" className="dv2-panel--wide">
      <div className="dv3-portfolio">
        <div className="dv3-portfolio__chart">
          <DonutChart data={view.allocation} height={240} />
        </div>
        <div className="dv3-portfolio__side">
          <div className="dv3-portfolio__metrics">
            <Metric
              label="Portfolio Value"
              value={view.portfolioValue !== null ? formatCurrency(view.portfolioValue) : '—'}
            />
            <Metric
              label="Cash"
              value={view.cash !== null ? formatCurrency(view.cash) : '—'}
              hint={formatPercent(view.cashReservePercent, { fallback: 'reserve n/a' })}
            />
            <Metric
              label="Largest Position"
              value={view.largestPosition ? view.largestPosition.symbol : '—'}
              hint={
                view.largestPosition
                  ? formatPercent(view.largestPosition.percent, { fallback: 'n/a' })
                  : 'no concentration'
              }
            />
            <Metric
              label="Health Score"
              value={view.healthScore !== null ? `${view.healthScore}` : '—'}
              hint={view.healthStatus ?? 'not scored'}
            />
          </div>

          <div className="dv3-portfolio__sectors">
            <span className="dv3-portfolio__k">Sector Exposure</span>
            {view.sectors.length === 0 ? (
              <small className="dv3-portfolio__hint">No sector data available.</small>
            ) : (
              view.sectors.slice(0, 5).map((sector) => (
                <MeterBar
                  key={sector.name}
                  value={sector.percent ?? 0}
                  tone="accent"
                  label={`${sector.name} · ${formatPercent(sector.percent, { fallback: 'n/a' })}`}
                />
              ))
            )}
          </div>
        </div>
      </div>
    </Panel>
  )
}

export default memo(PortfolioOverview)
