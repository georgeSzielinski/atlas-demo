import { memo } from 'react'
import Panel from '../ui/Panel'
import StatusPill from '../ui/StatusPill'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { operationsCells } from '../../services/missionOps'

// Row 2 — the operational vitals: scheduler heartbeat, last/next cycle,
// provider + database health, paper-fund status. Status colours are used only
// on the pill so the grid stays calm.
function OperationsCenterPanel() {
  const { data } = useDashboardData()
  const operations = data?.operations ?? {}
  const cells = operationsCells(data)
  const health = operations.overall_health?.status ?? 'Unavailable'

  return (
    <Panel
      eyebrow="Operations Center"
      title="System Vitals"
      action={<StatusPill status={health} />}
    >
      <div className="dv3-ops">
        {cells.map((cell) => (
          <div className="dv3-ops__cell" key={cell.key}>
            <div className="dv3-ops__head">
              <span className="dv3-ops__label">{cell.label}</span>
              <StatusPill status={cell.status} label={cell.status} />
            </div>
            <strong className="dv3-ops__value">{cell.value}</strong>
            <small className="dv3-ops__hint">{cell.hint}</small>
          </div>
        ))}
      </div>
      {operations.overall_health?.reason ? (
        <p className="dv3-ops__reason">{operations.overall_health.reason}</p>
      ) : null}
    </Panel>
  )
}

export default memo(OperationsCenterPanel)
