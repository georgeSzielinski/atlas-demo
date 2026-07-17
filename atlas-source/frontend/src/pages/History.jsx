import { useEffect, useState } from 'react'
import RecommendationCard from '../components/RecommendationCard'
import { getHistory, getHistoryRun } from '../services/api'

function formatValue(value, fallback = 'Unavailable') {
  if (value === null || value === undefined || value === '') {
    return fallback
  }

  return String(value)
}

function getRunId(run) {
  return run?.run_id ?? run?.id ?? run?.uuid
}

function getRunTimestamp(run) {
  return run?.created_at ?? run?.timestamp ?? run?.run_at ?? run?.completed_at
}

function getRunStatus(run) {
  return run?.status ?? run?.result ?? run?.state
}

function normalizeRuns(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.runs)) {
    return data.runs
  }

  if (Array.isArray(data?.history)) {
    return data.history
  }

  return []
}

function normalizeRecommendations(run) {
  const recommendations =
    run?.recommendations ?? run?.latest_recommendations ?? run?.run?.recommendations

  return Array.isArray(recommendations) ? recommendations : []
}

function normalizeSnapshot(run) {
  return (
    run?.portfolio_snapshot ??
    run?.latest_portfolio_snapshot ??
    run?.snapshot ??
    run?.portfolio ??
    null
  )
}

function normalizeBenchmarkSummaries(run) {
  const benchmarks =
    run?.benchmark_summaries ??
    run?.benchmarks ??
    run?.run?.benchmark_summaries ??
    []

  return Array.isArray(benchmarks) ? benchmarks : []
}

function summarizeRun(run) {
  if (!run) {
    return []
  }

  return [
    ['Run ID', formatValue(getRunId(run))],
    ['Status', formatValue(getRunStatus(run))],
    ['Started', formatValue(getRunTimestamp(run))],
    ['Market Status', formatValue(run.market_status)],
  ]
}

function snapshotMetrics(snapshot) {
  if (!snapshot) {
    return []
  }

  return [
    ['Portfolio Value', snapshot.portfolio_value ?? snapshot.total_value ?? snapshot.value],
    ['Cash', snapshot.cash],
    ['Cash Allocation', snapshot.cash_percentage],
    ['Positions', snapshot.position_count ?? snapshot.positions_count],
    ['Risk', snapshot.risk_level ?? snapshot.risk],
  ].filter(([, value]) => value !== null && value !== undefined && value !== '')
}

function validationResults(recommendations) {
  return recommendations
    .map((recommendation) => recommendation.validation_result ?? null)
    .filter(Boolean)
}

function average(values) {
  if (values.length === 0) {
    return 0
  }

  return values.reduce((total, value) => total + value, 0) / values.length
}

function hitRate(results, action) {
  const matching = action
    ? results.filter((result) => result.recommendation === action)
    : results

  if (matching.length === 0) {
    return 0
  }

  const hits = matching.filter((result) => result.success).length

  return (hits / matching.length) * 100
}

function formatNumber(value) {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return formatValue(value)
  }

  return numberValue.toFixed(2)
}

function performanceMetrics(recommendations) {
  const results = validationResults(recommendations)
  const returns = results
    .map((result) => Number(result.percentage_return))
    .filter((value) => !Number.isNaN(value))
  const gains = returns.filter((value) => value > 0)
  const losses = returns.filter((value) => value < 0)

  return [
    ['Overall Hit Rate', `${formatNumber(hitRate(results))}%`],
    ['BUY Hit Rate', `${formatNumber(hitRate(results, 'BUY'))}%`],
    ['HOLD Hit Rate', `${formatNumber(hitRate(results, 'HOLD'))}%`],
    ['AVOID Hit Rate', `${formatNumber(hitRate(results, 'AVOID'))}%`],
    ['Average Return', `${formatNumber(average(returns))}%`],
    ['Average Gain', `${formatNumber(average(gains))}%`],
    ['Average Loss', `${formatNumber(average(losses))}%`],
    ['Largest Gain', `${formatNumber(gains.length ? Math.max(...gains) : 0)}%`],
    ['Largest Loss', `${formatNumber(losses.length ? Math.min(...losses) : 0)}%`],
    ['Win/Loss Ratio', losses.length ? formatNumber(gains.length / losses.length) : 'Unavailable'],
    ['Max Drawdown', 'Not calculated yet'],
    ['Sharpe Ratio', 'Not calculated yet'],
  ]
}

function validationHistory(recommendations) {
  return recommendations
    .map((recommendation) => recommendation.validation_result)
    .filter(Boolean)
    .map((validation) => [
      `${validation.ticker} ${validation.recommendation}`,
      `${formatValue(validation.status)} | ${formatValue(validation.percentage_return)}%`,
    ])
}

function benchmarkMetrics(benchmarks) {
  return benchmarks
    .map((benchmark) => [
      benchmark.metric ?? benchmark.name ?? benchmark.source_name,
      benchmark.value ?? benchmark.effectiveness_score,
      benchmark.engine_name ?? benchmark.source_name ?? 'Benchmark',
      benchmark.benchmark_date ?? benchmark.last_benchmark_date,
    ])
    .filter(([label]) => label)
}

