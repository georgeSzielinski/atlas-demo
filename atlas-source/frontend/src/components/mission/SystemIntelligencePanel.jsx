import { memo } from 'react'
import Panel from '../ui/Panel'
import StatusPill from '../ui/StatusPill'
import GradeBadge from '../ui/GradeBadge'
import AlertList from '../ui/AlertList'
import Timeline from '../ui/Timeline'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { systemIntelligence } from '../../services/missionOps'
import { deriveLiveEvents, formatClock } from '../../services/paperFundOps'

function Stat({ label, children, hint }) {
  return (
    <div className="dv3-intel__stat">
      <span className="dv3-intel__k">{label}</span>
      <span className="dv3-intel__v">{children}</span>
      {hint ? <small className="dv3-intel__hint">{hint}</small> : null}
    </div>
  )
}

// Row 6 — the catch-all intelligence strip: warnings, reliability, learning,
// recommendation count, provider and the recent event stream.
function SystemIntelligencePanel() {
  const { data } = useDashboardData()
  const intel = systemIntelligence(data)
  const events = deriveLiveEvents(data?.paper_fund ?? {}, data?.risk ?? {}, 8).map(
    (event) => ({
      title: event.title,
      detail: event.detail,
      at: formatClock(event.at),
      tone: event.tone === 'profit' ? 'positive' : event.tone === 'loss' ? 'negative' : 'neutral',
    }),
  )
  const trendDirection = intel.reliabilityTrend?.direction

  return (
    <div className="dv3-intel">
      <Panel eyebrow="System Intelligence" title="Signals & Reliability">
        <div className="dv3-intel__stats">
          <Stat label="Reliability" hint={trendDirection ? `trend: ${trendDirection}` : 'no trend yet'}>
            <GradeBadge grade={intel.reliabilityGrade} score={intel.reliabilityScore} />
          </Stat>
          <Stat label="Recommendations" hint="latest cycle">
            {intel.recommendationCount ?? 0}
          </Stat>
          <Stat
            label="Provider"
            hint={
              intel.providerHealthy === null
                ? 'health n/a'
                : intel.providerHealthy
                  ? 'healthy'
                  : 'degraded'
            }
          >
            {intel.provider ?? '—'}
          </Stat>
          <Stat label="Learning" hint={`${intel.learning.entries} entries`}>
            <StatusPill
              status={intel.learning.active ? 'RUNNING' : 'OFF'}
              label={intel.learning.active ? 'Active' : 'Idle'}
            />
          </Stat>
        </div>
        {intel.learning.latestLesson ? (
          <p className="dv3-intel__lesson">“{intel.learning.latestLesson}”</p>
        ) : null}
      </Panel>

      <Panel eyebrow="Warnings" title="Active Warnings">
        <AlertList
          items={intel.warnings}
          tone="warn"
          emptyTitle="No warnings"
          emptyMessage="All monitored subsystems are within tolerance."
          max={6}
        />
      </Panel>

      <Panel eyebrow="Activity" title="Recent Events">
        <Timeline events={events} emptyMessage="No recorded activity yet." max={8} />
      </Panel>
    </div>
  )
}

export default memo(SystemIntelligencePanel)
