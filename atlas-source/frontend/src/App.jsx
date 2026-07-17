import { lazy, Suspense, useCallback, useState } from 'react'
import AppLayout from './layouts/AppLayout'
import { LoadingState } from './components/ui/States'

// Lazy-loaded routes: each page (and its heavy deps like Recharts) is a
// separate chunk, so the initial load only pulls the active page.
const DashboardV3 = lazy(() => import('./pages/DashboardV3'))
const RecommendationExplorer = lazy(() => import('./pages/RecommendationExplorer'))
const ResearchMemory = lazy(() => import('./pages/ResearchMemory'))
const LearningCenter = lazy(() => import('./pages/LearningCenter'))
const DashboardV2 = lazy(() => import('./pages/DashboardV2'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const AtlasBrain = lazy(() => import('./pages/AtlasBrain'))
const OperationsCenter = lazy(() => import('./pages/OperationsCenter'))
const ResearchWorkspace = lazy(() => import('./pages/ResearchWorkspace'))
const ResearchLab = lazy(() => import('./pages/ResearchLab'))
const StrategyLab = lazy(() => import('./pages/StrategyLab'))
const Analytics = lazy(() => import('./pages/Analytics'))
const PerformanceLab = lazy(() => import('./pages/PerformanceLab'))
const SelfImprovement = lazy(() => import('./pages/SelfImprovement'))
const MarketRegime = lazy(() => import('./pages/MarketRegime'))
const History = lazy(() => import('./pages/History'))
const Portfolio = lazy(() => import('./pages/Portfolio'))
const PaperTrading = lazy(() => import('./pages/PaperTrading'))
const Settings = lazy(() => import('./pages/Settings'))
const Learning = lazy(() => import('./pages/Learning'))
const Risk = lazy(() => import('./pages/Risk'))

const pages = {
  DashboardV3,
  RecommendationExplorer,
  ResearchMemory,
  LearningCenter,
  DashboardV2,
  Dashboard,
  AtlasBrain,
  OperationsCenter,
  ResearchWorkspace,
  ResearchLab,
  StrategyLab,
  Analytics,
  PerformanceLab,
  SelfImprovement,
  MarketRegime,
  History,
  Portfolio,
  PaperTrading,
  Settings,
  Learning,
  Risk,
}

function App() {
  const [activePage, setActivePage] = useState('DashboardV3')
  const handleNavigate = useCallback((key) => setActivePage(key), [])
  const ActivePage = pages[activePage] ?? DashboardV3

  return (
    <AppLayout activePage={activePage} onNavigate={handleNavigate}>
      <Suspense fallback={<LoadingState label="Loading…" />}>
        <ActivePage />
      </Suspense>
    </AppLayout>
  )
}

export default App
