import { useEffect, useState } from 'react'
import LivePaperFundPanel from '../components/LivePaperFundPanel'
import PaperLearningCard from '../components/PaperLearningCard'
import PaperPerformanceCard from '../components/PaperPerformanceCard'
import PaperPnLChart from '../components/PaperPnLChart'
import PaperPortfolioSummary from '../components/PaperPortfolioSummary'
import PaperSimulationControls from '../components/PaperSimulationControls'
import PaperTradesTable from '../components/PaperTradesTable'
import PaperTradingStatusCard from '../components/PaperTradingStatusCard'
import {
  getPaperBrokerStatus,
  getPaperFundStatus,
  getPaperPerformance,
  getPaperPortfolio,
  getPaperReplayHealth,
  getPaperTrades,
  getPaperTradingStatus,
  pausePaperFund,
  resetPaperFund,
  resetPaperSimulation,
  resumePaperFund,
  runPaperFundCycle,
  runPaperReplay,
  startPaperFund,
  stopPaperFund,
} from '../services/api'

function latestPerformance(performancePayload) {
  const reports = performancePayload?.paper_performance_reports

  if (!Array.isArray(reports) || reports.length === 0) {
    return {}
  }

  return reports[0]?.performance ?? {}
}

async function safeLoad(loader, fallback) {
  try {
    return await loader()
  } catch {
    return fallback
  }
}

