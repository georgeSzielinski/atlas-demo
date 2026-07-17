import { DashboardDataProvider, useDashboardData } from '../context/DashboardDataProvider'
import Panel from '../components/ui/Panel'
import KVList from '../components/ui/KVList'
import StatusPill from '../components/ui/StatusPill'
import { LoadingState, ErrorState } from '../components/ui/States'
import { formatValue } from '../services/formatters'

function SettingsBody() {
  const { data, isLoading, error } = useDashboardData()

  if (isLoading && !data) {
    return <LoadingState label="Loading settings…" />
  }
  if (error && !data) {
    return <ErrorState message={error.message} />
  }

  const operations = data?.operations ?? {}
  const mode = operations.operational_mode ?? {}
  const market = data?.market ?? {}
  const scheduler = data?.scheduler ?? {}
  const policy = data?.policy ?? {}

  const modeRows = [
    ['Operational Mode', formatValue(mode.mode)],
    ['Data Provider', formatValue(mode.data_provider)],
    ['Auto Fund Enabled', formatValue(mode.auto_fund_enabled)],
    ['Scheduler Enabled', formatValue(mode.scheduler_enabled)],
    ['Market Provider', formatValue(market.active_provider)],
    ['Scheduler Interval (s)', formatValue(scheduler.interval_seconds)],
  ]
  const policyRows = Object.entries(policy).map(([key, value]) => [
    key.replace(/_/g, ' '),
    String(value),
  ])

  return (
    <div className="dv2-page">
      <div className="dv2-row dv2-row--2">
        <Panel
          eyebrow="Settings"
          title="Runtime Configuration"
          action={<StatusPill status={mode.mode ?? 'OFFLINE_MOCK'} label={mode.mode ?? 'OFFLINE_MOCK'} tone="neutral" />}
        >
          <KVList rows={modeRows} />
        </Panel>
        <Panel eyebrow="Settings" title="Read-only Policy">
          <KVList rows={policyRows} emptyMessage="Policy metadata unavailable." />
        </Panel>
      </div>
    </div>
  )
}

// Read-only settings view: reflects operational config from /dashboard/v2.
function Settings() {
  return (
    <DashboardDataProvider>
      <SettingsBody />
    </DashboardDataProvider>
  )
}

export default Settings
