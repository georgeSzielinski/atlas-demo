import { useState } from 'react'

function PaperSimulationControls({ isRunning, message, onReplay, onReset }) {
  const [tickers, setTickers] = useState('AAPL, MSFT')
  const [startDate, setStartDate] = useState('2024-01-02')
  const [endDate, setEndDate] = useState('2024-01-05')
  const [startingCash, setStartingCash] = useState('100000')
  const [allocationPercent, setAllocationPercent] = useState('')

  function runReplay() {
    const payload = {
      tickers: tickers
        .split(',')
        .map((ticker) => ticker.trim().toUpperCase())
        .filter(Boolean),
      start_date: startDate,
      end_date: endDate,
      starting_cash: Number(startingCash) || 100000,
      mode: 'historical_price_replay',
    }
    const allocation = Number(allocationPercent)
    if (allocationPercent !== '' && !Number.isNaN(allocation) && allocation > 0) {
      payload.allocation_percent = allocation
    }
    onReplay(payload)
  }

  return (
    <section className="paper-panel paper-sim-controls">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">HISTORICAL PRICE REPLAY</p>
          <h2>Run Replay From Real OHLCV Rows</h2>
        </div>
        <div className="paper-hero__badges">
          <span>NO REAL MONEY</span>
          <span>NO BROKER CONNECTED</span>
        </div>
      </div>

      <div className="paper-replay-form">
        <label>
          <span>Tickers</span>
          <input
            disabled={isRunning}
            onChange={(event) => setTickers(event.target.value)}
            value={tickers}
          />
        </label>
        <label>
          <span>Start date</span>
          <input
            disabled={isRunning}
            onChange={(event) => setStartDate(event.target.value)}
            type="date"
            value={startDate}
          />
        </label>
        <label>
          <span>End date</span>
          <input
            disabled={isRunning}
            onChange={(event) => setEndDate(event.target.value)}
            type="date"
            value={endDate}
          />
        </label>
        <label>
          <span>Starting cash</span>
          <input
            disabled={isRunning}
            min="1"
            onChange={(event) => setStartingCash(event.target.value)}
            type="number"
            value={startingCash}
          />
        </label>
        <label>
          <span>Allocation % per ticker (blank = equal weight)</span>
          <input
            disabled={isRunning}
            max="100"
            min="1"
            onChange={(event) => setAllocationPercent(event.target.value)}
            placeholder="Equal weight"
            type="number"
            value={allocationPercent}
          />
        </label>
        <button disabled={isRunning} onClick={runReplay} type="button">
          Run Historical Replay
        </button>
      </div>

      <div className="paper-sim-controls__actions">
        <button
          className="paper-sim-controls__reset"
          disabled={isRunning}
          onClick={onReset}
          type="button"
        >
          Reset replay records
        </button>
      </div>
      <p className="paper-sim-controls__message">
        {message || 'Historical replay uses real OHLCV close prices or fails loudly. No demo data exists in Paper Trading.'}
      </p>
    </section>
  )
}

export default PaperSimulationControls
