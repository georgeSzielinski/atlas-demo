import { useEffect, useState } from 'react'
import DashboardCard from '../components/DashboardCard'
import RecommendationCard from '../components/RecommendationCard'
import { getDashboard, runAtlas } from '../services/api'

function formatValue(value, fallback = 'Unavailable') {
  if (value === null || value === undefined || value === '') {
    return fallback
  }

  return String(value)
}

function formatPercent(value) {
  if (value === null || value === undefined || value === '') {
    return 'Unavailable'
  }

  return `${value}%`
}

function formatMetric(value, suffix = '') {
  if (value === null || value === undefined || value === '') {
    return 'Unavailable'
  }

  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return `${value}${suffix}`
  }

  return `${numberValue.toFixed(2).replace(/\.00$/, '')}${suffix}`
}

function formatList(value) {
  if (Array.isArray(value) && value.length > 0) {
    return value.map((item) => formatValue(item)).filter(Boolean)
  }

  if (typeof value === 'string' && value.trim()) {
    return [value]
  }

  return []
}

function formatObjectList(value) {
  const normalize = (item, index, label = null) => {
    const fallbackLabel = label ?? `Item ${index + 1}`

    if (item === null || item === undefined || item === '') {
      return null
    }

    if (typeof item === 'object' && !Array.isArray(item)) {
      return {
        source: fallbackLabel,
        scenario: fallbackLabel,
        ...item,
      }
    }

    const text = Array.isArray(item)
      ? item.map((entry) => formatValue(entry)).join(', ')
      : formatValue(item)

    return {
      source: label ?? text,
      effect: text,
      score: '',
      scenario: label ?? text,
      effect_on_confidence: text,
      effect_on_conviction: '',
      possible_recommendation_change: '',
    }
  }

  if (Array.isArray(value)) {
    return value
      .map((item, index) => normalize(item, index))
      .filter(Boolean)
  }

  if (typeof value === 'string' && value.trim()) {
    return [normalize(value, 0)]
  }

  if (typeof value === 'number') {
    return [normalize(value, 0)]
  }

  if (value && typeof value === 'object') {
    return Object.entries(value)
      .map(([label, item], index) => normalize(item, index, label))
      .filter(Boolean)
  }

  return []
}

function getRecommendationKey(recommendation) {
  return `${recommendation?.ticker ?? recommendation?.symbol ?? 'N/A'}-${recommendation?.action ?? 'HOLD'}`
}

function buildRecommendationDetails(recommendation) {
  if (!recommendation) {
    return []
  }

  return [
    ['Ticker', recommendation.ticker ?? recommendation.symbol],
    ['Action', recommendation.action],
    ['Confidence', formatPercent(recommendation.confidence)],
    ['Technical Score', recommendation.technical_score],
    ['Fundamental Score', recommendation.fundamental_score],
    ['Portfolio Score', recommendation.portfolio_score],
    ['Risk Score', recommendation.risk_score],
    ['Forecast Score', recommendation.forecast_score],
    ['Overall Score', recommendation.overall_score],
    ['Rating', recommendation.rating],
    ['News Sentiment', recommendation.news_sentiment],
    ['News Confidence', formatPercent(recommendation.news_confidence)],
    ['Headline Count', recommendation.headline_count],
    ['News Summary', recommendation.news_summary],
  ].map(([label, value]) => [label, formatValue(value)])
}

function formatRun(run) {
  if (!run) {
    return {
      value: 'No runs yet',
      detail: 'Run Atlas to populate this dashboard',
    }
  }

  return {
    value: formatValue(run.status ?? run.result ?? run.id, 'Latest run found'),
    detail: formatValue(run.created_at ?? run.timestamp ?? run.run_at, 'Run timestamp unavailable'),
  }
}

