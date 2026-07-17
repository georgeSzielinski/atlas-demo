import { DashboardDataProvider, useDashboardData } from '../context/DashboardDataProvider'
import { LoadingState, ErrorState } from '../components/ui/States'
import TopStatusBar from '../components/dashboard/TopStatusBar'
import SystemStatusPanel from '../components/dashboard/SystemStatusPanel'
import NextCycleWidget from '../components/dashboard/NextCycleWidget'
import LiveEquityCurvePanel from '../components/dashboard/LiveEquityCurvePanel'
import PipelineMeter from '../components/dashboard/PipelineMeter'
import LiveTradesPanel from '../components/dashboard/LiveTradesPanel'
import ActivityPanel from '../components/dashboard/ActivityPanel'
import MarketTickerStrip from '../components/dashboard/MarketTickerStrip'
import FloatingEventsLayer from '../components/dashboard/FloatingTradeEvent'
import MissionControlPanel from '../components/dashboard/MissionControlPanel'
import LiveOpsTiles from '../components/dashboard/LiveOpsTiles'
import HoldingsPanel from '../components/dashboard/HoldingsPanel'
import AllocationPanel from '../components/dashboard/AllocationPanel'
import TradingHistoryPanel from '../components/dashboard/TradingHistoryPanel'
import CycleJournalPanel from '../components/dashboard/CycleJournalPanel'
import RiskRejectionPanel from '../components/dashboard/RiskRejectionPanel'
import LearningSummaryPanel from '../components/dashboard/LearningSummaryPanel'
import RiskPanel from '../components/dashboard/RiskPanel'
import CorrelationPanel from '../components/dashboard/CorrelationPanel'
import ScenarioPanel from '../components/dashboard/ScenarioPanel'
import LearningPanel from '../components/dashboard/LearningPanel'
import AlertsPanel from '../components/dashboard/AlertsPanel'
import ReliabilityPanel from '../components/dashboard/ReliabilityPanel'
import EventsTimeline from '../components/dashboard/EventsTimeline'

function DashboardBody() {
  const { data, isLoading, error } = useDashboardData()

  if (isLoading && !data) {
    return <LoadingState label="Loading Atlas dashboard…" />
  }
  if (error && !data) {
    return <ErrorState message={error.message} />
  }

  return (
    <div className="dv2-page dv2-page--command">
      <TopStatusBar />

      {/* Command center: system rail · live equity + pipeline · execution rail */}
      <div className="dv2-command">
        <div className="dv2-command__rail">
          <NextCycleWidget />
          <SystemStatusPanel />
        </div>
        <div className="dv2-command__center">
          <LiveEquityCurvePanel />
          <PipelineMeter />
        </div>
        <div className="dv2-command__rail">
          <LiveTradesPanel />
          <ActivityPanel />
        </div>
      </div>

      <MarketTickerStrip />

      <MissionControlPanel />
      <LiveOpsTiles />

      <div className="dv2-row dv2-row--2">
        <TradingHistoryPanel />
        <CycleJournalPanel />
      </div>

      <div className="dv2-row dv2-row--3">
        <AllocationPanel />
        <HoldingsPanel />
        <LearningSummaryPanel />
      </div>

      <div className="dv2-row dv2-row--3">
        <RiskRejectionPanel />
        <AlertsPanel />
        <ReliabilityPanel />
      </div>

      {/* Deeper analytics below — degrade to empty states when NOT_EVALUATED. */}
      <div className="dv2-row dv2-row--3">
        <RiskPanel />
        <CorrelationPanel />
        <ScenarioPanel />
      </div>

      <div className="dv2-row dv2-row--2">
        <LearningPanel />
        <EventsTimeline />
      </div>

      <FloatingEventsLayer />
    </div>
  )
}

// One provider => one GET /dashboard/v2 shared by every widget above.
function DashboardV2() {
  return (
    <DashboardDataProvider>
      <DashboardBody />
    </DashboardDataProvider>
  )
}

export default DashboardV2
