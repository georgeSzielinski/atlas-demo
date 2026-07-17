import { memo, useMemo } from 'react'
import Panel from '../ui/Panel'
import AlertList from '../ui/AlertList'
import StatusPill from '../ui/StatusPill'
import { useDashboardData } from '../../context/DashboardDataProvider'

function AlertsPanel() {
  const { data } = useDashboardData()
  const operations = data?.operations ?? {}

  const items = useMemo(() => {
    const errors = (operations.recent_errors ?? []).map((error) => ({
      severity: 'error',
      message: typeof error === 'string' ? error : error.message,
      subsystem: typeof error === 'object' ? error.source : null,
    }))
    const warnings = (operations.warnings ?? []).map((warning) => ({
      severity: 'warning',
      message: warning,
    }))
    const recommendations = (operations.operational_recommendations ?? []).map((rec) => ({
      severity: 'neutral',
      message: rec,
    }))
    return [...errors, ...warnings, ...recommendations]
  }, [operations.recent_errors, operations.warnings, operations.operational_recommendations])

  const mode = operations.operational_mode?.mode

  return (
    <Panel
      eyebrow="Operations"
      title="Operational Alerts"
      action={mode ? <StatusPill status={mode} label={mode} tone="neutral" /> : null}
    >
      <AlertList
        items={items}
        emptyTitle="All clear"
        emptyMessage="No operational alerts."
        max={7}
      />
    </Panel>
  )
}

export default memo(AlertsPanel)
