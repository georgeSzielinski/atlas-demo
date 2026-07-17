import { memo, useMemo } from 'react'
import Panel from '../ui/Panel'
import BarChart from '../charts/BarChart'
import { EmptyState } from '../ui/States'
import { useDashboardData } from '../../context/DashboardDataProvider'

function numericValue(value) {
  if (value && typeof value === 'object' && 'value' in value) {
    return value.value
  }
  return value
}

function ScenarioPanel() {
  const { data } = useDashboardData()
  const scenarios = data?.scenarios ?? {}

  const bars = useMemo(() => {
    const list = Array.isArray(scenarios.scenarios) ? scenarios.scenarios : []
    return list
      .map((scenario) => {
        const name = scenario?.name ?? scenario?.scenario ?? scenario?.label
        const rawValue =
          scenario?.portfolio_impact_pct ??
          scenario?.impact_pct ??
          scenario?.estimated_portfolio_return ??
          scenario?.estimated_drawdown ??
          scenario?.impact
        const value = numericValue(rawValue)
        if (name === undefined || value === undefined || value === null) {
          return null
        }
        return { name: String(name), value: Number(value) }
      })
      .filter((row) => row && !Number.isNaN(row.value))
  }, [scenarios.scenarios])

  const emptyReason =
    scenarios.stress_summary?.reason ??
    scenarios.base_portfolio?.reason ??
    'Scenario stress appears once the paper fund holds positions.'

  return (
    <Panel eyebrow="Analytics" title="Scenario Stress">
      {bars.length > 0 ? (
        <BarChart data={bars} height={220} emptyMessage="No scenarios evaluated yet." />
      ) : (
        <EmptyState
          title={scenarios.status === 'Unavailable' ? 'Unavailable' : 'Not evaluated'}
          message={emptyReason}
        />
      )}
    </Panel>
  )
}

export default memo(ScenarioPanel)
