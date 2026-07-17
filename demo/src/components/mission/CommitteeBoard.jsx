import { memo, useState } from 'react'
import Panel from '../ui/Panel'
import StatusPill from '../ui/StatusPill'
import { EmptyState } from '../ui/States'
import CommitteeCard from './CommitteeCard'
import InstitutionalReportDrawer from './InstitutionalReportDrawer'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { committeeBoard } from '../../services/missionOps'
import { formatClock } from '../../services/paperFundOps'

// Row 3 — the investment committee's freshest verdicts as recommendation cards.
// Clicking a card opens the read-only Institutional Research Report drawer for
// that ticker (GET /institutional-report/{ticker}).
function CommitteeBoard() {
  const { data } = useDashboardData()
  const board = committeeBoard(data)
  const [selected, setSelected] = useState(null)

  return (
    <Panel
      eyebrow="Investment Committee"
      title="Current Recommendations"
      className="dv2-panel--wide"
      action={
        board.at ? (
          <span className="dv3-timestamp">evaluated {formatClock(board.at)}</span>
        ) : (
          <StatusPill status={board.status} label={board.status} />
        )
      }
    >
      {board.cards.length === 0 ? (
        <EmptyState
          title="No committee verdicts yet"
          message={
            board.reason ??
            'The investment committee has not evaluated any fresh recommendations. Run an autonomous research cycle to populate verdicts.'
          }
        />
      ) : (
        <div className="dv3-committee-grid">
          {board.cards.map((card) => (
            <CommitteeCard key={card.ticker} card={card} onOpen={setSelected} />
          ))}
        </div>
      )}
      <InstitutionalReportDrawer card={selected} onClose={() => setSelected(null)} />
    </Panel>
  )
}

export default memo(CommitteeBoard)
