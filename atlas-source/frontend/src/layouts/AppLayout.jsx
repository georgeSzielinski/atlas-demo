import Header from '../components/Header'
import Sidebar from '../components/Sidebar'
import { pageTitle } from '../navigation'

function AppLayout({ activePage, children, onNavigate }) {
  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} onNavigate={onNavigate} />
      <main className="main-panel">
        <Header title={pageTitle(activePage)} />
        {children}
      </main>
    </div>
  )
}

export default AppLayout
