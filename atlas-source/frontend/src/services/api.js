const API_BASE_URL = import.meta.env.VITE_ATLAS_API_URL ?? 'http://127.0.0.1:8000'

async function requestJson(path, label, options = {}) {
  const url = `${API_BASE_URL}${path}`

  try {
    const response = await fetch(url, options)

    if (!response.ok) {
      const detail = await response.text()
      const message = detail ? `: ${detail}` : ''
      throw new Error(`${label} failed at ${url} with status ${response.status}${message}`)
    }

    return response.json()
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        `${label} could not reach ${url}. Check that FastAPI is running and CORS allows the Vite origin.`,
        { cause: error },
      )
    }

    throw error
  }
}

export async function getDashboard() {
  return requestJson('/dashboard', 'Dashboard request')
}

export async function getDashboardV2() {
  return requestJson('/dashboard/v2', 'Dashboard v2 request')
}

export async function runAtlas() {
  return requestJson('/run', 'Run request', {
    method: 'POST',
  })
}

export async function getHistory() {
  return requestJson('/history', 'History request')
}

export async function getHistoryRun(runId) {
  return requestJson(`/history/${runId}`, 'History detail request')
}

export async function getRecommendationHistory(limit = 500) {
  const suffix = limit ? `?limit=${encodeURIComponent(limit)}` : ''
  return requestJson(`/recommendations/history${suffix}`, 'Recommendation history request')
}

export async function getRecommendationIntelligenceRecords(limit = 10000) {
  const suffix = limit ? `?limit=${encodeURIComponent(limit)}` : ''
  return requestJson(
    `/recommendation-intelligence/records${suffix}`,
    'Recommendation outcome records request',
  )
}

export async function getLearningCenter(filters = {}) {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      params.set(key, String(value))
    }
  })
  const suffix = params.toString() ? `?${params.toString()}` : ''
  return requestJson(`/learning-center${suffix}`, 'Learning Center request')
}

export async function getLearningCenterStatus(limit = 10000) {
  return requestJson(
    `/learning-center/status?limit=${encodeURIComponent(limit)}`,
    'Learning Center status request',
  )
}

export async function getRecommendationOutcomes(recommendationId) {
  return requestJson(
    `/recommendations/${encodeURIComponent(recommendationId)}/outcomes`,
    'Recommendation outcomes request',
  )
}

export async function getInstitutionalReport(ticker) {
  return requestJson(`/institutional-report/${ticker}`, 'Institutional report request')
}

export async function getResearchMemory(ticker) {
  const suffix = ticker ? `?ticker=${encodeURIComponent(ticker)}` : ''
  return requestJson(`/research-memory${suffix}`, 'Research memory request')
}

export async function getCaseStudies() {
  return requestJson('/case-studies', 'Case studies request')
}

export async function getCatalysts() {
  return requestJson('/catalysts', 'Catalysts request')
}

export async function getProviders() {
  return requestJson('/providers', 'Providers request')
}

export async function getProviderHealth() {
  return requestJson('/provider-health', 'Provider health request')
}

export async function getPaperPortfolio() {
  return requestJson('/paper-portfolio', 'Paper portfolio request')
}

export async function getPaperTrades() {
  return requestJson('/paper-trades', 'Paper trades request')
}

export async function getPaperPerformance() {
  return requestJson('/paper-performance', 'Paper performance request')
}

export async function getPaperTradingStatus() {
  return requestJson('/paper-trading/status', 'Paper trading status request')
}

export async function getPaperReplayHealth() {
  return requestJson('/paper-replay/health', 'Paper replay health request')
}

export async function getPaperBrokerStatus() {
  return requestJson('/paper-broker/status', 'Paper broker status request')
}

export async function getPaperFundStatus() {
  return requestJson('/paper-fund/status', 'Paper fund status request')
}

