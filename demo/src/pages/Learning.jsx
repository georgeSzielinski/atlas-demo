import { DashboardDataProvider, useDashboardData } from '../context/DashboardDataProvider'
import { LoadingState, ErrorState } from '../components/ui/States'
import LearningPanel from '../components/dashboard/LearningPanel'
import ReliabilityPanel from '../components/dashboard/ReliabilityPanel'
import EventsTimeline from '../components/dashboard/EventsTimeline'

function LearningBody() {
  const { data, isLoading, error } = useDashboardData()
  if (isLoading && !data) {
    return <LoadingState label="Loading learning…" />
  }
  if (error && !data) {
    return <ErrorState message={error.message} />
  }
  return (
    <div className="dv2-page">
      <div className="dv2-row dv2-row--2">
        <LearningPanel />
        <ReliabilityPanel />
      </div>
      <EventsTimeline />
    </div>
  )
}

function Learning() {
  return (
    <DashboardDataProvider>
      <LearningBody />
    </DashboardDataProvider>
  )
}

export default Learning
