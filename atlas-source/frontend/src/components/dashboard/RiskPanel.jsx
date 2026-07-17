import { memo, useMemo } from 'react'
import Panel from '../ui/Panel'
import KVList from '../ui/KVList'
import StatusPill from '../ui/StatusPill'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { formatPercent, formatValue } from '../../services/formatters'

function RiskPanel() {
  const { data } = useDashboardData()
  const risk = data?.risk
  const riskLimits = risk?.limits
  const riskCount = risk?.count

  const rows = useMemo(() => {
    const limits = riskLimits ?? {}
    return [
      ['Max Position Size', formatPercent(Number(limits.max_position_size) * 100, { fallback: '—' })],
      ['Max Portfolio Exposure', formatPercent(Number(limits.max_portfolio_exposure) * 100, { fallback: '—' })],
      ['Max Sector Exposure', formatPercent(Number(limits.max_sector_exposure) * 100, { fallback: '—' })],
      ['Max Correlation', formatValue(limits.max_correlation, '—')],
      ['Max Positions', formatValue(limits.max_position_count, '—')],
      ['Risk Decisions', formatValue(riskCount, '0')],
    ]
  }, [riskLimits, riskCount])

  return (
    <Panel
      eyebrow="Risk"
      title="Risk Summary"
      action={<StatusPill status="EVALUATED" label="Read-only" />}
    >
      <KVList rows={rows} />
    </Panel>
  )
}

export default memo(RiskPanel)
