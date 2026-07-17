import { memo, useMemo } from 'react'
import Panel from '../ui/Panel'
import StatusPill from '../ui/StatusPill'
import { EmptyState } from '../ui/States'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { latestRiskRejection, formatClock } from '../../services/paperFundOps'

// Surfaces the most recent risk-gate rejection so an operator can see why a
// proposed paper trade was blocked without opening the risk drill-down.
function RiskRejectionPanel() {
  const { data } = useDashboardData()
  const risk = data?.risk ?? {}

  const rejection = useMemo(() => latestRiskRejection(risk), [risk])
  const decisionCount = Array.isArray(risk.decisions)
    ? risk.decisions.length
    : Number(risk.count ?? 0)
  const hasDecisions = decisionCount > 0
  const pillStatus = rejection ? 'REJECTED' : hasDecisions ? 'APPROVED' : 'NOT_EVALUATED'
  const pillLabel = rejection ? 'Blocked' : hasDecisions ? 'Clear' : 'No decisions'

  return (
    <Panel
      eyebrow="Risk Gate"
      title="Latest Rejection"
      action={<StatusPill status={pillStatus} label={pillLabel} />}
    >
      {rejection ? (
        <div className="dv2-reject">
          <div className="dv2-reject__head">
            <span className="dv2-reject__symbol">
              {rejection.side} {rejection.quantity} {rejection.symbol}
            </span>
            <span className="dv2-reject__time">{formatClock(rejection.at)}</span>
          </div>
          {rejection.reasons.length > 0 ? (
            <ul className="dv2-reject__reasons">
              {rejection.reasons.map((reason, index) => (
                <li key={index}>{reason}</li>
              ))}
            </ul>
          ) : (
            <p className="dv2-reject__reasons">Rejected by the risk gate (no detailed reason recorded).</p>
          )}
        </div>
      ) : (
        <EmptyState
          title={hasDecisions ? 'No rejections' : 'No risk decisions yet'}
          message={
            hasDecisions
              ? 'No proposed paper trades have been blocked by the risk gate in the current window.'
              : 'Risk gate decisions appear after the live paper fund proposes orders during a cycle.'
          }
        />
      )}
    </Panel>
  )
}

export default memo(RiskRejectionPanel)