function PaperTrading() {
  const [paperData, setPaperData] = useState({
    broker: null,
    fund: null,
    health: null,
    performance: null,
    portfolio: null,
    status: null,
    trades: null,
  })
  const [isLoading, setIsLoading] = useState(true)
  const [isReplayRunning, setIsReplayRunning] = useState(false)
  const [isFundBusy, setIsFundBusy] = useState(false)
  const [error, setError] = useState('')
  const [replayMessage, setReplayMessage] = useState('')
  const [fundMessage, setFundMessage] = useState('')
  const [lastReplay, setLastReplay] = useState(null)

  useEffect(() => {
    let isCurrent = true

    loadPaperTrading(isCurrent)

    return () => {
      isCurrent = false
    }
  }, [])

  async function loadPaperTrading(isCurrent = true) {
    try {
      const [portfolio, trades, performance, status, health, broker, fund] = await Promise.all([
        safeLoad(getPaperPortfolio, {}),
        safeLoad(getPaperTrades, { paper_trades: [] }),
        safeLoad(getPaperPerformance, { paper_performance_reports: [] }),
        safeLoad(getPaperTradingStatus, null),
        safeLoad(getPaperReplayHealth, null),
        safeLoad(getPaperBrokerStatus, null),
        safeLoad(getPaperFundStatus, null),
      ])

      if (isCurrent) {
        setPaperData({ broker, fund, health, performance, portfolio, status, trades })
        setError('')
      }
    } catch {
      if (isCurrent) {
        setError('Paper trading data is unavailable. Start the FastAPI backend and refresh this page.')
      }
    } finally {
      if (isCurrent) {
        setIsLoading(false)
      }
    }
  }

  async function handleRunReplay(payload) {
    setIsReplayRunning(true)
    setReplayMessage('Running historical price replay from real OHLCV rows...')

    try {
      const result = await runPaperReplay(payload)
      setLastReplay(result)
      await loadPaperTrading(true)
      const audit = result.audit ?? result.replay?.audit ?? {}
      if (result.price_backed) {
        setReplayMessage(
          `Replay ${audit.replay_id ?? 'complete'} COMPLETED. Price-backed by ${audit.rows_used_count ?? 0} real rows (${audit.first_price_date ?? '?'} to ${audit.last_price_date ?? '?'}). Source: ${audit.price_source ?? 'unknown'}. NO REAL MONEY. NO BROKER CONNECTED.`,
        )
      } else {
        setReplayMessage(
          `Replay FAILED — NOT PRICE BACKED. ${result.error || audit.failure_reason || 'Historical prices unavailable'}. No fake P/L, trades, or chart were produced.`,
        )
      }
    } catch (requestError) {
      setLastReplay(null)
      setReplayMessage(
        `${requestError.message || 'Historical replay failed.'} No trades were executed.`,
      )
    } finally {
      setIsReplayRunning(false)
    }
  }

  async function handleFundAction(action, successMessage) {
    setIsFundBusy(true)

    try {
      const result = await action()
      await loadPaperTrading(true)
      const cycle = result?.cycle
      if (cycle && cycle.cycle_status === 'FAILED') {
        setFundMessage(`Cycle FAILED: ${cycle.error}`)
      } else if (cycle) {
        setFundMessage(
          `Cycle ${cycle.cycle_id} completed: ${cycle.orders.length} simulated orders filled from ${cycle.price_provider}. Next update ${cycle.next_update}. NO REAL MONEY.`,
        )
      } else {
        setFundMessage(successMessage)
      }
    } catch (requestError) {
      setFundMessage(requestError.message || 'Live paper fund request failed. No real trades were executed.')
    } finally {
      setIsFundBusy(false)
    }
  }

  async function handleResetReplays() {
    setIsReplayRunning(true)
    setReplayMessage('')

    try {
      await resetPaperSimulation()
      setLastReplay(null)
      await loadPaperTrading(true)
      setReplayMessage('Replay records cleared. Paper Trading is back to its empty setup state.')
    } catch {
      setReplayMessage('Reset failed. No trades were executed.')
    } finally {
      setIsReplayRunning(false)
    }
  }

  if (isLoading) {
    return <section className="dashboard-state">Loading paper trading dashboard...</section>
  }

  if (error) {
    return <section className="dashboard-state dashboard-state--error">{error}</section>
  }

  const replayAudit = lastReplay ? (lastReplay.audit ?? lastReplay.replay?.audit ?? null) : null
  const lastReplayFailed = lastReplay != null && lastReplay.price_backed === false
  const health = paperData.health
  const broker = paperData.broker
  const status = paperData.status
  const portfolio = paperData.portfolio?.latest_portfolio
  const trades = paperData.trades?.paper_trades ?? []
  const performance = latestPerformance(paperData.performance)
  const history = paperData.portfolio?.portfolio_history ?? []
  const hasReplayData = Boolean(portfolio) && history.length > 0
  const fundStatus = paperData.fund?.fund_status ?? (paperData.fund ? 'OFF' : 'UNAVAILABLE')
  const replayEmptyMessage = lastReplayFailed
    ? 'The last replay failed because price-backed data was unavailable. No fake P/L, trades, or chart were produced.'
    : 'No historical replay has run yet. Use the replay form above to test Atlas against real historical OHLCV prices.'

  const healthPanel = health ? (
    <div className="paper-health-list" aria-label="Historical data source health">
      <span className={health.yfinance_installed ? 'paper-health-item' : 'paper-health-item paper-health-item--bad'}>
        yfinance installed: {health.yfinance_installed ? 'true' : 'false'}
      </span>
      <span className={health.historical_provider_available ? 'paper-health-item' : 'paper-health-item paper-health-item--bad'}>
        historical provider available: {health.historical_provider_available ? 'true' : 'false'}
      </span>
      {health.last_error ? (
        <span className="paper-health-item paper-health-item--bad">Last error: {health.last_error}</span>
      ) : null}
      {(health.how_to_fix ?? []).map((fix) => (
        <span className="paper-health-item paper-health-item--fix" key={fix}>How to fix: {fix}</span>
      ))}
    </div>
  ) : null

  const auditPanel = replayAudit ? (
    <section className={`paper-panel paper-replay-audit${replayAudit.price_backed ? '' : ' paper-replay-audit--failed'}`}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">HISTORICAL PRICE REPLAY</p>
          <h2>Replay Audit Trail</h2>
        </div>
        <span className={`paper-policy-pill${replayAudit.price_backed ? '' : ' paper-policy-pill--danger'}`}>
          {replayAudit.price_backed ? 'PRICE BACKED' : 'NOT PRICE BACKED'}
        </span>
      </div>
      {!replayAudit.price_backed ? (
        <p className="paper-not-price-backed">
          FAILED — {replayAudit.failure_reason || lastReplay.error || 'Historical prices unavailable'}.
          No fake P/L, trades, or chart were produced.
        </p>
      ) : null}
      <dl className="paper-audit-list">
        {[
          ['Replay ID', replayAudit.replay_id ?? 'n/a'],
          ['Mode', replayAudit.mode ?? 'n/a'],
          ['Requested Tickers', (replayAudit.requested_tickers ?? []).join(', ') || 'n/a'],
          ['Date Range', `${replayAudit.start_date ?? '?'} → ${replayAudit.end_date ?? '?'}`],
          ['Price Source', replayAudit.price_source ?? 'unavailable'],
          ['Price Backed', replayAudit.price_backed ? 'true' : 'false'],
          ['Fallback Used', replayAudit.fallback_used ? 'true' : 'false'],
          ['Rows Used', replayAudit.rows_used_count ?? 0],
          ['First Price Date', replayAudit.first_price_date ?? 'n/a'],
          ['Last Price Date', replayAudit.last_price_date ?? 'n/a'],
          ['Trades Generated', replayAudit.trades_generated ?? 0],
          ['Portfolio Points', replayAudit.portfolio_points_generated ?? 0],
        ].map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{String(value)}</dd>
          </div>
        ))}
      </dl>
      {Array.isArray(replayAudit.price_rows_used) && replayAudit.price_rows_used.length > 0 ? (
        <div className="paper-table-wrap">
          <table className="paper-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Ticker</th>
                <th>Open</th>
                <th>High</th>
                <th>Low</th>
                <th>Close</th>
                <th>Volume</th>
              </tr>
            </thead>
            <tbody>
              {replayAudit.price_rows_used.map((row, index) => (
                <tr key={`${row.date}-${row.ticker}-${index}`}>
                  <td>{row.date}</td>
                  <td>{row.ticker}</td>
                  <td>{row.open}</td>
                  <td>{row.high}</td>
                  <td>{row.low}</td>
                  <td>{row.close}</td>
                  <td>{row.volume}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted-copy">No price rows were used — the replay was not price-backed.</p>
      )}
    </section>
  ) : null

  const brokerPanel = (
    <section className="paper-panel paper-broker-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">BROKER PAPER TRADING</p>
          <h2>Alpaca Paper — Coming Later</h2>
        </div>
        <span className="paper-policy-pill paper-policy-pill--muted">DISABLED</span>
      </div>
      <p className="muted-copy">
        {broker?.message ?? 'Broker paper trading is future architecture only. No orders can be placed and no real money is involved.'}
      </p>
      <dl className="paper-performance-list">
        <div>
          <dt>Provider</dt>
          <dd>{broker?.provider ?? 'alpaca_paper'}</dd>
        </div>
        <div>
          <dt>Supported</dt>
          <dd>{String(broker?.broker_paper_supported ?? 'pending')}</dd>
        </div>
        <div>
          <dt>Configured</dt>
          <dd>{broker?.configured ? 'Yes' : 'No'}</dd>
        </div>
        <div>
          <dt>Missing config</dt>
          <dd>{(broker?.missing_config ?? []).join(', ') || 'None'}</dd>
        </div>
        <div>
          <dt>Execution enabled</dt>
          <dd>{broker?.execution_enabled ? 'Yes' : 'No'}</dd>
        </div>
        <div>
          <dt>Real money</dt>
          <dd>{broker?.real_money ? 'Yes' : 'No'}</dd>
        </div>
      </dl>
    </section>
  )

  return (
    <div className="paper-page">
      <section className="paper-hero">
        <div>
          <p className="eyebrow">Paper Trading</p>
          <h2>Paper Trading Control Center</h2>
          <p>
            NO REAL MONEY. NO BROKER CONNECTED. Historical Replay tests Atlas
            against past OHLCV prices. Live Paper Fund runs a separate simulated
            forward paper account when started.
          </p>
        </div>
        <div className="paper-hero__badges" aria-label="Paper trading safety policy">
          <span>REPLAY: PRICE-BACKED ONLY</span>
          <span>LIVE FUND: {fundStatus}</span>
          <span>NO REAL MONEY</span>
          <span>NO BROKER CONNECTED</span>
        </div>
      </section>

      <PaperSimulationControls
        isRunning={isReplayRunning}
        message={replayMessage}
        onReplay={handleRunReplay}
        onReset={handleResetReplays}
      />

      {healthPanel}

      {auditPanel}

      {hasReplayData ? (
        <>
          <PaperPortfolioSummary portfolio={portfolio} />
          <PaperPnLChart history={history} replay={lastReplay} />
          <PaperPerformanceCard performance={performance} />
          <PaperTradesTable trades={trades} />
        </>
      ) : (
        <>
          {lastReplayFailed ? <PaperPnLChart history={[]} replay={lastReplay} /> : null}
          <section className="dashboard-state">
            {replayEmptyMessage}
          </section>
        </>
      )}

      <LivePaperFundPanel
        fund={paperData.fund}
        isBusy={isFundBusy}
        message={fundMessage}
        onCycle={() => handleFundAction(runPaperFundCycle, 'Cycle completed.')}
        onPause={() => handleFundAction(pausePaperFund, 'Live paper fund paused.')}
        onReset={() => handleFundAction(resetPaperFund, 'Live paper fund records cleared.')}
        onResume={() => handleFundAction(resumePaperFund, 'Live paper fund resumed.')}
        onStart={(payload) => handleFundAction(() => startPaperFund(payload), 'Live paper fund started. Run an analysis cycle to begin.')}
        onStop={() => handleFundAction(stopPaperFund, 'Live paper fund stopped.')}
      />

      <PaperTradingStatusCard
        isRunning={isReplayRunning}
        lastReplayFailed={lastReplayFailed}
        status={status}
      />

      <PaperLearningCard learning={status?.learning} />

      {brokerPanel}
    </div>
  )
}

export default PaperTrading
