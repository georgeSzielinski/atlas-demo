import { useEffect, useState } from 'react'
import BenchmarkComparison from '../components/BenchmarkComparison'
import CalibrationChart from '../components/CalibrationChart'
import EquityCurve from '../components/EquityCurve'
import LearningCurve from '../components/LearningCurve'
import MonthlyReport from '../components/MonthlyReport'
import PerformanceDashboard from '../components/PerformanceDashboard'
import ResearchProgress from '../components/ResearchProgress'
import { getAnalytics, getLatestMonthlyReport } from '../services/api'

async function safeLoad(loader, fallback) {
  try {
    return await loader()
  } catch {
    return fallback
  }
}

function Analytics() {
  const [analytics, setAnalytics] = useState(null)
  const [monthlyReport, setMonthlyReport] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let isCurrent = true

    async function loadAnalytics() {
      setIsLoading(true)
      try {
        const analyticsData = await getAnalytics()
        const monthly = await safeLoad(getLatestMonthlyReport, { monthly_report: null })
        if (!isCurrent) return
        setAnalytics(analyticsData)
        setMonthlyReport(monthly.monthly_report ?? analyticsData.monthly_report ?? null)
        setError('')
      } catch (requestError) {
        if (!isCurrent) return
        setError(requestError.message)
        setAnalytics(null)
      } finally {
        if (isCurrent) {
          setIsLoading(false)
        }
      }
    }

    loadAnalytics()

    return () => {
      isCurrent = false
    }
  }, [])

  if (isLoading) {
    return <section className="dashboard-state">Loading Performance Analytics...</section>
  }

  if (error && !analytics) {
    return (
      <section className="dashboard-state dashboard-state--error">
        {error} Start the FastAPI backend and refresh to load Performance Analytics.
      </section>
    )
  }

  const calibration = analytics?.recommendation_analytics ?? {}

  return (
    <div className="analytics-page">
      <section className="analytics-hero">
        <div>
          <p className="eyebrow">Performance Analytics</p>
          <h2>Should we trust Atlas more today than yesterday?</h2>
          <p>
            RESEARCH ONLY. PAPER TRADING. NO BROKER CONNECTED. NO REAL MONEY. Atlas does not
            claim improvement; it demonstrates it through measurable evidence.
          </p>
        </div>
        <div className="analytics-hero__badges">
          <span>DETERMINISTIC</span>
          <span>PAPER ONLY</span>
          {analytics?.demo_data ? <span>SIMULATED DEMO DATA</span> : null}
        </div>
      </section>

      <PerformanceDashboard analytics={analytics} />
      <EquityCurve equity={analytics?.equity_curve} />

      <div className="analytics-grid analytics-grid--two">
        <BenchmarkComparison benchmarks={analytics?.benchmark_comparison} />
        <CalibrationChart
          calibration={{
            confidence_calibration: calibration.confidence_calibration,
            probability_calibration: calibration.probability_calibration,
          }}
          recommendation={calibration}
        />
      </div>

      <LearningCurve learning={analytics?.learning_curve} />
      <ResearchProgress research={analytics?.research_progress} />
      <MonthlyReport report={monthlyReport} />
    </div>
  )
}

export default Analytics
