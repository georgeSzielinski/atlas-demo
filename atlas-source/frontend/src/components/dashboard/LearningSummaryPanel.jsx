import { memo, useMemo } from 'react'
import Panel from '../ui/Panel'
import { EmptyState } from '../ui/States'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { latestLearning, formatClock } from '../../services/paperFundOps'

// Latest per-cycle learning takeaway from the paper fund's learning log. This
// is the "what did the last cycle teach us" line, distinct from the aggregate
// learning analytics shown elsewhere.
function LearningSummaryPanel() {
  const { data } = useDashboardData()
  const fund = data?.paper_fund ?? {}

  const learning = useMemo(() => latestLearning(fund), [fund])
  const summary = learning?.summary ?? null
  const worked = Array.isArray(summary?.what_worked) ? summary.what_worked : []
  const didNot = Array.isArray(summary?.what_did_not_work) ? summary.what_did_not_work : []

  return (
    <Panel eyebrow="Learning" title="Latest Cycle Takeaway">
      {learning ? (
        <div className="dv2-learn">
          <p className="dv2-learn__lesson">{learning.lesson}</p>
          <span className="dv2-learn__time">{formatClock(learning.at)}</span>
          {worked.length > 0 ? (
            <div className="dv2-learn__group">
              <span className="dv2-learn__group-label dv2-learn__group-label--good">What worked</span>
              <ul className="dv2-learn__list">
                {worked.slice(0, 3).map((item, index) => <li key={index}>{item}</li>)}
              </ul>
            </div>
          ) : null}
          {didNot.length > 0 ? (
            <div className="dv2-learn__group">
              <span className="dv2-learn__group-label dv2-learn__group-label--bad">What didn&apos;t</span>
              <ul className="dv2-learn__list">
                {didNot.slice(0, 3).map((item, index) => <li key={index}>{item}</li>)}
              </ul>
            </div>
          ) : null}
        </div>
      ) : (
        <EmptyState
          title="No lessons yet"
          message="A learning takeaway is recorded after each paper-fund cycle completes."
        />
      )}
    </Panel>
  )
}

export default memo(LearningSummaryPanel)