function formatPortfolio(snapshot) {
  if (!snapshot) {
    return {
      value: 'Unavailable',
      detail: 'No portfolio snapshot returned',
      tone: 'muted',
    }
  }

  const totalValue = snapshot.total_value ?? snapshot.portfolio_value ?? snapshot.value
  const health = snapshot.health ?? snapshot.status ?? snapshot.risk_level

  return {
    value: formatValue(health ?? totalValue, 'Snapshot found'),
    detail: totalValue ? `Portfolio value: ${totalValue}` : 'Portfolio snapshot loaded',
    tone: 'positive',
  }
}

function formatRecommendations(recommendations) {
  if (!Array.isArray(recommendations) || recommendations.length === 0) {
    return {
      value: '0',
      detail: 'No recommendations returned',
    }
  }

  const topNames = recommendations
    .slice(0, 3)
    .map((item) => item.ticker ?? item.symbol ?? item.name)
    .filter(Boolean)
    .join(', ')

  return {
    value: String(recommendations.length),
    detail: topNames || 'Recommendations loaded',
  }
}

function buildCards(data) {
  const latestRun = formatRun(data.latest_run)
  const portfolio = formatPortfolio(data.latest_portfolio_snapshot)
  const recommendations = formatRecommendations(data.latest_recommendations)

  return [
    {
      title: 'Market Status',
      value: formatValue(data.market_status ?? data.latest_run?.market_status),
      detail: 'Loaded from Atlas API',
      tone: 'accent',
    },
    {
      title: 'Portfolio Health',
      ...portfolio,
    },
    {
      title: 'Latest Run',
      ...latestRun,
      tone: 'neutral',
    },
    {
      title: 'Top Recommendations',
      ...recommendations,
      tone: 'accent',
    },
  ]
}

function buildSystemHealthCards(data) {
  const health = data.system_health ?? {}

  return [
    ['Backend Status', health.backend_status],
    ['Database Status', health.database_status],
    ['Forecast Provider', health.forecast_provider],
    ['Validation Status', health.validation_status],
    ['Backtesting', health.backtesting_availability],
    ['News Engine', health.news_engine_status],
  ].map(([title, value]) => ({
    title,
    value: formatValue(value),
    detail: 'Atlas system health',
    tone: value === 'Online' || value === 'Connected' || value === 'Available' || value === 'Ready'
      ? 'positive'
      : 'neutral',
  }))
}

function buildRecommendationMetricCards(data) {
  const metrics = data.recommendation_metrics ?? {}

  return [
    ['Total Recommendations', metrics.total, 'All saved Atlas recommendations'],
    ['Pending', metrics.pending, 'Awaiting validation'],
    ['Successful', metrics.successful, 'Validated hits'],
    ['Failed', metrics.failed, 'Validated misses'],
    ['Hit Rate', formatMetric(metrics.hit_rate, '%'), 'Succeeded vs completed'],
    ['Average Return', formatMetric(metrics.average_return, '%'), 'Validated recommendation return'],
  ].map(([title, value, detail]) => ({
    title,
    value: formatValue(value),
    detail,
    tone: title === 'Successful' || title === 'Hit Rate' ? 'positive' : 'neutral',
  }))
}

function buildEvidenceMetricCards(data) {
  const metrics = data.evidence_metrics ?? {}

  return [
    ['Technical', metrics.technical],
    ['Fundamentals', metrics.fundamentals],
    ['Forecast', metrics.forecast],
    ['News', metrics.news],
    ['Portfolio', metrics.portfolio],
    ['Risk', metrics.risk],
  ].map(([title, value]) => ({
    title,
    value: formatMetric(value),
    detail: 'Average evidence score',
    tone: 'accent',
  }))
}

function buildForecastCards(data) {
  const forecast = data.forecast_information ?? {}

  return [
    {
      title: 'Current Provider',
      value: formatValue(forecast.display_name),
      detail: `Configured: ${formatValue(forecast.current_provider, 'mock')}`,
      tone: forecast.display_name === 'Kronos' ? 'positive' : 'accent',
    },
  ]
}

