import { memo, useState } from 'react'
import Panel from '../ui/Panel'
import StatusPill from '../ui/StatusPill'
import MeterBar from '../ui/MeterBar'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { runPaperFundCycle } from '../../services/api'
import {
  formatCurrency,
  formatPercent,
  formatSignedPercent,
} from '../../services/formatters'
import {
  deriveTodayTrades,
  formatClock,
  schedulerLabel,
} from '../../services/paperFundOps'

const FUND_EXPLANATIONS = {
  OFF: 'The simulated live paper fund has not been started. Start it from Paper Trading before cycles can run.',
  READY: 'The paper fund is armed and waiting for a validated-price cycle.',
  RUNNING: 'The paper fund is active. Cycles still execute simulated orders only.',
  PAUSED: 'The paper fund is paused. Resume it from Paper Trading before automation continues.',
  ERROR: 'The paper fund hit an error. Review the latest error before running another cycle.',
}

function msUntil(timestamp) {
  if (!timestamp) return null
  const target = new Date(timestamp).getTime()
  if (Number.isNaN(target)) return null
  return target - Date.now()
}

function formatCountdown(timestamp) {
  const ms = msUntil(timestamp)
  if (ms === null) return 'No cycle scheduled'
  if (ms <= 0) return 'Due now'
  const totalMinutes = Math.ceil(ms / 60000)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours <= 0) return `${minutes} min`
  return `${hours}h ${String(minutes).padStart(2, '0')}m`
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return 'n/a'
  const total = Math.max(0, Number(seconds) || 0)
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  if (minutes <= 0) return `${rest}s`
  return `${minutes}m ${String(rest).padStart(2, '0')}s`
}

function investedValue(fund, snapshot) {
  if (snapshot?.current_value !== null && snapshot?.current_value !== undefined) {
    return Number(snapshot.current_value) || 0
  }
  return Object.values(fund?.open_positions ?? {}).reduce((total, position) => {
    const value =
      position?.current_value ??
      (Number(position?.quantity ?? 0) * Number(position?.current_price ?? position?.cost_basis ?? 0))
    return total + (Number(value) || 0)
  }, 0)
}

function MissionControlPanel() {
  const { data, refetch } = useDashboardData()
  const [isRunning, setIsRunning] = useState(false)
  const [message, setMessage] = useState('')
  const fund = data?.paper_fund ?? {}
  const risk = data?.risk ?? {}
  const scheduler = data?.scheduler ?? {}
  const market = data?.market ?? {}
  const snapshot = fund.latest_snapshot ?? {}
  const cycle = fund.cycle_state ?? {}
  const fundStatus = String(fund.fund_status ?? 'OFF').toUpperCase()
  const cash = Number(snapshot.cash ?? fund.cash ?? 0) || 0
  const invested = investedValue(fund, snapshot)
  const portfolioValue = Number(snapshot.portfolio_value ?? cash + invested) || 0
  const investedPercent = portfolioValue > 0 ? invested / portfolioValue * 100 : null
  const cashPercent = portfolioValue > 0 ? cash / portfolioValue * 100 : null
  const today = deriveTodayTrades(fund, risk)
  const canRunCycle = ['READY', 'RUNNING'].includes(fundStatus)
  const explanation = fund.last_error || FUND_EXPLANATIONS[fundStatus] || 'Paper fund status is unavailable.'

  async function handleRunCycle() {
    if (!canRunCycle || isRunning) return
    setIsRunning(true)
    setMessage('Running one simulated paper-fund cycle. No broker. No real money.')
    try {
      const result = await runPaperFundCycle()
      const cycle = result?.cycle
      await refetch()
      if (cycle?.cycle_status === 'FAILED') {
        setMessage(`Cycle failed: ${cycle.error || 'validated prices were unavailable'}. No real trades were sent.`)
      } else if (cycle?.cycle_id) {
        setMessage(`Cycle ${cycle.cycle_id} finished. Filled ${cycle.orders?.length ?? 0} simulated order(s).`)
      } else {
        setMessage('Cycle request finished. Dashboard refreshed.')
      }
    } catch (error) {
      setMessage(`${error.message || 'Cycle request failed.'} No real trades were sent.`)
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <Panel
      eyebrow="Mission Control"
      title="Live Paper Fund Control Room"
      className="dv2-panel--wide"
      action={<StatusPill status={fundStatus} />}
    >
      <div className="dv2-mission">
        <div className="dv2-mission__status">
          <p>{explanation}</p>
          <div className="dv2-mission__badges">
            <StatusPill status={schedulerLabel(scheduler)} label={`Scheduler: ${schedulerLabel(scheduler)}`} />
            <StatusPill
              status={market.status === 'EVALUATED' ? 'EVALUATED' : 'NOT_EVALUATED'}
              label={`Market: ${market.market_session ?? market.status ?? 'unknown'}`}
            />
          </div>
        </div>

        <div className="dv2-mission__grid">
          <div>
            <span className="dv2-mission__label">Next cycle</span>
            <strong>{formatCountdown(fund.next_update)}</strong>
            <small>{formatClock(fund.next_update)}</small>
          </div>
          <div>
            <span className="dv2-mission__label">Cycle state</span>
            <strong>{cycle.state ?? 'Idle'}</strong>
            <small>{formatDuration(cycle.duration_seconds)}</small>
          </div>
          <div>
            <span className="dv2-mission__label">Approved / rejected today</span>
            <strong>{today.approved} / {today.rejected}</strong>
            <small>{today.hasRiskData ? 'risk decisions' : 'no risk decisions yet'}</small>
          </div>
          <div>
            <span className="dv2-mission__label">Simulated fills today</span>
            <strong>{today.simulated}</strong>
            <small>No broker integration</small>
          </div>
          <div>
            <span className="dv2-mission__label">Portfolio value</span>
            <strong>{portfolioValue > 0 ? formatCurrency(portfolioValue) : 'Not started'}</strong>
            <small>{formatSignedPercent(snapshot.total_return, { fallback: 'total return n/a' })}</small>
          </div>
          <div>
            <span className="dv2-mission__label">Last successful cycle</span>
            <strong>{formatClock(cycle.last_successful_cycle_time)}</strong>
            <small>{cycle.recovery_status ?? 'no recovery active'}</small>
          </div>
        </div>

        <div className="dv2-mission__capital">
          <div>
            <span>Cash</span>
            <strong>{formatCurrency(cash)}</strong>
            <small>{formatPercent(cashPercent, { fallback: 'cash n/a' })}</small>
          </div>
          <MeterBar
            value={investedPercent ?? 0}
            tone={investedPercent > 80 ? 'warn' : 'accent'}
            label={`Invested ${formatPercent(investedPercent, { fallback: 'n/a' })}`}
          />
          <div>
            <span>Invested</span>
            <strong>{formatCurrency(invested)}</strong>
            <small>{formatPercent(investedPercent, { fallback: 'invested n/a' })}</small>
          </div>
        </div>

        <div className="dv2-mission__actions">
          <button
            className="dv2-button"
            disabled={!canRunCycle || isRunning}
            onClick={handleRunCycle}
            type="button"
          >
            {isRunning ? 'Running simulated cycle...' : 'Run simulated cycle'}
          </button>
          <span>
            Manual cycle uses the existing paper-fund endpoint. It can only create simulated paper orders after validated prices and risk approval.
          </span>
        </div>
        {message ? <p className="dv2-mission__message">{message}</p> : null}
      </div>
    </Panel>
  )
}

export default memo(MissionControlPanel)
