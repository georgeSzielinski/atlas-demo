import { memo, useMemo } from 'react'
import Panel from '../ui/Panel'
import DonutChart from '../charts/DonutChart'
import { useDashboardData } from '../../context/DashboardDataProvider'

function AllocationPanel() {
  const { data } = useDashboardData()
  const fund = data?.paper_fund ?? {}

  const allocation = useMemo(() => {
    const positions = fund.open_positions ?? {}
    const rows = Object.entries(positions).map(([ticker, position]) => {
      const value =
        position?.current_value ??
        (Number(position?.quantity ?? 0) * Number(position?.current_price ?? position?.cost_basis ?? 0))
      return { name: ticker, value: Number(value) || 0 }
    })
    const cash = Number(fund.cash ?? 0)
    if (cash > 0) {
      rows.push({ name: 'Cash', value: cash })
    }
    return rows.filter((row) => row.value > 0)
  }, [fund.open_positions, fund.cash])

  return (
    <Panel eyebrow="Portfolio" title="Allocation">
      <DonutChart data={allocation} emptyMessage="Start the paper fund to build allocations." />
    </Panel>
  )
}

export default memo(AllocationPanel)
