import { memo } from 'react'
import Panel from '../ui/Panel'
import StatusPill from '../ui/StatusPill'
import { useDashboardData } from '../../context/DashboardDataProvider'
import {
  schedulerLabel,
  marketLabel,
  formatClock,
} from '../../services/paperFundOps'

function Row({ label, children }) {
  return (
    <div className="dv2-opsrow">
      <span className="dv2-opsrow__label">{label}</span>
      <span className="dv2-opsrow__value">{children}</span>
    </div>
  )
}

// Compact operational status: the three runtime subsystems plus the timing
// that tells the operator whether the loop is actually turning over.
function OperationsSnapshot() {
  const { data } = useDashboardData()
  const fund = data?.paper_fund ?? {}
  const scheduler = data?.scheduler ?? {}
  const market = data?.market ?? {}

  const fundStatus = fund.fund_status ?? 'OFF'
  const provider = fund.price_provider || market.active_provider

  return (
    <Panel eyebrow="Operations" title="Runtime Status">
      <div className="dv2-opslist">
        <Row label="Paper Fund">
          <StatusPill status={fundStatus} />
        </Row>
        <Row label="Scheduler">
          <StatusPill status={schedulerLabel(scheduler)} label={schedulerLabel(scheduler)} />
        </Row>
        <Row label="Market">
          <StatusPill status={marketLabel(market)} label={marketLabel(market)} />
        </Row>
        <Row label="Price Provider">
          <span className="dv2-opsrow__text">{provider || '—'}</span>
        </Row>
        <Row label="Last Tick">
          <span className="dv2-opsrow__text">{formatClock(scheduler.last_tick_at)}</span>
        </Row>
        <Row label="Last Completed Cycle">
          <span className="dv2-opsrow__text">{formatClock(fund.last_update)}</span>
        </Row>
        <Row label="Next Scheduled Cycle">
          <span className="dv2-opsrow__text">{formatClock(fund.next_update)}</span>
        </Row>
      </div>
      {fund.last_error ? (
        <p className="dv2-opslist__error">{fund.last_error}</p>
      ) : null}
    </Panel>
  )
}

export default memo(OperationsSnapshot)
