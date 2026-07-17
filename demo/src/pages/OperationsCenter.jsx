import { useEffect, useState } from 'react'
import OperationsAlerts from '../components/OperationsAlerts'
import OperationsCatalysts from '../components/OperationsCatalysts'
import OperationsPaperPortfolio from '../components/OperationsPaperPortfolio'
import OperationsPerformance from '../components/OperationsPerformance'
import DataProviderCard from '../components/DataProviderCard'
import MarketHealthCard from '../components/MarketHealthCard'
import MarketStatusCard from '../components/MarketStatusCard'
import OperationsProviders from '../components/OperationsProviders'
import OperationsResearchLab from '../components/OperationsResearchLab'
import OperationsSummary from '../components/OperationsSummary'
import RuntimeStatusCard from '../components/RuntimeStatusCard'
import DailyJournalCard from '../components/DailyJournalCard'
import OperationsLearningIntelligence from '../components/OperationsLearningIntelligence'
import {
  getCatalystSummary,
  getDashboard,
  getDailyCycle,
  getDailyJournal,
  getLatestDailyJournal,
  getMacroSummary,
  getMarketHealth,
  getMarketProvider,
  getMarketStatus,
  getPaperPerformance,
  getPaperPortfolio,
  getProviderHealth,
  getResearchLab,
  getRuntimeStatus,
  runDailyCycle,
} from '../services/api'

async function safeLoad(loader, fallback) {
  try {
    return await loader()
  } catch {
    return fallback
  }
}

function isStillCurrent(value) {
  return typeof value === 'function' ? value() : value
}

