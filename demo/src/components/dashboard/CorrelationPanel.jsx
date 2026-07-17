import { memo } from 'react'
import Panel from '../ui/Panel'
import KVList from '../ui/KVList'
import StatusPill from '../ui/StatusPill'
import { EmptyState } from '../ui/States'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { isEvaluated, sectionReason, formatValue } from '../../services/formatters'

function CorrelationPanel() {
  const { data } = useDashboardData()
  const correlation = data?.correlation ?? {}

  if (!isEvaluated(correlation)) {
    return (
      <Panel eyebrow="Risk" title="Correlation">
        <EmptyState
          title="Not evaluated"
          message={sectionReason(correlation, 'Correlation needs real price-backed history.')}
        />
      </Panel>
    )
  }

  const coverage = correlation.coverage ?? {}
  const rows = [
    ['Symbols Evaluated', formatValue(coverage.symbols_evaluated, '0')],
    ['Pairs Evaluated', formatValue(coverage.pairs_evaluated, '0')],
    ['High-Correlation Pairs', formatValue(correlation.high_correlation_pairs?.items?.length, '0')],
    ['Clusters', formatValue(correlation.clusters?.items?.length, '0')],
    ['Limit Violations', formatValue(correlation.limit_violations?.items?.length, '0')],
  ]

  return (
    <Panel
      eyebrow="Risk"
      title="Correlation"
      action={<StatusPill status={correlation.status} />}
    >
      <KVList rows={rows} />
    </Panel>
  )
}

export default memo(CorrelationPanel)
