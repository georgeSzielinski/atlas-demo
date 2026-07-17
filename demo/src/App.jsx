import { Component, lazy, Suspense, useCallback, useState } from 'react'
import AppLayout from './layouts/AppLayout'
import { LoadingState } from './components/ui/States'

// Lazy-loaded routes: each page (and its heavy deps like Recharts) is a
// separate chunk, so the initial load only pulls the active page.
const DashboardV3 = lazy(() => import('./pages/DashboardV3'))
const RecommendationExplorer = lazy(() => import('./pages/RecommendationExplorer'))
const ResearchMemory = lazy(() => import('./pages/ResearchMemory'))
const LearningCenter = lazy(() => import('./pages/LearningCenter'))

const pages = {
  DashboardV3,
  RecommendationExplorer,
  ResearchMemory,
  LearningCenter,
}

function App() {
  const [activePage, setActivePage] = useState('DashboardV3')
  const handleNavigate = useCallback((key) => setActivePage(key), [])
  const ActivePage = pages[activePage] ?? DashboardV3

  return (
    <AppLayout activePage={activePage} onNavigate={handleNavigate}>
      <DemoErrorBoundary>
        <Suspense fallback={<LoadingState label="Loading…" />}>
          <ActivePage />
        </Suspense>
      </DemoErrorBoundary>
    </AppLayout>
  )
}

class DemoErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return <p role="alert">Fixture view failed to load: {this.state.error.message}</p>
    }
    return this.props.children
  }
}

export default App
