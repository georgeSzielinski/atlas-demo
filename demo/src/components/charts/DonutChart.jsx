import { memo } from 'react'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { CHART_PALETTE, TOOLTIP_STYLE } from './chartTheme'
import { EmptyState } from '../ui/States'

// Reusable responsive donut. data: [{ name, value }].
function DonutChart({ data, height = 240, emptyMessage = 'No allocation data yet.', showLegend = true }) {
  const rows = (Array.isArray(data) ? data : []).filter(
    (row) => row && Number(row.value) > 0,
  )
  if (rows.length === 0) {
    return <EmptyState title="No allocation" message={emptyMessage} />
  }

  return (
    <div className="dv2-chart" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={rows}
            dataKey="value"
            nameKey="name"
            innerRadius="58%"
            outerRadius="82%"
            paddingAngle={2}
            stroke="none"
            animationDuration={600}
          >
            {rows.map((row, index) => (
              <Cell key={row.name ?? index} fill={CHART_PALETTE[index % CHART_PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip {...TOOLTIP_STYLE} />
          {showLegend ? (
            <Legend
              verticalAlign="bottom"
              height={28}
              wrapperStyle={{ fontSize: 12, color: 'rgba(148,163,184,0.85)' }}
            />
          ) : null}
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

export default memo(DonutChart)
