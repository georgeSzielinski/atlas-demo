import { useEffect, useMemo, useState } from 'react'
import CatalystTimeline from '../components/CatalystTimeline'
import CommitteePanel from '../components/CommitteePanel'
import EvidenceBreakdown from '../components/EvidenceBreakdown'
import ExecutiveSummary from '../components/ExecutiveSummary'
import HistoricalAnalogs from '../components/HistoricalAnalogs'
import PortfolioImpact from '../components/PortfolioImpact'
import ProbabilityCard from '../components/ProbabilityCard'
import ProviderHealthCard from '../components/ProviderHealthCard'
import ResearchHeader from '../components/ResearchHeader'
import ResearchMemoryCard from '../components/ResearchMemoryCard'
import {
  getCaseStudies,
  getCatalysts,
  getDashboard,
  getInstitutionalReport,
  getProviderHealth,
  getProviders,
  getResearchMemory,
} from '../services/api'

const fallbackRecommendation = {
  ticker: 'AAPL',
  action: 'HOLD',
  confidence: 0,
  knowledge_score: 0,
  stability_score: 0,
  executive_status: 'Unavailable',
  evidence_breakdown: [],
  catalysts: [],
  committee_agreement: 0,
}

function firstTicker(dashboard) {
  const recommendations = dashboard?.latest_recommendations
  if (Array.isArray(recommendations) && recommendations[0]?.ticker) {
    return recommendations[0].ticker
  }

  return 'AAPL'
}

function findRecommendation(dashboard, ticker) {
  const recommendations = Array.isArray(dashboard?.latest_recommendations)
    ? dashboard.latest_recommendations
    : []

  return recommendations.find((item) => item.ticker === ticker) ?? recommendations[0] ?? fallbackRecommendation
}

function sectionData(report, title) {
  return report?.sections?.find((section) => section.title === title)?.data ?? {}
}

function asArray(value) {
  return Array.isArray(value) ? value : []
}

function ResearchWorkspace() {
  const [dashboard, setDashboard] = useState(null)
  const [report, setReport] = useState(null)
  const [memory, setMemory] = useState(null)
  const [caseStudies, setCaseStudies] = useState([])
  const [catalysts, setCatalysts] = useState([])
  const [providers, setProviders] = useState([])
  const [providerHealth, setProviderHealth] = useState({})
  const [selectedTicker, setSelectedTicker] = useState('AAPL')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let isCurrent = true

    async function loadDashboardData() {
      try {
        const dashboardData = await getDashboard()
        if (!isCurrent) return
        setDashboard(dashboardData)
        setSelectedTicker(firstTicker(dashboardData))
      } catch (requestError) {
        if (!isCurrent) return
        setError(requestError.message)
        setDashboard({ latest_recommendations: [fallbackRecommendation] })
      }
    }

    loadDashboardData()

    return () => {
      isCurrent = false
    }
  }, [])

  useEffect(() => {
    let isCurrent = true

    async function loadWorkspaceData() {
      setIsLoading(true)
      try {
        const [
          reportData,
          memoryData,
          caseStudyData,
          catalystData,
          providerData,
          providerHealthData,
        ] = await Promise.all([
          getInstitutionalReport(selectedTicker),
          getResearchMemory(selectedTicker),
          getCaseStudies(),
          getCatalysts(),
          getProviders(),
          getProviderHealth(),
        ])

        if (!isCurrent) return
        setReport(reportData)
        setMemory(memoryData)
        setCaseStudies(asArray(caseStudyData.case_studies))
        setCatalysts(asArray(catalystData.catalysts ?? catalystData.events))
        setProviders(asArray(providerData.providers))
        setProviderHealth(providerHealthData)
        setError('')
      } catch (requestError) {
        if (!isCurrent) return
        setError(requestError.message)
        setReport(null)
        setMemory(null)
        setCaseStudies([])
        setCatalysts([])
        setProviders([])
        setProviderHealth({})
      } finally {
        if (isCurrent) {
          setIsLoading(false)
        }
      }
    }

    loadWorkspaceData()

    return () => {
      isCurrent = false
    }
  }, [selectedTicker])

  const recommendation = useMemo(
    () => findRecommendation(dashboard, selectedTicker),
    [dashboard, selectedTicker],
  )
  const recommendations = Array.isArray(dashboard?.latest_recommendations)
    ? dashboard.latest_recommendations
    : [fallbackRecommendation]
  const probability = report?.sections
    ? sectionData(report, 'Probability Distribution')
    : recommendation.probability_report?.probabilities ?? {}
  const expected = report?.sections
    ? sectionData(report, 'Expected Return')
    : recommendation.probability_report?.expected_outcome ?? {}
  const scenarios = report?.sections ? sectionData(report, 'Scenario Analysis') : recommendation
  const analogs = memory?.similar_historical_cases ?? sectionData(report, 'Historical Analogs')
  const filteredCases = caseStudies.filter((item) => item.ticker === selectedTicker)
  const recommendationCatalysts = asArray(recommendation.catalysts)
  const visibleCatalysts = recommendationCatalysts.length ? recommendationCatalysts : catalysts

  return (
    <div className="research-workspace">
      <div className="workspace-toolbar">
        <div>
          <p className="eyebrow">Institutional Workstation</p>
          <h2>Research Workspace</h2>
        </div>
        <label className="ticker-select">
          <span>Ticker</span>
          <select
            onChange={(event) => setSelectedTicker(event.target.value)}
            value={selectedTicker}
          >
            {recommendations.map((item) => (
              <option key={item.ticker} value={item.ticker}>
                {item.ticker}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error ? <section className="dashboard-state dashboard-state--error">{error}</section> : null}
      {isLoading ? <section className="dashboard-state">Loading research workspace...</section> : null}

      <ResearchHeader report={report} recommendation={recommendation} />

      <div className="workspace-grid workspace-grid--top">
        <ExecutiveSummary report={report} recommendation={recommendation} />
        <ProbabilityCard probability={probability} expected={expected} scenarios={scenarios} />
        <ProviderHealthCard providers={providers} health={providerHealth} />
      </div>

      <div className="workspace-grid workspace-grid--main">
        <EvidenceBreakdown recommendation={recommendation} />
        <CommitteePanel recommendation={recommendation} />
      </div>

      <div className="workspace-grid workspace-grid--main">
        <CatalystTimeline catalysts={visibleCatalysts} />
        <PortfolioImpact
          portfolio={dashboard?.latest_portfolio_snapshot ?? {}}
          recommendation={recommendation}
        />
      </div>

      <div className="workspace-grid workspace-grid--main">
        <HistoricalAnalogs analogs={Array.isArray(analogs) ? analogs : []} caseStudies={filteredCases} />
        <ResearchMemoryCard memory={memory ?? {}} />
      </div>
    </div>
  )
}

export default ResearchWorkspace
