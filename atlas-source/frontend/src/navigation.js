// Single source of truth for navigation: the sidebar renders these, and the
// header derives its human-readable title from the same list (so pages never
// show their raw route key).

export const primaryNav = [
  { key: 'DashboardV3', label: 'Mission Control' },
  { key: 'RecommendationExplorer', label: 'Recommendation Explorer' },
  { key: 'ResearchMemory', label: 'Research Memory' },
  { key: 'LearningCenter', label: 'Learning Center' },
  { key: 'DashboardV2', label: 'Dashboard (v2)' },
  { key: 'Portfolio', label: 'Portfolio' },
  { key: 'Analytics', label: 'Analytics' },
  { key: 'PerformanceLab', label: 'Performance Lab' },
  { key: 'SelfImprovement', label: 'Self-Improvement' },
  { key: 'MarketRegime', label: 'Market Regime' },
  { key: 'Learning', label: 'Learning' },
  { key: 'Risk', label: 'Risk' },
  { key: 'OperationsCenter', label: 'Operations' },
  { key: 'Settings', label: 'Settings' },
]

export const secondaryNav = [
  { key: 'AtlasBrain', label: 'Brain' },
  { key: 'PaperTrading', label: 'Paper Trading' },
  { key: 'StrategyLab', label: 'Strategy Lab' },
  { key: 'ResearchLab', label: 'Research Lab' },
  { key: 'ResearchWorkspace', label: 'Research Workspace' },
  { key: 'History', label: 'History' },
  { key: 'Dashboard', label: 'Dashboard (Legacy)' },
]

const ALL_NAV = [...primaryNav, ...secondaryNav]

export function pageTitle(key) {
  return ALL_NAV.find((item) => item.key === key)?.label ?? key
}