function buildDataProviderCards(data) {
  const health = data.data_provider_health ?? {}
  const isHealthy = health.healthy === true

  return [
    {
      title: 'Active Provider',
      value: formatValue(health.active_provider, 'mock'),
      detail: 'Configured market data source',
      tone: 'accent',
    },
    {
      title: 'Provider Health',
      value: isHealthy ? 'Healthy' : 'Unhealthy',
      detail: formatValue(health.failure_message, 'No provider failure reported'),
      tone: isHealthy ? 'positive' : 'neutral',
    },
    {
      title: 'Supported Tickers',
      value: formatValue(health.supported_tickers_count),
      detail: 'Provider ticker coverage',
      tone: 'neutral',
    },
    {
      title: 'Latest Price',
      value: health.latest_price_available ? 'Available' : 'Unavailable',
      detail: 'Latest price probe',
      tone: health.latest_price_available ? 'positive' : 'neutral',
    },
  ]
}

function buildPipelineStatusCards(data) {
  const status = data.pipeline_status ?? {}

  return [
    {
      title: 'Pipeline',
      value: status.pipeline_active ? 'Active' : 'Inactive',
      detail: 'Atlas orchestration layer',
      tone: status.pipeline_active ? 'positive' : 'neutral',
    },
    {
      title: 'Execution Mode',
      value: formatValue(status.execution_mode),
      detail: 'Analysis lifecycle coordinator',
      tone: 'accent',
    },
    {
      title: 'Data Provider',
      value: formatValue(status.data_provider, 'mock'),
      detail: 'Market data input',
      tone: 'accent',
    },
    {
      title: 'Forecast Provider',
      value: formatValue(status.forecast_provider, 'mock'),
      detail: 'Forecast intelligence input',
      tone: 'accent',
    },
    {
      title: 'Validation',
      value: status.validation_available ? 'Available' : 'Unavailable',
      detail: 'Recommendation validation layer',
      tone: status.validation_available ? 'positive' : 'neutral',
    },
    {
      title: 'Benchmark',
      value: status.benchmark_available ? 'Available' : 'Unavailable',
      detail: 'Atlas Benchmark Suite',
      tone: status.benchmark_available ? 'positive' : 'neutral',
    },
  ]
}

function buildNewsProviderCards(data) {
  const health = data.news_provider_health ?? {}
  const isHealthy = health.healthy === true

  return [
    {
      title: 'News Provider',
      value: formatValue(health.active_provider, 'fake'),
      detail: 'Configured news intelligence source',
      tone: 'accent',
    },
    {
      title: 'News Health',
      value: isHealthy ? 'Healthy' : 'Unhealthy',
      detail: formatValue(health.failure_message, 'No provider failure reported'),
      tone: isHealthy ? 'positive' : 'neutral',
    },
    {
      title: 'Headlines',
      value: health.headline_availability ? 'Available' : 'Unavailable',
      detail: 'Headline probe',
      tone: health.headline_availability ? 'positive' : 'neutral',
    },
    {
      title: 'Failure Message',
      value: formatValue(health.failure_message, 'None'),
      detail: 'Provider diagnostic',
      tone: health.failure_message ? 'neutral' : 'positive',
    },
  ]
}

function buildFundamentalProviderCards(data) {
  const health = data.fundamental_provider_health ?? {}
  const isHealthy = health.healthy === true

  return [
    {
      title: 'Fundamental Provider',
      value: formatValue(health.active_provider, 'mock'),
      detail: 'Configured company fundamentals source',
      tone: 'accent',
    },
    {
      title: 'Fundamental Health',
      value: isHealthy ? 'Healthy' : 'Unhealthy',
      detail: formatValue(health.failure_message, 'No provider failure reported'),
      tone: isHealthy ? 'positive' : 'neutral',
    },
    {
      title: 'Fundamental Data',
      value: health.data_availability ? 'Available' : 'Unavailable',
      detail: 'Fundamental data probe',
      tone: health.data_availability ? 'positive' : 'neutral',
    },
    {
      title: 'Failure Message',
      value: formatValue(health.failure_message, 'None'),
      detail: 'Provider diagnostic',
      tone: health.failure_message ? 'neutral' : 'positive',
    },
  ]
}

