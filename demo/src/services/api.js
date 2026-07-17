import { resolveDemoRequest } from './demoFixtures'

async function requestJson(path, label) {
  try {
    return resolveDemoRequest(path)
  } catch (error) {
    throw new Error(`${label} is unavailable in the static Atlas demo: ${error.message}`, {
      cause: error,
    })
  }
}

export async function getDashboardV2() {
  return requestJson('/dashboard/v2', 'Dashboard v2 request')
}

export async function getRecommendationHistory(limit = 500) {
  return requestJson(
    `/recommendations/history?limit=${encodeURIComponent(limit)}`,
    'Recommendation history request',
  )
}

export async function getRecommendationIntelligenceRecords(limit = 10000) {
  return requestJson(
    `/recommendation-intelligence/records?limit=${encodeURIComponent(limit)}`,
    'Recommendation outcome records request',
  )
}

export async function getLearningCenter(filters = {}) {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') params.set(key, String(value))
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
  return requestJson(`/institutional-report/${encodeURIComponent(ticker)}`, 'Institutional report request')
}
