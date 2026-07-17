import { memo } from 'react'
import { EmptyState } from './States'

// Simple key/value list. rows: [[key, value], ...] or [{ key, value }].
function KVList({ rows, emptyMessage = 'No values available.' }) {
  const list = (Array.isArray(rows) ? rows : [])
    .map((row) => (Array.isArray(row) ? { key: row[0], value: row[1] } : row))
    .filter((row) => row && row.value !== null && row.value !== undefined && row.value !== '')
  if (list.length === 0) {
    return <EmptyState message={emptyMessage} />
  }
  return (
    <div className="dv2-kv">
      {list.map((row) => (
        <div className="dv2-kv__row" key={String(row.key)}>
          <span className="dv2-kv__key">{row.key}</span>
          <span className="dv2-kv__val">{row.value}</span>
        </div>
      ))}
    </div>
  )
}

export default memo(KVList)