function buildLatestRecommendationCards(data) {
  const recommendation = data.latest_recommendation

  if (!recommendation) {
    return [
      {
        title: 'Latest Recommendation',
        value: 'Unavailable',
        detail: 'Run Atlas to create recommendations',
        tone: 'muted',
      },
    ]
  }

  return [
    ['Ticker', recommendation.ticker],
    ['Action', recommendation.action],
    ['Confidence', formatPercent(recommendation.confidence)],
    ['Signal Quality', recommendation.signal_quality_score],
    ['Validation Status', recommendation.validation_status],
  ].map(([title, value]) => ({
    title,
    value: formatValue(value),
    detail: 'Latest saved recommendation',
    tone: title === 'Validation Status' && value === 'Succeeded' ? 'positive' : 'neutral',
  }))
}

function buildFusionStatusCards(data) {
  const status = data.fusion_status ?? {}
  const latest = Array.isArray(data.latest_recommendations)
    ? data.latest_recommendations[0]
    : null

  return [
    {
      title: 'Fusion Status',
      value: formatValue(status.status),
      detail: 'Intelligence fusion engine',
      tone: status.status === 'PASS' ? 'positive' : 'neutral',
    },
    {
      title: 'Fusion Conviction',
      value: formatValue(latest?.overall_conviction ?? status.overall_conviction),
      detail: 'Latest recommendation or health probe',
      tone: 'accent',
    },
    {
      title: 'Validation Status',
      value: formatValue(latest?.validation_status, 'Pending'),
      detail: 'Latest recommendation validation',
      tone: latest?.validation_status === 'Succeeded' ? 'positive' : 'neutral',
    },
    {
      title: 'Benchmark Status',
      value: data.pipeline_status?.benchmark_available ? 'Available' : 'Unavailable',
      detail: 'Atlas Benchmark Suite',
      tone: data.pipeline_status?.benchmark_available ? 'positive' : 'neutral',
    },
  ]
}