function History() {
  const [runs, setRuns] = useState([])
  const [selectedRunId, setSelectedRunId] = useState('')
  const [selectedRun, setSelectedRun] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDetailLoading, setIsDetailLoading] = useState(false)
  const [error, setError] = useState('')
  const [detailError, setDetailError] = useState('')

  useEffect(() => {
    let isCurrent = true

    async function loadHistory() {
      try {
        const data = await getHistory()
        const nextRuns = normalizeRuns(data)
        const firstRunId = getRunId(nextRuns[0])

        if (isCurrent) {
          setRuns(nextRuns)
          setSelectedRunId(firstRunId ? String(firstRunId) : '')
          setError('')
        }
      } catch {
        if (isCurrent) {
          setError('Atlas API is offline. Start the FastAPI backend and refresh history.')
        }
      } finally {
        if (isCurrent) {
          setIsLoading(false)
        }
      }
    }

    loadHistory()

    return () => {
      isCurrent = false
    }
  }, [])

  useEffect(() => {
    if (!selectedRunId) {
      const clearSelectedRun = setTimeout(() => {
        setSelectedRun(null)
      }, 0)

      return () => clearTimeout(clearSelectedRun)
    }

    let isCurrent = true

    async function loadRunDetail() {
      setIsDetailLoading(true)
      setDetailError('')

      try {
        const data = await getHistoryRun(selectedRunId)

        if (isCurrent) {
          setSelectedRun(data)
        }
      } catch {
        if (isCurrent) {
          setSelectedRun(null)
          setDetailError('Unable to load this run. The backend may be offline.')
        }
      } finally {
        if (isCurrent) {
          setIsDetailLoading(false)
        }
      }
    }

    loadRunDetail()

    return () => {
      isCurrent = false
    }
  }, [selectedRunId])

  if (isLoading) {
    return <section className="dashboard-state">Loading history...</section>
  }

  if (error) {
    return <section className="dashboard-state dashboard-state--error">{error}</section>
  }

  if (runs.length === 0) {
    return <section className="dashboard-state">No history returned by the API.</section>
  }

  const recommendations = normalizeRecommendations(selectedRun)
  const snapshot = normalizeSnapshot(selectedRun)
  const runSummary = summarizeRun(selectedRun)
  const metrics = snapshotMetrics(snapshot)
  const performance = performanceMetrics(recommendations)
  const validationItems = validationHistory(recommendations)
  const benchmarks = benchmarkMetrics(normalizeBenchmarkSummaries(selectedRun))

  return (
    <div className="history-page">
      <section className="history-panel" aria-label="Recent Atlas runs">
        <div className="section-heading">
          <p className="eyebrow">Run History</p>
          <h2>Recent Runs</h2>
        </div>

        <div className="history-table">
          {runs.map((run) => {
            const runId = String(getRunId(run) ?? '')

            return (
              <button
                className={
                  runId === selectedRunId ? 'history-row is-selected' : 'history-row'
                }
                key={runId || getRunTimestamp(run)}
                onClick={() => setSelectedRunId(runId)}
                type="button"
              >
                <span>
                  <strong>{formatValue(runId, 'Unknown run')}</strong>
                  <small>{formatValue(getRunTimestamp(run), 'Timestamp unavailable')}</small>
                </span>
                <span>{formatValue(getRunStatus(run), 'Status unavailable')}</span>
              </button>
            )
          })}
        </div>
      </section>

      <section className="history-panel history-detail" aria-label="Selected run details">
        <div className="section-heading">
          <p className="eyebrow">Selected Run</p>
          <h2>Run Details</h2>
        </div>

        {isDetailLoading ? (
          <div className="dashboard-state">Loading run details...</div>
        ) : detailError ? (
          <div className="dashboard-state dashboard-state--error">{detailError}</div>
        ) : (
          <>
            <dl className="history-summary">
              {runSummary.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>

            <div className="history-section">
              <div className="section-heading">
                <p className="eyebrow">Portfolio</p>
                <h2>Snapshot</h2>
              </div>
              {metrics.length > 0 ? (
                <dl className="history-summary history-summary--compact">
                  {metrics.map(([label, value]) => (
                    <div key={label}>
                      <dt>{label}</dt>
                      <dd>{formatValue(value)}</dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <div className="dashboard-state">No portfolio snapshot returned.</div>
              )}
            </div>

            <div className="history-section">
              <div className="section-heading">
                <p className="eyebrow">Recommendations</p>
                <h2>Run Recommendations</h2>
              </div>
              {recommendations.length > 0 ? (
                <div className="history-recommendations">
                  {recommendations.map((recommendation, index) => (
                    <RecommendationCard
                      key={`${recommendation.ticker ?? recommendation.symbol ?? index}-${index}`}
                      recommendation={recommendation}
                    />
                  ))}
                </div>
              ) : (
                <div className="dashboard-state">No recommendations returned for this run.</div>
              )}
            </div>

            <div className="history-section">
              <div className="section-heading">
                <p className="eyebrow">Validation</p>
                <h2>Performance Summary</h2>
              </div>
              <dl className="history-summary history-summary--compact">
                {performance.map(([label, value]) => (
                  <div key={label}>
                    <dt>{label}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>
            </div>

            {validationItems.length > 0 ? (
              <div className="history-section">
                <div className="section-heading">
                  <p className="eyebrow">Validation</p>
                  <h2>Validation History</h2>
                </div>
                <dl className="history-summary history-summary--compact">
                  {validationItems.map(([label, value]) => (
                    <div key={`${label}-${value}`}>
                      <dt>{label}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            ) : null}

            {benchmarks.length > 0 ? (
              <div className="history-section">
                <div className="section-heading">
                  <p className="eyebrow">Benchmark Suite</p>
                  <h2>Benchmark History</h2>
                </div>
                <dl className="history-summary history-summary--compact">
                  {benchmarks.map(([label, value, engineName, date]) => (
                    <div key={`${engineName}-${label}-${date}`}>
                      <dt>{formatValue(engineName)} - {formatValue(label)}</dt>
                      <dd>{formatValue(value)}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            ) : null}
          </>
        )}
      </section>
    </div>
  )
}

export default History
