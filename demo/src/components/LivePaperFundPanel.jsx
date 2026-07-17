import { useState } from 'react'
import PaperPnLChart from './PaperPnLChart'

function formatCurrency(value) {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue) || value === null || value === undefined) {
    return 'n/a'
  }

  return new Intl.NumberFormat('en-US', {
    currency: 'USD',
    maximumFractionDigits: 2,
    style: 'currency',
  }).format(numberValue)
}

const STATUS_CLASSES = {
  ERROR: ' paper-policy-pill--danger',
  OFF: ' paper-policy-pill--muted',
  PAUSED: ' paper-policy-pill--muted',
}

function LivePaperFundPanel({ fund, isBusy, message, onStart, onPause, onResume, onStop, onCycle, onReset }) {
  const [watchlist, setWatchlist] = useState('AAPL, MSFT, NVDA, GOOGL')
  const [startingCash, setStartingCash] = useState('100000')
  const [intervalMinutes, setIntervalMinutes] = useState('30')

  const hasFundStatus = fund && typeof fund === 'object'
  const fundStatus = hasFundStatus ? (fund.fund_status ?? 'OFF') : 'UNAVAILABLE'
  const isOff = fundStatus === 'OFF'
  const positions = Object.entries(fund?.open_positions ?? {}).map(([ticker, position]) => ({
    ticker,
    ...position,
  }))
  const orders = fund?.virtual_orders ?? []
  const activity = fund?.activity_log ?? []
  const learning = fund?.learning_log ?? []
  const snapshots = fund?.snapshots ?? []

  function startFund() {
    onStart({
      watchlist: watchlist
        .split(',')
        .map((ticker) => ticker.trim().toUpperCase())
        .filter(Boolean),
      starting_cash: Number(startingCash) || 100000,
      interval_minutes: Number(intervalMinutes) || 30,
    })
  }

  if (!hasFundStatus) {
    return (
      <section className="paper-panel paper-fund-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">LIVE PAPER FUND</p>
            <h2>Continuously Running Paper Fund</h2>
            <p className="muted-copy">
              Simulated execution only. Broker disabled. Real money: No.
            </p>
          </div>
          <span className="paper-policy-pill paper-policy-pill--danger">UNAVAILABLE</span>
        </div>
        <p className="paper-not-price-backed">
          Live paper fund status is unavailable. Confirm the FastAPI backend is running,
          then refresh this page. No real trades can be placed from here.
        </p>
      </section>
    )
  }

  return (
    <section className="paper-panel paper-fund-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">LIVE PAPER FUND</p>
          <h2>Continuously Running Paper Fund</h2>
          <p className="muted-copy">
            Simulated execution only. Broker disabled. Real money: No. Cycles require
            validated real market prices or fail loudly.
          </p>
        </div>
        <span className={`paper-policy-pill${STATUS_CLASSES[fundStatus] ?? ''}`}>{fundStatus}</span>
      </div>

      {fund?.last_error ? (
        <p className="paper-not-price-backed">Last error: {fund.last_error}</p>
      ) : null}

      {isOff ? (
        <div className="paper-replay-form paper-fund-form">
          <p className="muted-copy">
            The live paper fund is OFF. Start it to create a simulated cash
            account and watchlist. It will still wait for validated real market
            prices before any cycle can fill simulated orders.
          </p>
          <label>
            <span>Watchlist</span>
            <input
              disabled={isBusy}
              onChange={(event) => setWatchlist(event.target.value)}
              value={watchlist}
            />
          </label>
          <label>
            <span>Starting cash</span>
            <input
              disabled={isBusy}
              min="1"
              onChange={(event) => setStartingCash(event.target.value)}
              type="number"
              value={startingCash}
            />
          </label>
          <label>
            <span>Update interval (minutes)</span>
            <input
              disabled={isBusy}
              min="1"
              onChange={(event) => setIntervalMinutes(event.target.value)}
              type="number"
              value={intervalMinutes}
            />
          </label>
          <button disabled={isBusy} onClick={startFund} type="button">
            Start Live Paper Fund
          </button>
        </div>
      ) : (
        <>
          <dl className="paper-performance-list">
            <div>
              <dt>Last update</dt>
              <dd>{fund?.last_update ?? 'Never'}</dd>
            </div>
            <div>
              <dt>Next scheduled update</dt>
              <dd>{fund?.next_update ?? 'n/a'}</dd>
            </div>
            <div>
              <dt>Price provider</dt>
              <dd>{fund?.price_provider ?? 'n/a'}</dd>
            </div>
            <div>
              <dt>Virtual cash</dt>
              <dd>{formatCurrency(fund?.cash)}</dd>
            </div>
            <div>
              <dt>Realized P/L</dt>
              <dd>{formatCurrency(fund?.realized_pl)}</dd>
            </div>
            <div>
              <dt>Update interval</dt>
              <dd>{fund?.interval_minutes ? `${fund.interval_minutes} min` : 'n/a'}</dd>
            </div>
          </dl>

          <div className="paper-fund-watchlist" aria-label="Live paper fund watchlist">
            {(fund?.watchlist ?? []).map((ticker) => (
              <span key={ticker}>{ticker}</span>
            ))}
          </div>

          <div className="paper-sim-controls__actions">
            <button disabled={isBusy} onClick={onCycle} type="button">
              Run analysis cycle now
            </button>
            {fundStatus === 'PAUSED' ? (
              <button disabled={isBusy} onClick={onResume} type="button">
                Resume
              </button>
            ) : (
              <button disabled={isBusy} onClick={onPause} type="button">
                Pause
              </button>
            )}
            <button className="paper-sim-controls__reset" disabled={isBusy} onClick={onStop} type="button">
              Stop fund
            </button>
            <button className="paper-sim-controls__reset" disabled={isBusy} onClick={onReset} type="button">
              Reset fund records
            </button>
          </div>
        </>
      )}

      {message ? <p className="paper-sim-controls__message">{message}</p> : null}

      {positions.length > 0 ? (
        <div className="paper-table-wrap">
          <table className="paper-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Quantity</th>
                <th>Cost Basis</th>
                <th>Current Price</th>
                <th>Value</th>
                <th>Unrealized P/L</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((position) => (
                <tr key={position.ticker}>
                  <td>{position.ticker}</td>
                  <td>{position.quantity}</td>
                  <td>{formatCurrency(position.cost_basis)}</td>
                  <td>{formatCurrency(position.current_price)}</td>
                  <td>{formatCurrency(position.current_value)}</td>
                  <td>{formatCurrency(position.unrealized_pl)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        !isOff && <p className="muted-copy">No open paper positions yet.</p>
      )}

      {snapshots.length > 0 ? (
        <PaperPnLChart
          eyebrow="LIVE PAPER FUND P/L"
          history={snapshots}
          pill="SIMULATED ONLY"
          pointsLabel="fund snapshots"
          title="Paper Fund Portfolio Value"
        />
      ) : null}

      {orders.length > 0 ? (
        <div className="paper-table-wrap">
          <table className="paper-table">
            <thead>
              <tr>
                <th>Side</th>
                <th>Ticker</th>
                <th>Qty</th>
                <th>Fill Price</th>
                <th>Status</th>
                <th>Source</th>
                <th>Filled At</th>
              </tr>
            </thead>
            <tbody>
              {orders.slice(0, 10).map((order) => (
                <tr key={order.order_id}>
                  <td>
                    <span className={`paper-action paper-action--${String(order.side).toLowerCase()}`}>
                      {order.side}
                    </span>
                  </td>
                  <td>{order.ticker}</td>
                  <td>{order.quantity}</td>
                  <td>{formatCurrency(order.fill_price)}</td>
                  <td>{order.status}</td>
                  <td>{order.price_source}</td>
                  <td>{order.filled_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        !isOff && <p className="muted-copy">No virtual orders yet.</p>
      )}

      {activity.length > 0 ? (
        <div className="paper-fund-log">
          <h3>Activity Log</h3>
          <ul>
            {activity.slice(0, 10).map((entry, index) => (
              <li key={`${entry.at}-${entry.activity_type}-${index}`}>
                <span>{entry.at}</span>
                <strong>{entry.activity_type}</strong>
                <p>{entry.message}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {learning.length > 0 ? (
        <div className="paper-fund-log">
          <h3>Learning Log</h3>
          <ul>
            {learning.slice(0, 5).map((entry, index) => (
              <li key={`${entry.at}-${index}`}>
                <span>{entry.at}</span>
                <p>{entry.lesson}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}

export default LivePaperFundPanel