function OperationsCenter() {
  const [data, setData] = useState({
    catalystSummary: null,
    dashboard: null,
    dailyCycle: null,
    dailyJournal: null,
    macroSummary: null,
    marketStatus: null,
    marketProvider: null,
    marketHealth: null,
    paperPerformance: null,
    paperPortfolio: null,
    providerHealth: null,
    researchLab: null,
    runtimeStatus: null,
  })
  const [isLoading, setIsLoading] = useState(true)
  const [isCycleRunning, setIsCycleRunning] = useState(false)
  const [error, setError] = useState('')
  const [cycleMessage, setCycleMessage] = useState('')

  async function loadOperations(isCurrent = true) {
    try {
      const [
        dashboard,
        providerHealth,
        paperPortfolio,
        paperPerformance,
        catalystSummary,
        macroSummary,
        runtimeStatus,
        latestDailyJournal,
        dailyJournal,
        dailyCycle,
        researchLab,
        marketStatus,
        marketProvider,
        marketHealth,
      ] = await Promise.all([
        safeLoad(getDashboard, {}),
        safeLoad(getProviderHealth, {}),
        safeLoad(getPaperPortfolio, {}),
        safeLoad(getPaperPerformance, {}),
        safeLoad(getCatalystSummary, {}),
        safeLoad(getMacroSummary, {}),
        safeLoad(getRuntimeStatus, {}),
        safeLoad(getLatestDailyJournal, { latest_daily_journal: null }),
        safeLoad(getDailyJournal, { daily_journals: [] }),
        safeLoad(getDailyCycle, { daily_cycle_runs: [] }),
        safeLoad(getResearchLab, {}),
        safeLoad(getMarketStatus, {}),
        safeLoad(getMarketProvider, {}),
        safeLoad(getMarketHealth, {}),
      ])

      if (isStillCurrent(isCurrent)) {
        setData({
          catalystSummary,
          dashboard,
          dailyCycle,
          dailyJournal: {
            ...dailyJournal,
            latest_daily_journal: latestDailyJournal.latest_daily_journal,
          },
          macroSummary,
          marketStatus,
          marketProvider,
          marketHealth,
          paperPerformance,
          paperPortfolio,
          providerHealth,
          researchLab,
          runtimeStatus,
        })
        setError('')
      }
    } catch {
      if (isStillCurrent(isCurrent)) {
        setError('Operations data is unavailable. Start the FastAPI backend and refresh this page.')
      }
    } finally {
      if (isStillCurrent(isCurrent)) {
        setIsLoading(false)
      }
    }
  }

  useEffect(() => {
    let isCurrent = true

    Promise.resolve().then(() => loadOperations(() => isCurrent))

    return () => {
      isCurrent = false
    }
  }, [])

  async function handleRunDailyCycle() {
    setIsCycleRunning(true)
    setCycleMessage('Running SIMULATED full daily cycle...')

    try {
      const result = await runDailyCycle()
      await loadOperations(true)
      setCycleMessage(
        `${result.simulation?.mode ?? 'full_daily_cycle'} completed. SIMULATED ONLY. NO REAL MONEY. NO BROKER CONNECTED.`,
      )
    } catch (requestError) {
      setCycleMessage(
        `${requestError.message || 'Daily cycle failed.'} No real trades were executed.`,
      )
    } finally {
      setIsCycleRunning(false)
    }
  }

  if (isLoading) {
    return <section className="dashboard-state">Loading Operations Center...</section>
  }

  if (error) {
    return <section className="dashboard-state dashboard-state--error">{error}</section>
  }

  return (
    <div className="operations-page">
      <section className="operations-hero">
        <div>
          <p className="eyebrow">Operations Center</p>
          <h2>Atlas Daily Operating State</h2>
          <p>
            SIMULATED ONLY. NO BROKER CONNECTED. NO REAL MONEY. This page summarizes
            research, provider, paper trading, macro, and catalyst status.
          </p>
        </div>
        <div className="operations-hero__badges">
          <span>SIMULATED ONLY</span>
          <span>NO BROKER CONNECTED</span>
          <span>NO REAL MONEY</span>
        </div>
        <div className="operations-cycle-action">
          <button
            disabled={isCycleRunning}
            onClick={handleRunDailyCycle}
            type="button"
          >
            {isCycleRunning ? 'Running daily cycle...' : 'Run Full Daily Cycle'}
          </button>
          <span>
            {cycleMessage || `${data.dailyCycle?.daily_cycle_runs?.length ?? 0} saved cycle phases`}
          </span>
        </div>
      </section>

      <section className="operations-grid operations-grid--wide">
        <MarketStatusCard marketStatus={data.marketStatus} />
        <DataProviderCard provider={data.marketProvider} />
        <MarketHealthCard marketHealth={data.marketHealth} />
      </section>

      <OperationsSummary
        catalystSummary={data.catalystSummary}
        dashboard={data.dashboard}
        macroSummary={data.macroSummary}
        paperPerformance={data.paperPerformance}
        runtimeStatus={data.runtimeStatus}
      />

      <RuntimeStatusCard
        paperPerformance={data.paperPerformance}
        runtimeStatus={data.runtimeStatus}
      />

      <DailyJournalCard dailyJournal={data.dailyJournal} />

      <OperationsResearchLab researchLab={data.researchLab} />

      <OperationsLearningIntelligence />

      <section className="operations-grid">
        <OperationsAlerts
          catalystSummary={data.catalystSummary}
          macroSummary={data.macroSummary}
          paperPerformance={data.paperPerformance}
          providerHealth={data.providerHealth}
        />
        <OperationsPaperPortfolio
          paperPerformance={data.paperPerformance}
          paperPortfolio={data.paperPortfolio}
        />
      </section>

      <section className="operations-grid operations-grid--wide">
        <OperationsPerformance
          dashboard={data.dashboard}
          paperPerformance={data.paperPerformance}
        />
        <OperationsProviders providerHealth={data.providerHealth} />
        <OperationsCatalysts
          catalystSummary={data.catalystSummary}
          macroSummary={data.macroSummary}
        />
      </section>
    </div>
  )
}

export default OperationsCenter
