import { DashboardDataProvider, useDashboardData } from '../context/DashboardDataProvider'
import { LoadingState, ErrorState } from '../components/ui/States'
import ExecutiveBriefing from '../components/mission/ExecutiveBriefing'
import MissionKpiRow from '../components/mission/MissionKpiRow'
import OperationsCenterPanel from '../components/mission/OperationsCenterPanel'
import CommitteeBoard from '../components/mission/CommitteeBoard'
import ResearchTimeline from '../components/mission/ResearchTimeline'
import PortfolioOverview from '../components/mission/PortfolioOverview'
import PortfolioIntelligence from '../components/mission/PortfolioIntelligence'
import SystemIntelligencePanel from '../components/mission/SystemIntelligencePanel'
import LearningHealthPanel from '../components/mission/LearningHealthPanel'

// Dashboard V3 — Mission Control. A calm, institutional operations view built
// entirely from the single /dashboard/v2 payload (one shared request via the
// provider). Six stacked rows answer "is Atlas healthy, what did it just do,
// and what does it recommend" within ten seconds.
function MissionControlBody() {
  const { data, isLoading, error } = useDashboardData()

  if (isLoading && !data) {
    return <LoadingState label="Loading Mission Control…" />
  }
  if (error && !data) {
    return <ErrorState message={error.message} />
  }

  return (
    <div className="dv2-page dv3-page">
      <ExecutiveBriefing />
      <MissionKpiRow />
      <LearningHealthPanel />
      <OperationsCenterPanel />
      <CommitteeBoard />
      <ResearchTimeline />
      <PortfolioOverview />
      <PortfolioIntelligence />
      <SystemIntelligencePanel />
    </div>
  )
}

function DashboardV3() {
  return (
    <DashboardDataProvider>
      <MissionControlBody />
    </DashboardDataProvider>
  )
}

export default DashboardV3
