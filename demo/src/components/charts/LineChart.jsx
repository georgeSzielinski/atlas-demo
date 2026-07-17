import { memo } from 'react'
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AXIS_STYLE, CHART_COLORS, CHART_PALETTE, TOOLTIP_STYLE } from './chartTheme'
import { EmptyState } from '../ui/States'

// Reusable responsive line/area chart.
//   data:  array of row objects
//   xKey:  key for the x axis
//   series: [{ key, name, color?, area? }]
//   referenceLines: [{ y, label?, color? }] horizontal dashed guides
function LineChart({
  data,
  xKey,
  series,
  height = 240,
  emptyMessage = 'No series data yet.',
  showLegend = false,
  yFormatter,
  referenceLines = [],
}) {
  const rows = Array.isArray(data) ? data : []
  const lines = Array.isArray(series) ? series : []
  if (rows.length === 0 || lines.length === 0) {
    return <EmptyState title="No chart data" message={emptyMessage} />
  }

  return (
    <div className="dv2-chart" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <defs>
            {lines.map((line, index) => {
              const color = line.color ?? CHART_PALETTE[index % CHART_PALETTE.length]
              return (
                <linearGradient id={`dv2-area-${line.key}`} key={line.key} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              )
            })}
          </defs>
          <CartesianGrid stroke={CHART_COLORS.grid} vertical={false} />
          <XAxis
            dataKey={xKey}
            tick={AXIS_STYLE.tick}
            stroke={AXIS_STYLE.stroke}
            tickLine={false}
            minTickGap={24}
          />
          <YAxis
            tick={AXIS_STYLE.tick}
            stroke={AXIS_STYLE.stroke}
            tickLine={false}
            width={48}
            tickFormatter={yFormatter}
          />
          <Tooltip {...TOOLTIP_STYLE} />
          {showLegend ? <Legend wrapperStyle={{ fontSize: 12, color: CHART_COLORS.axis }} /> : null}
          {referenceLines.map((line) => (
            <ReferenceLine
              key={`ref-${line.y}-${line.label ?? ''}`}
              y={line.y}
              stroke={line.color ?? CHART_COLORS.axis}
              strokeDasharray="4 4"
              label={line.label ? {
                value: line.label,
                fill: CHART_COLORS.axis,
                fontSize: 11,
                position: 'insideTopRight',
              } : undefined}
            />
          ))}
          {lines.map((line, index) => {
            const color = line.color ?? CHART_PALETTE[index % CHART_PALETTE.length]
            return line.area ? (
              <Area
                key={line.key}
                type="monotone"
                dataKey={line.key}
                name={line.name ?? line.key}
                stroke={color}
                strokeWidth={2}
                fill={`url(#dv2-area-${line.key})`}
                animationDuration={600}
                dot={false}
                activeDot={{ r: 4 }}
              />
            ) : (
              <Line
                key={line.key}
                type="monotone"
                dataKey={line.key}
                name={line.name ?? line.key}
                stroke={color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
                animationDuration={600}
              />
            )
          })}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

export default memo(LineChart)
