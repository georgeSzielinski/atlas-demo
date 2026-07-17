// Shared dark-first chart theme so every Recharts component reads as one system.
export const CHART_PALETTE = [
  '#5b8cff', // accent blue
  '#3ddc97', // green
  '#f5b544', // amber
  '#c084fc', // violet
  '#38bdf8', // sky
  '#fb7185', // rose
  '#a3e635', // lime
  '#f472b6', // pink
]

export const CHART_COLORS = {
  axis: 'rgba(148, 163, 184, 0.65)',
  grid: 'rgba(148, 163, 184, 0.14)',
  accent: '#5b8cff',
  positive: '#3ddc97',
  negative: '#fb7185',
}

export const TOOLTIP_STYLE = {
  contentStyle: {
    background: 'rgba(10, 15, 23, 0.96)',
    border: '1px solid rgba(148, 163, 184, 0.22)',
    borderRadius: 10,
    color: '#e2e8f0',
    fontSize: 12,
    boxShadow: '0 10px 30px rgba(0, 0, 0, 0.45)',
  },
  labelStyle: { color: '#94a3b8', marginBottom: 4 },
  itemStyle: { color: '#e2e8f0' },
}

export const AXIS_STYLE = {
  tick: { fill: CHART_COLORS.axis, fontSize: 11 },
  stroke: CHART_COLORS.grid,
}
