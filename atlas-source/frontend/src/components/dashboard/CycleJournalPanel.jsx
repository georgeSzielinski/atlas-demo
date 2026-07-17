import { memo } from 'react'
import Panel from '../ui/Panel'
import { EmptyState } from '../ui/States'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { formatCurrency, formatValue } from '../../services/formatters'
import { formatClock } from '../../services/paperFundOps'

function symbols(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return 'None'
  return rows
    .map((row) => row.symbol ?? row.ticker ?? row)
    .filter(Boolean)
    .join(', ') || 'None'
}

function reasons(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return []
  return rows.map((row) => {
    const reasonText = Array.isArray(row.reasons)
      ? row.reasons.join('; ')
      : formatValue(row.reason, 'No reason recorded')
    return `${row.symbol ?? row.ticker ?? 'Order'}: ${reasonText}`
  })
}

function CycleJournalPanel() {
  const { data } = useDashboardData()
  const journalSection = data?.paper_fund?.cycle_journal ?? {}
  const journal = journalSection.latest
  const rejected = reasons(journal?.rejected_trades)
  const portfolio = journal?.portfolio_changes ?? {}
  const learning = journal?.learning_summary ?? {}

  return (
    <Panel eyebrow="Cycle Journal" title="Latest Completed Cycle">
      {journal ? (
        <div className="dv2-journal">
          <div className="dv2-journal__meta">
            <strong>{journal.cycle_id}</strong>
            <span>{formatClock(journal.completed_at)}</span>
          </div>
          <dl className="dv2-journal__grid">
            <div>
              <dt>Market</dt>
              <dd>{journal.market_conditions?.session ?? 'Unavailable'}</dd>
            </div>
            <div>
              <dt>Execution Time</dt>
              <dd>{journal.execution_time?.duration_seconds ?? 'n/a'}s</dd>
            </div>
            <div>
              <dt>Accepted</dt>
              <dd>{symbols(journal.accepted_trades)}</dd>
            </div>
            <div>
              <dt>Rejected</dt>
              <dd>{symbols(journal.rejected_trades)}</dd>
            </div>
            <div>
              <dt>Value Change</dt>
              <dd>{formatCurrency(portfolio.value_change)}</dd>
            </div>
            <div>
              <dt>Portfolio Value</dt>
              <dd>{formatCurrency(portfolio.current_value)}</dd>
            </div>
          </dl>
          <div className="dv2-journal__notes">
            <strong>What worked</strong>
            <p>{(learning.what_worked ?? ['No positive cycle signal recorded.']).join(' ')}</p>
          </div>
          <div className="dv2-journal__notes">
            <strong>What did not work</strong>
            <p>{(learning.what_did_not_work ?? ['No issue recorded.']).join(' ')}</p>
          </div>
          {rejected.length ? (
            <div className="dv2-journal__notes">
              <strong>Risk rejections</strong>
              <ul>
                {rejected.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          ) : null}
        </div>
      ) : (
        <EmptyState
          title="No completed cycle journal"
          message={journalSection.reason ?? 'A structured journal appears after a completed simulated paper-fund cycle.'}
        />
      )}
    </Panel>
  )
}

export default memo(CycleJournalPanel)