function Dashboard() {
  const [dashboard, setDashboard] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState('')
  const [runMessage, setRunMessage] = useState('')
  const [selectedRecommendation, setSelectedRecommendation] = useState(null)

  async function loadDashboard() {
    const data = await getDashboard()
    setDashboard(data)
    setError('')
  }

  useEffect(() => {
    let isCurrent = true

    async function loadInitialDashboard() {
      try {
        const data = await getDashboard()

        if (isCurrent) {
          setDashboard(data)
          setError('')
        }
      } catch (requestError) {
        if (isCurrent) {
          setError(requestError.message)
        }
      } finally {
        if (isCurrent) {
          setIsLoading(false)
        }
      }
    }

    loadInitialDashboard()

    return () => {
      isCurrent = false
    }
  }, [])

  useEffect(() => {
    const recommendations = Array.isArray(dashboard?.latest_recommendations)
      ? dashboard.latest_recommendations
      : []

    const updateSelection = setTimeout(() => {
      if (recommendations.length === 0) {
        setSelectedRecommendation(null)
        return
      }

      const selectedKey = getRecommendationKey(selectedRecommendation)
      const stillExists = recommendations.some(
        (recommendation) => getRecommendationKey(recommendation) === selectedKey,
      )

      if (!selectedRecommendation || !stillExists) {
        setSelectedRecommendation(recommendations[0])
      }
    }, 0)

    return () => clearTimeout(updateSelection)
  }, [dashboard, selectedRecommendation])

  async function handleRunAtlas() {
    setIsRunning(true)
    setRunMessage('')

    try {
      await runAtlas()
      await loadDashboard()
      setRunMessage('Atlas run completed. Dashboard data refreshed.')
    } catch (requestError) {
      setRunMessage(requestError.message)
    } finally {
      setIsRunning(false)
    }
  }

  if (isLoading) {
    return <section className="dashboard-state">Loading dashboard...</section>
  }

  if (error) {
    return <section className="dashboard-state dashboard-state--error">{error}</section>
  }

  const dashboardCards = buildCards(dashboard)
  const systemHealthCards = buildSystemHealthCards(dashboard)
  const recommendationMetricCards = buildRecommendationMetricCards(dashboard)
  const evidenceMetricCards = buildEvidenceMetricCards(dashboard)
  const forecastCards = buildForecastCards(dashboard)
  const dataProviderCards = buildDataProviderCards(dashboard)
  const pipelineStatusCards = buildPipelineStatusCards(dashboard)
  const newsProviderCards = buildNewsProviderCards(dashboard)
  const fundamentalProviderCards = buildFundamentalProviderCards(dashboard)
  const fusionStatusCards = buildFusionStatusCards(dashboard)
  const latestRecommendationCards = buildLatestRecommendationCards(dashboard)
  const recommendations = Array.isArray(dashboard.latest_recommendations)
    ? dashboard.latest_recommendations
    : []
  const selectedRecommendationKey = getRecommendationKey(selectedRecommendation)
  const detailFields = buildRecommendationDetails(selectedRecommendation)
  const reasons = formatList(
    selectedRecommendation?.reasons ?? selectedRecommendation?.reason,
  )
  const risks = formatList(selectedRecommendation?.risks ?? selectedRecommendation?.risk)
  const assumptions = formatList(selectedRecommendation?.assumptions)
  const flipConditions = formatList(
    selectedRecommendation?.recommendation_flip_conditions,
  )
  const counterfactuals = formatObjectList(selectedRecommendation?.counterfactuals)
  const confidenceDrivers = formatObjectList(
    selectedRecommendation?.confidence_drivers,
  )
  const executiveWarnings = formatList(selectedRecommendation?.executive_warnings)
  const executiveStrengths = formatList(selectedRecommendation?.executive_strengths)
  const executiveWeaknesses = formatList(selectedRecommendation?.executive_weaknesses)
  const requiredResearch = formatList(
    selectedRecommendation?.required_follow_up_research,
  )

  return (
    <>
      <section className="dashboard-actions" aria-label="Atlas run controls">
        <div>
          <p className="eyebrow">Atlas Engine</p>
          <h2>Run a fresh research pass</h2>
        </div>
        <button
          className="run-atlas-button"
          disabled={isRunning}
          onClick={handleRunAtlas}
          type="button"
        >
          {isRunning ? 'Running Atlas...' : 'Run Atlas'}
        </button>
      </section>

      {runMessage ? <section className="dashboard-state">{runMessage}</section> : null}

      <section className="dashboard-grid" aria-label="Atlas dashboard overview">
        {dashboardCards.map((card) => (
          <DashboardCard key={card.title} {...card} />
        ))}
      </section>

      <section className="dashboard-section" aria-labelledby="system-health-title">
        <div className="section-heading">
          <p className="eyebrow">Atlas Intelligence</p>
          <h2 id="system-health-title">System Health</h2>
        </div>
        <div className="dashboard-grid dashboard-grid--six">
          {systemHealthCards.map((card) => (
            <DashboardCard key={card.title} {...card} />
          ))}
        </div>
      </section>

      <section className="dashboard-section" aria-labelledby="recommendation-metrics-title">
        <div className="section-heading">
          <p className="eyebrow">Validation</p>
          <h2 id="recommendation-metrics-title">Recommendation Metrics</h2>
        </div>
        <div className="dashboard-grid dashboard-grid--six">
          {recommendationMetricCards.map((card) => (
            <DashboardCard key={card.title} {...card} />
          ))}
        </div>
      </section>

      <section className="dashboard-section" aria-labelledby="evidence-metrics-title">
        <div className="section-heading">
          <p className="eyebrow">Evidence</p>
          <h2 id="evidence-metrics-title">Evidence Metrics</h2>
        </div>
        <div className="dashboard-grid dashboard-grid--six">
          {evidenceMetricCards.map((card) => (
            <DashboardCard key={card.title} {...card} />
          ))}
        </div>
      </section>

      <section className="dashboard-section" aria-labelledby="forecast-info-title">
        <div className="section-heading">
          <p className="eyebrow">Forecast</p>
          <h2 id="forecast-info-title">Forecast Information</h2>
        </div>
        <div className="dashboard-grid dashboard-grid--single">
          {forecastCards.map((card) => (
            <DashboardCard key={card.title} {...card} />
          ))}
        </div>
      </section>

      <section className="dashboard-section" aria-labelledby="data-provider-title">
        <div className="section-heading">
          <p className="eyebrow">Market Data</p>
          <h2 id="data-provider-title">Data Provider Health</h2>
        </div>
        <div className="dashboard-grid">
          {dataProviderCards.map((card) => (
            <DashboardCard key={card.title} {...card} />
          ))}
        </div>
      </section>

      <section className="dashboard-section" aria-labelledby="pipeline-status-title">
        <div className="section-heading">
          <p className="eyebrow">Pipeline</p>
          <h2 id="pipeline-status-title">Intelligence Pipeline</h2>
        </div>
        <div className="dashboard-grid dashboard-grid--six">
          {pipelineStatusCards.map((card) => (
            <DashboardCard key={card.title} {...card} />
          ))}
        </div>
      </section>

      <section className="dashboard-section" aria-labelledby="news-provider-title">
        <div className="section-heading">
          <p className="eyebrow">News</p>
          <h2 id="news-provider-title">News Provider Health</h2>
        </div>
        <div className="dashboard-grid">
          {newsProviderCards.map((card) => (
            <DashboardCard key={card.title} {...card} />
          ))}
        </div>
      </section>

      <section className="dashboard-section" aria-labelledby="fundamental-provider-title">
        <div className="section-heading">
          <p className="eyebrow">Fundamentals</p>
          <h2 id="fundamental-provider-title">Fundamental Provider Health</h2>
        </div>
        <div className="dashboard-grid">
          {fundamentalProviderCards.map((card) => (
            <DashboardCard key={card.title} {...card} />
          ))}
        </div>
      </section>

      <section className="dashboard-section" aria-labelledby="fusion-status-title">
        <div className="section-heading">
          <p className="eyebrow">Fusion</p>
          <h2 id="fusion-status-title">Fusion and Controls</h2>
        </div>
        <div className="dashboard-grid">
          {fusionStatusCards.map((card) => (
            <DashboardCard key={card.title} {...card} />
          ))}
        </div>
      </section>

      <section className="dashboard-section" aria-labelledby="latest-recommendation-title">
        <div className="section-heading">
          <p className="eyebrow">Latest Recommendation</p>
          <h2 id="latest-recommendation-title">Latest Recommendation</h2>
        </div>
        <div className="dashboard-grid dashboard-grid--five">
          {latestRecommendationCards.map((card) => (
            <DashboardCard key={card.title} {...card} />
          ))}
        </div>
      </section>

      <section className="recommendations-section" aria-labelledby="recommendations-title">
        <div className="section-heading">
          <p className="eyebrow">Live Recommendations</p>
          <h2 id="recommendations-title">Top Recommendations</h2>
        </div>

        {recommendations.length > 0 ? (
          <div className="recommendations-grid">
            {recommendations.map((recommendation) => (
              <RecommendationCard
                isSelected={
                  getRecommendationKey(recommendation) === selectedRecommendationKey
                }
                key={getRecommendationKey(recommendation)}
                onSelect={setSelectedRecommendation}
                recommendation={recommendation}
              />
            ))}
          </div>
        ) : (
          <div className="dashboard-state">No recommendations returned by the API.</div>
        )}
      </section>

      {selectedRecommendation ? (
        <section
          className="recommendation-detail"
          aria-labelledby="recommendation-detail-title"
        >
          <div className="section-heading">
            <p className="eyebrow">Recommendation Detail</p>
            <h2 id="recommendation-detail-title">
              {formatValue(
                selectedRecommendation.ticker ?? selectedRecommendation.symbol,
                'Selected Recommendation',
              )}
            </h2>
          </div>

          <dl className="recommendation-detail__metrics">
            {detailFields.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>

          <div className="recommendation-detail__notes">
            <section>
              <h3>Reasons</h3>
              {reasons.length > 0 ? (
                <ul>
                  {reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              ) : (
                <p>Unavailable</p>
              )}
            </section>

            <section>
              <h3>Risks</h3>
              {risks.length > 0 ? (
                <ul>
                  {risks.map((risk) => (
                    <li key={risk}>{risk}</li>
                  ))}
                </ul>
              ) : (
                <p>Unavailable</p>
              )}
            </section>

            <section className="recommendation-detail__wide">
              <h3>Executive Review</h3>
              <p>
                {formatValue(selectedRecommendation.executive_status, 'Unreviewed')}
                {` | Confidence ${formatPercent(selectedRecommendation.executive_confidence)}`}
              </p>
              <p>{formatValue(selectedRecommendation.executive_summary)}</p>
            </section>

            <section>
              <h3>Readiness</h3>
              <p>{formatValue(selectedRecommendation.executive_status, 'Unreviewed')}</p>
            </section>

            <section>
              <h3>Warnings</h3>
              {executiveWarnings.length > 0 ? (
                <ul>
                  {executiveWarnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              ) : (
                <p>Unavailable</p>
              )}
            </section>

            <section>
              <h3>Strengths</h3>
              {executiveStrengths.length > 0 ? (
                <ul>
                  {executiveStrengths.map((strength) => (
                    <li key={strength}>{strength}</li>
                  ))}
                </ul>
              ) : (
                <p>Unavailable</p>
              )}
            </section>

            <section>
              <h3>Weaknesses</h3>
              {executiveWeaknesses.length > 0 ? (
                <ul>
                  {executiveWeaknesses.map((weakness) => (
                    <li key={weakness}>{weakness}</li>
                  ))}
                </ul>
              ) : (
                <p>Unavailable</p>
              )}
            </section>

            <section className="recommendation-detail__wide">
              <h3>Required Research</h3>
              {requiredResearch.length > 0 ? (
                <ul>
                  {requiredResearch.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p>Unavailable</p>
              )}
            </section>

            <section>
              <h3>Why Atlas Believes This</h3>
              {confidenceDrivers.length > 0 ? (
                <ul>
                  {confidenceDrivers.map((driver) => (
                    <li key={`${driver.source}-${driver.score}`}>
                      {formatValue(driver.source)} {formatValue(driver.effect)} confidence
                      with score {formatValue(driver.score)}.
                    </li>
                  ))}
                </ul>
              ) : (
                <p>Unavailable</p>
              )}
            </section>

            <section>
              <h3>What Could Change the Recommendation</h3>
              {flipConditions.length > 0 ? (
                <ul>
                  {flipConditions.map((condition) => (
                    <li key={condition}>{condition}</li>
                  ))}
                </ul>
              ) : (
                <p>Unavailable</p>
              )}
            </section>

            <section>
              <h3>Top Assumptions</h3>
              {assumptions.length > 0 ? (
                <ul>
                  {assumptions.slice(0, 5).map((assumption) => (
                    <li key={assumption}>{assumption}</li>
                  ))}
                </ul>
              ) : (
                <p>Unavailable</p>
              )}
            </section>

            <section>
              <h3>Most Fragile Assumption</h3>
              <p>{formatValue(selectedRecommendation.weakest_assumption)}</p>
            </section>

            <section className="recommendation-detail__wide">
              <h3>Possible Future Scenarios</h3>
              {counterfactuals.length > 0 ? (
                <ul>
                  {counterfactuals.map((scenario) => (
                    <li key={scenario.scenario}>
                      <strong>{formatValue(scenario.scenario)}</strong>: confidence
                      {` ${formatValue(scenario.effect_on_confidence)}`},
                      conviction {formatValue(scenario.effect_on_conviction)}.
                      {` ${formatValue(scenario.possible_recommendation_change)}`}
                    </li>
                  ))}
                </ul>
              ) : (
                <p>Unavailable</p>
              )}
            </section>
          </div>
        </section>
      ) : null}
    </>
  )
}

export default Dashboard