export async function startPaperFund(payload) {
  return requestJson('/paper-fund/start', 'Paper fund start request', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function pausePaperFund() {
  return requestJson('/paper-fund/pause', 'Paper fund pause request', { method: 'POST' })
}

export async function resumePaperFund() {
  return requestJson('/paper-fund/resume', 'Paper fund resume request', { method: 'POST' })
}

export async function stopPaperFund() {
  return requestJson('/paper-fund/stop', 'Paper fund stop request', { method: 'POST' })
}

export async function resetPaperFund() {
  return requestJson('/paper-fund/reset', 'Paper fund reset request', { method: 'POST' })
}

export async function runPaperFundCycle() {
  return requestJson('/paper-fund/cycle', 'Paper fund cycle request', { method: 'POST' })
}

export async function runPaperReplay(payload) {
  return requestJson('/paper-replay/run', 'Paper replay request', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function runDailyCycle() {
  return requestJson('/daily-cycle/run', 'Daily cycle request', {
    method: 'POST',
  })
}

export async function resetPaperSimulation() {
  return requestJson('/paper-sim/reset', 'Paper simulation reset request', {
    method: 'POST',
  })
}

export async function getPortfolioConstruction() {
  return requestJson('/portfolio-construction', 'Portfolio construction request')
}

export async function getAllocation() {
  return requestJson('/allocation', 'Allocation request')
}

export async function getRebalance() {
  return requestJson('/rebalance', 'Rebalance request')
}

export async function getRiskBudget() {
  return requestJson('/risk-budget', 'Risk budget request')
}

export async function getScientificValidation() {
  return requestJson('/scientific-validation', 'Scientific validation request')
}

export async function getResearchLab() {
  return requestJson('/research-lab', 'Research lab request')
}

export async function getStrategies() {
  return requestJson('/strategies', 'Strategy registry request')
}

export async function getStrategyComparison() {
  return requestJson('/strategies/compare', 'Strategy comparison request')
}

export async function getStrategy(strategyId) {
  return requestJson(
    `/strategies/${encodeURIComponent(strategyId)}`,
    'Strategy detail request',
  )
}

export async function getCommitteeMembers() {
  return requestJson('/committee/members', 'Committee members request')
}

export async function getCommitteeEvaluation(ticker) {
  return requestJson(
    `/committee/evaluate/${encodeURIComponent(ticker)}`,
    'Committee evaluation request',
  )
}

export async function getBrain(ticker) {
  return requestJson(`/brain/${encodeURIComponent(ticker)}`, 'Atlas Brain request')
}

export async function getBrainSummary(ticker) {
  return requestJson(`/brain/summary/${encodeURIComponent(ticker)}`, 'Atlas Brain summary request')
}

export async function getBrainEvidence(ticker) {
  return requestJson(`/brain/evidence/${encodeURIComponent(ticker)}`, 'Atlas Brain evidence request')
}

export async function getBrainTimeline(ticker) {
  return requestJson(`/brain/timeline/${encodeURIComponent(ticker)}`, 'Atlas Brain timeline request')
}

export async function getMarketStatus() {
  return requestJson('/market/status', 'Market status request')
}

export async function getMarketProvider() {
  return requestJson('/market/provider', 'Market provider request')
}

export async function getMarketHealth() {
  return requestJson('/market/health', 'Market health request')
}

export async function getMarketCache() {
  return requestJson('/market/cache', 'Market cache request')
}

export async function getAnalytics() {
  return requestJson('/analytics', 'Analytics request')
}

export async function getAnalyticsEquity() {
  return requestJson('/analytics/equity', 'Analytics equity request')
}

export async function getAnalyticsBenchmarks() {
  return requestJson('/analytics/benchmarks', 'Analytics benchmarks request')
}

export async function getAnalyticsCalibration() {
  return requestJson('/analytics/calibration', 'Analytics calibration request')
}

export async function getAnalyticsResearch() {
  return requestJson('/analytics/research', 'Analytics research request')
}

export async function getPerformanceLab() {
  return requestJson('/performance-lab', 'Performance Lab request')
}

export async function getSelfImprovement() {
  return requestJson('/self-improvement', 'Self-Improvement request')
}

export async function getMarketRegime() {
  return requestJson('/market-regime', 'Market Regime request')
}

export async function getLatestMonthlyReport() {
  return requestJson('/monthly-report/latest', 'Monthly report request')
}

export async function getExperiments() {
  return requestJson('/experiments', 'Experiments request')
}

export async function getExperimentHistory(filters = {}) {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      params.append(key, value)
    }
  })
  const suffix = params.toString() ? `?${params.toString()}` : ''
  return requestJson(`/experiments/history${suffix}`, 'Experiment history request')
}

export async function getActiveExperiments() {
  return requestJson('/experiments/active', 'Active experiments request')
}

export async function getLatestValidation() {
  return requestJson('/validation/latest', 'Latest validation request')
}

export async function getDailyJournal() {
  return requestJson('/daily-journal', 'Daily journal request')
}

export async function getDailyCycle() {
  return requestJson('/daily-cycle', 'Daily cycle request')
}

export async function getLatestDailyJournal() {
  return requestJson('/daily-journal/latest', 'Latest daily journal request')
}

export async function getCatalystSummary() {
  return requestJson('/catalyst-summary', 'Catalyst summary request')
}

export async function getMacroSummary() {
  return requestJson('/macro-summary', 'Macro summary request')
}

export async function getRuntime() {
  return requestJson('/runtime', 'Runtime request')
}

export async function getRuntimeStatus() {
  return requestJson('/runtime/status', 'Runtime status request')
}

export async function getRuntimeTasks() {
  return requestJson('/runtime/tasks', 'Runtime tasks request')
}
