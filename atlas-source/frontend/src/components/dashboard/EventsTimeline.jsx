import { memo, useMemo } from 'react'
import Panel from '../ui/Panel'
import Timeline from '../ui/Timeline'
import { useDashboardData } from '../../context/DashboardDataProvider'

const FAILURE_TYPES = new Set(['CYCLE_FAILED', 'FUND_STOPPED'])
const SUCCESS_TYPES = new Set(['CYCLE_COMPLETED', 'ORDERS_FILLED', 'FUND_STARTED', 'PORTFOLIO_UPDATED'])

function activityTone(type) {
  if (FAILURE_TYPES.has(type)) return 'negative'
  if (SUCCESS_TYPES.has(type)) return 'positive'
  return 'neutral'
}

function severityTone(severity) {
  const key = String(severity).toUpperCase()
  if (key === 'CRITICAL' || key === 'ERROR') return 'negative'
  if (key === 'WARNING') return 'warning'
  return 'neutral'
}

// Merged timeline of paper-fund activity + reliability incidents, newest first.
function EventsTimeline() {
  const { data } = useDashboardData()
  const fund = data?.paper_fund ?? {}
  const reliability = data?.reliability ?? {}

  const events = useMemo(() => {
    const activity = (fund.activity_log ?? []).map((entry) => ({
      at: String(entry.at ?? ''),
      title: String(entry.activity_type ?? 'EVENT').replace(/_/g, ' '),
      detail: entry.message,
      tone: activityTone(entry.activity_type),
    }))
    const incidents = (reliability.recent_incidents ?? []).map((incident) => ({
      at: String(incident.at ?? ''),
      title: `${incident.subsystem ?? 'system'} · ${incident.severity ?? 'incident'}`,
      detail: incident.message,
      tone: severityTone(incident.severity),
    }))
    return [...activity, ...incidents]
      .sort((a, b) => String(b.at).localeCompare(String(a.at)))
      .map((event) => ({ ...event, at: event.at.slice(0, 19).replace('T', ' ') }))
  }, [fund.activity_log, reliability.recent_incidents])

  return (
    <Panel eyebrow="Timeline" title="Recent Events">
      <Timeline events={events} emptyMessage="Events appear as Atlas operates." max={14} />
    </Panel>
  )
}

export default memo(EventsTimeline)
