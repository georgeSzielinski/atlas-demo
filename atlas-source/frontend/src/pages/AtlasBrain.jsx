import { useEffect, useMemo, useState } from 'react'
import BrainFlow from '../components/BrainFlow'
import CatalystImpact from '../components/CatalystImpact'
import ConfidenceBreakdown from '../components/ConfidenceBreakdown'
import DecisionTree from '../components/DecisionTree'
import EngineContribution from '../components/EngineContribution'
import EvidenceRadar from '../components/EvidenceRadar'
import HistoricalInfluence from '../components/HistoricalInfluence'
import PortfolioImpactSummary from '../components/PortfolioImpactSummary'
import ReasoningSummary from '../components/ReasoningSummary'
import RecommendationConfidenceGauge from '../components/RecommendationConfidenceGauge'
import RecommendationTimeline from '../components/RecommendationTimeline'
import TrustIndicators from '../components/TrustIndicators'
import ValidationStatus from '../components/ValidationStatus'
import { getBrain, getDashboard } from '../services/api'

const FALLBACK_TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']

function tickerOptions(dashboard) {
  const recommendations = dashboard?.latest_recommendations
  if (Array.isArray(recommendations) && recommendations.length > 0) {
    const tickers = recommendations.map((item) => item.ticker).filter(Boolean)
    if (tickers.length > 0) {
      return Array.from(new Set(tickers))
    }
  }
  return FALLBACK_TICKERS
}

