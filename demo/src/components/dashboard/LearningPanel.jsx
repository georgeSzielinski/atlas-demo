import { memo, useMemo } from 'react'
import Panel from '../ui/Panel'
import KVList from '../ui/KVList'
import { EmptyState } from '../ui/States'
import { useDashboardData } from '../../context/DashboardDataProvider'

function titleize(key) {
  return String(key).replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

function LearningPanel() {
  const { data } = useDashboardData()
  const learningSection = data?.learning

  const rows = useMemo(() => {
    const learning = learningSection ?? {}
    const counts = learning.source_counts ?? {}
    const entries = Object.entries(counts)
    if (entries.length > 0) {
      return entries.map(([key, value]) => [titleize(key), String(value)])
    }
    return [
      ['Recommendation Outcomes', (learning.recommendation_outcomes?.items ?? learning.recommendation_outcomes ?? []).length],
      ['Symbol Performance', (learning.symbol_performance?.items ?? learning.symbol_performance ?? []).length],
      ['Risk Blockers', (learning.risk_blockers?.items ?? learning.risk_blockers ?? []).length],
    ].map(([key, value]) => [key, String(value)])
  }, [learningSection])

  const hasData = rows.some((row) => row[1] && row[1] !== '0')

  return (
    <Panel eyebrow="Learning" title="Learning Summary">
      {hasData ? (
        <KVList rows={rows} />
      ) : (
        <EmptyState
          title="No lessons yet"
          message="Atlas learning activates after paper-fund cycles produce outcomes."
        />
      )}
    </Panel>
  )
}

export default memo(LearningPanel)
