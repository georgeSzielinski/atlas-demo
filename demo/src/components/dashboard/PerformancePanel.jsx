import { memo, useMemo } from 'react'
import Panel from '../ui/Panel'
import LineChart from '../charts/LineChart'
import { useDashboardData } from '../../context/DashboardDataProvider'

function shortDate(value) {
  if (!value) return ''
  return String(value).slice(0, 10)
}

function PerformancePanel() {
  const { data } = useDashboardData()
  const fund = data?.paper_fund ?? {}

  const series = useMemo(() => {
    const snapshots = Array.isArray(fund.snapshots) ? [...fund.snapshots] : []
    // Snapshots arrive newest-first; chart needs chronological order.
    snapshots.reverse()
    return snapshots
      .map((snapshot) => ({
        date: shortDate(snapshot.as_of ?? snapshot.date),
        value: Number(snapshot.portfolio_value ?? 0),
      }))
      .filter((row) => row.value > 0)
  }, [fund.snapshots])

  return (
    <Panel eyebrow="Performance" title="Portfolio Value">
      <LineChart
        data={series}
        xKey="date"
        series={[{ key: 'value', name: 'Portfolio Value', area: true }]}
        emptyMessage="Portfolio value history appears after paper-fund cycles run."
      />
    </Panel>
  )
}

export default memo(PerformancePanel)