function AtlasBrain() {
  const [tickers, setTickers] = useState(FALLBACK_TICKERS)
  const [selectedTicker, setSelectedTicker] = useState(FALLBACK_TICKERS[0])
  const [brain, setBrain] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let isCurrent = true
    async function loadTickers() {
      try {
        const dashboard = await getDashboard()
        if (!isCurrent) return
        const options = tickerOptions(dashboard)
        setTickers(options)
        setSelectedTicker((current) => (options.includes(current) ? current : options[0]))
      } catch {
        if (isCurrent) setTickers(FALLBACK_TICKERS)
      }
    }
    loadTickers()
    return () => {
      isCurrent = false
    }
  }, [])

  useEffect(() => {
    let isCurrent = true
    async function loadBrain() {
      setIsLoading(true)
      try {
        const data = await getBrain(selectedTicker)
        if (!isCurrent) return
        setBrain(data)
        setSelectedNode(null)
        setError('')
      } catch (requestError) {
        if (!isCurrent) return
        setError(requestError.message)
        setBrain(null)
      } finally {
        if (isCurrent) setIsLoading(false)
      }
    }
    loadBrain()
    return () => {
      isCurrent = false
    }
  }, [selectedTicker])

  const overview = brain?.overview ?? {}
  const trust = brain?.trust_indicators ?? {}
  const provider = trust.data_provider_health ?? {}
  const providerUnavailable = provider.healthy === false
  const recommendationLabel = overview.recommendation ?? 'Unavailable'
  const confidenceLabel = overview.confidence === null || overview.confidence === undefined
    ? 'Unavailable'
    : `${overview.confidence}%`
  const probabilityLabel = overview.probability === null || overview.probability === undefined
    ? 'Unavailable'
    : `${overview.probability}%`
  const overviewCards = useMemo(
    () => [
      ['Recommendation', recommendationLabel],
      ['Confidence', confidenceLabel],
      ['Probability', probabilityLabel],
      ['Knowledge', overview.knowledge_score ?? 0],
      ['Stability', overview.stability_score ?? 0],
      ['Executive', overview.executive_review ?? 'Unavailable'],
      ['Committee', `${overview.committee_decision?.agreement ?? 0}%`],
    ],
    [confidenceLabel, overview, probabilityLabel, recommendationLabel],
  )

  if (isLoading) {
    return <section className="dashboard-state">Loading Atlas Brain...</section>
  }

  if (error && !brain) {
    return (
      <section className="dashboard-state dashboard-state--error">
        {error} Start the FastAPI backend and refresh to open Atlas Brain.
      </section>
    )
  }

  return (
    <div className="brain-page">
      <section className="brain-hero">
        <div className="brain-hero__content">
          <p className="eyebrow">Atlas Brain</p>
          <h2>{selectedTicker}: {recommendationLabel}</h2>
          <p>
            Daily testing view for why Atlas reached this conclusion, what evidence mattered,
            and what would change its mind.
          </p>
          <div className="brain-safety-row" aria-label="Atlas safety policy">
            <span>PAPER ONLY</span>
            <span>NO BROKER CONNECTED</span>
            <span>HUMAN APPROVAL REQUIRED</span>
          </div>
        </div>
        <label className="brain-ticker-select">
          <span>Ticker</span>
          <select onChange={(event) => setSelectedTicker(event.target.value)} value={selectedTicker}>
            {tickers.map((ticker) => (
              <option key={ticker} value={ticker}>
                {ticker}
              </option>
            ))}
          </select>
        </label>
      </section>

      {brain?.demo_data ? (
        <p className="brain-demo-banner">
          Showing a deterministic illustrative example — no saved recommendation exists for{' '}
          {brain.ticker} yet.
        </p>
      ) : null}

      {providerUnavailable ? (
        <p className="brain-demo-banner brain-demo-banner--warning">
          Provider unavailable: {provider.failure_message ?? provider.message ?? 'Atlas is showing the safest available read-only context.'}
        </p>
      ) : null}

      <section className="brain-overview-strip">
        {overviewCards.map(([label, value]) => (
          <article className="brain-overview-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </section>

      <div className="brain-grid brain-grid--top">
        <RecommendationConfidenceGauge overview={overview} />
        <ReasoningSummary reasoning={brain?.reasoning_summary} />
      </div>

      <div className="brain-grid brain-grid--flow">
        <BrainFlow
          flow={brain?.decision_flow}
          onSelect={setSelectedNode}
          selectedNodeId={selectedNode?.id}
        />
        <div className="brain-flow-detail">
          {selectedNode ? (
            <section className="brain-panel">
              <div className="brain-panel__heading">
                <div>
                  <p className="eyebrow">Stage Detail</p>
                  <h3>{selectedNode.label}</h3>
                </div>
                <span className={`brain-pill brain-pill--${selectedNode.status}`}>
                  {selectedNode.status}
                </span>
              </div>
              <p className="brain-narrative">{selectedNode.summary}</p>
              <p className="brain-note">{selectedNode.detail}</p>
            </section>
          ) : (
            <section className="brain-panel">
              <div className="brain-panel__heading">
                <div>
                  <p className="eyebrow">Stage Detail</p>
                  <h3>Select a stage</h3>
                </div>
              </div>
              <p className="brain-empty">
                Select a stage to inspect its inputs, confidence effect, and risk notes.
              </p>
            </section>
          )}
        </div>
      </div>

      <div className="brain-grid brain-grid--two">
        <EvidenceRadar evidence={brain?.evidence_contribution} />
        <EngineContribution contributions={brain?.engine_contributions} />
      </div>

      <ConfidenceBreakdown breakdown={brain?.confidence_breakdown} />

      <div className="brain-grid brain-grid--two">
        <RecommendationTimeline timeline={brain?.timeline} />
        <DecisionTree tree={brain?.decision_tree} />
      </div>

      <div className="brain-grid brain-grid--two">
        <HistoricalInfluence historical={brain?.historical_influence} />
        <PortfolioImpactSummary impact={brain?.portfolio_impact} />
      </div>

      <div className="brain-grid brain-grid--two">
        <CatalystImpact catalystImpact={brain?.catalyst_impact} />
        <ValidationStatus trust={brain?.trust_indicators} probability={brain?.probability_detail} />
      </div>

      <TrustIndicators trust={brain?.trust_indicators} />
    </div>
  )
}

export default AtlasBrain
