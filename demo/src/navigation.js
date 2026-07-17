// Single source of truth for navigation: the sidebar renders these, and the
// header derives its human-readable title from the same list (so pages never
// show their raw route key).

export const primaryNav = [
  { key: 'DashboardV3', label: 'Mission Control' },
  { key: 'RecommendationExplorer', label: 'Recommendation Explorer' },
  { key: 'ResearchMemory', label: 'Research Memory' },
  { key: 'LearningCenter', label: 'Learning Center' },
]

export const secondaryNav = []

const ALL_NAV = [...primaryNav, ...secondaryNav]

export function pageTitle(key) {
  return ALL_NAV.find((item) => item.key === key)?.label ?? key
}
