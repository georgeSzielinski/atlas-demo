import { memo } from 'react'
import {
  Bar,
  BarChart as RBarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AXIS_STYLE, CHART_COLORS, TOOLTIP_STYLE } from './chartTheme'
import { EmptyState } from '../ui/States'

// Reusable horizontal bar chart for contributions/impacts.
// data: [{ name, value }]; positive/negative auto-colored.
function BarChart({ data, height = 240, emptyMessage = 'No contribution data yet.', layout = 'vertical' }) {
  const rows = Array.isArray(data) ? data.filter(Boolean) : []
  if (rows.length === 0) {
    return <EmptyState title="No data" message={emptyMessage} />
  }

  const vertical = layout === 'vertical'
  return (
    <div className="dv2-chart" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RBarChart
          data={rows}
          layout={vertical ? 'vertical' : 'horizontal'}
          margin={{ top: 4, right: 16, bottom: 4, left: 4 }}
        >
          <CartesianGrid stroke={CHART_COLORS.grid} horizontal={!vertical} vertical={vertical} />
          {vertical ? (
            <>
              <XAxis type="number" tick={AXIS_STYLE.tick} stroke={AXIS_STYLE.stroke} tickLine={false} />
              <YAxis
                type="category"
                dataKey="name"
                tick={AXIS_STYLE.tick}
                stroke={AXIS_STYLE.stroke}
                tickLine={false}
                width={96}
              />
            </>
          ) : (
            <>
              <XAxis dataKey="name" tick={AXIS_STYLE.tick} stroke={AXIS_STYLE.stroke} tickLine={false} />
              <YAxis tick={AXIS_STYLE.tick} stroke={AXIS_STYLE.stroke} tickLine={false} width={48} />
            </>
          )}
          <Tooltip {...TOOLTIP_STYLE} cursor={{ fill: 'rgba(148,163,184,0.08)' }} />
          <Bar dataKey="value" radius={4} animationDuration={600}>
            {rows.map((row, index) => (
              <Cell
                key={row.name ?? index}
                fill={Number(row.value) < 0 ? CHART_COLORS.negative : CHART_COLORS.positive}
              />
            ))}
          </Bar>
        </RBarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default memo(BarChart)
