import { memo, useMemo } from 'react'
import Panel from '../ui/Panel'
import Timeline from '../ui/Timeline'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { dayOf, todayKey } from '../../services/paperFundOps'

const FAILURE_TYPES = new Set(['CYCLE_FAILED', 'FUND_STOPPED'])
const SUCCESS_TYPES = new Set(['CYCLE_COMPLETED', 'ORDERS_FILLED', 'FUND_STARTED', 'PORTFOLIO_UPDATED'])

function toneFor(type) {
  if (FAILURE_TYPES.has(type)) return 'negative'
  if (SUCCESS_TYPES.has(type)) return 'positive'
  return 'neutral'
}

function ActivityPanel() {
  const { data } = useDashboardData()
  const fund = data?.paper_fund ?? {}

  const events = useMemo(() => {
    const log = Array.isArray(fund.activity_log) ? fund.activity_log : []
    const key = todayKey()
    const today = log.filter((entry) => dayOf(entry?.at) === key)
    const source = today.length > 0 ? today : log
    return source.map((entry) => ({
      at: String(entry.at ?? '').slice(0, 19).replace('T', ' '),
      title: String(entry.activity_type ?? 'EVENT').replace(/_/g, ' '),
      detail: entry.message,
      tone: toneFor(entry.activity_type),
    }))
  }, [fund.activity_log])

  return (
    <Panel eyebrow="Paper Fund" title="Today's Activity">
      <Timeline
        events={events}
        emptyMessage="Activity appears after the live paper fund starts or completes a simulated cycle."
        max={8}
      />
    </Panel>
  )
}

export default memo(ActivityPanel)
