import { memo, useMemo } from 'react'
import StatTile from '../ui/StatTile'
import { useDashboardData } from '../../context/DashboardDataProvider'
import {
  formatCurrency,
  formatSignedPercent,
  toneForDelta,
} from '../../services/formatters'
import { deriveTodayTrades } from '../../services/paperFundOps'

function countPositions(openPositions) {
  if (!openPositions || typeof openPositions !== 'object') return 0
  return Object.keys(openPositions).length
}

// Live paper-fund operating KPIs, useful even when downstream analytics are
// NOT_EVALUATED. Everything here reads from paper_fund + risk in the payload.
function LiveOpsTiles() {
  const { data } = useDashboardData()
  const fund = data?.paper_fund ?? {}
  const risk = data?.risk ?? {}
  const snapshot = fund.latest_snapshot ?? {}

  const today = useMemo(() => deriveTodayTrades(fund, risk), [fund, risk])

  const fundStatus = fund.fund_status ?? 'OFF'
  const portfolioValue = snapshot.portfolio_value ?? fund.cash ?? fund.starting_cash
  const portfolioLabel =
    portfolioValue === null || portfolioValue === undefined
      ? fundStatus === 'OFF' ? 'Not started' : 'Unavailable'
      : formatCurrency(portfolioValue)
  const cash = snapshot.cash ?? fund.cash
  const realized = snapshot.realized_pl ?? fund.realized_pl
  const unrealized = snapshot.unrealized_pl
  const dailyReturn = snapshot.daily_return
  const positions = countPositions(fund.open_positions)

  return (
    <>
      <div className="dv2-row dv2-row--4">
        <StatTile
          label="Portfolio Value"
          value={portfolioLabel}
          delta={formatSignedPercent(snapshot.total_return)}
          deltaTone={toneForDelta(snapshot.total_return)}
          hint="total return"
        />
        <StatTile
          label="Cash Balance"
          value={formatCurrency(cash)}
          hint={`${positions} open position${positions === 1 ? '' : 's'}`}
        />
        <StatTile
          label="Daily Return"
          value={formatSignedPercent(dailyReturn)}
          deltaTone={toneForDelta(dailyReturn)}
          hint="since last cycle"
        />
        <StatTile
          label="Realized / Unrealized P&L"
          value={formatCurrency(realized)}
          delta={
            unrealized === undefined || unrealized === null
              ? undefined
              : `${Number(unrealized) >= 0 ? '+' : ''}${formatCurrency(unrealized)} unreal.`
          }
          deltaTone={toneForDelta(unrealized)}
          hint="realized"
        />
      </div>

      <div className="dv2-row dv2-row--4">
        <StatTile
          label="Today's Simulated Trades"
          value={String(today.simulated)}
          hint="filled today"
        />
        <StatTile
          label="Today's Approved"
          value={String(today.approved)}
          deltaTone="positive"
          hint={today.hasRiskData ? 'risk gate passed' : 'no risk decisions yet'}
        />
        <StatTile
          label="Today's Rejected"
          value={String(today.rejected)}
          deltaTone={today.rejected > 0 ? 'negative' : 'neutral'}
          hint="blocked by risk gate"
        />
        <StatTile
          label="Open Positions"
          value={String(positions)}
          hint={fund.watchlist ? `${(fund.watchlist || []).length} on watchlist` : 'holdings'}
        />
      </div>
    </>
  )
}

export default memo(LiveOpsTiles)
