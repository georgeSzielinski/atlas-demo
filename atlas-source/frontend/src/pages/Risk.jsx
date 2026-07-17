import { DashboardDataProvider, useDashboardData } from '../context/DashboardDataProvider'
import { LoadingState, ErrorState } from '../components/ui/States'
import RiskPanel from '../components/dashboard/RiskPanel'
import CorrelationPanel from '../components/dashboard/CorrelationPanel'
import ScenarioPanel from '../components/dashboard/ScenarioPanel'

function RiskBody() {
  const { data, isLoading, error } = useDashboardData()
  if (isLoading && !data) {
    return <LoadingState label="Loading risk…" />
  }
  if (error && !data) {
    return <ErrorState message={error.message} />
  }
  return (
    <div className="dv2-page">
      <div className="dv2-row dv2-row--3">
        <RiskPanel />
        <CorrelationPanel />
        <ScenarioPanel />
      </div>
    </div>
  )
}

function Risk() {
  return (
    <DashboardDataProvider>
      <RiskBody />
    </DashboardDataProvider>
  )
}

export default Risk
