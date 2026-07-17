import { memo, useMemo } from 'react'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { formatCurrency, formatSignedPercent, toneForDelta } from '../../services/formatters'
import { tickerRows } from '../../services/paperFundOps'

function TickerItem({ row }) {
  return (
    <span className="dv2-ticker__item">
      <span className="dv2-ticker__symbol">{row.symbol}</span>
      <span className="dv2-ticker__price">{formatCurrency(row.price)}</span>
      {row.plPercent !== null && row.plPercent !== undefined ? (
        <span className={`dv2-ticker__pl dv2-ticker__pl--${toneForDelta(row.plPercent)}`}>
          {formatSignedPercent(row.plPercent)}
        </span>
      ) : null}
    </span>
  )
}

// Bottom marquee of the last validated prices Atlas actually recorded (latest
// snapshot positions + the newest learning entry's cycle price map). Held
// symbols show unrealized % vs cost basis. When no cycle has produced prices
// the strip is an honest static notice — quotes are never invented.
function MarketTickerStrip() {
  const { data } = useDashboardData()
  const fund = data?.paper_fund ?? {}

  const rows = useMemo(() => tickerRows(fund), [fund])

  if (rows.length === 0) {
    return (
      <div className="dv2-ticker dv2-ticker--empty">
        <span className="dv2-ticker__notice">
          No validated prices yet — the ticker activates after the paper fund&apos;s
          first validated cycle.
        </span>
      </div>
    )
  }

  return (
    <div className="dv2-ticker" aria-label="Last validated watchlist prices">
      <span className="dv2-ticker__badge">LAST CYCLE</span>
      <div className="dv2-ticker__viewport">
        {/* Track duplicated once for a seamless marquee loop. */}
        <div className="dv2-ticker__track">
          {rows.map((row) => <TickerItem row={row} key={`a-${row.symbol}`} />)}
          {rows.map((row) => <TickerItem row={row} key={`b-${row.symbol}`} />)}
        </div>
      </div>
    </div>
  )
}

export default memo(MarketTickerStrip)
