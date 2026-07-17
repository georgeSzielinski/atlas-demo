import { memo, useMemo } from 'react'
import Panel from '../ui/Panel'
import StatTile from '../ui/StatTile'
import StatusPill from '../ui/StatusPill'
import GradeBadge from '../ui/GradeBadge'
import MeterBar from '../ui/MeterBar'
import Timeline from '../ui/Timeline'
import DonutChart from '../charts/DonutChart'
import KVList from '../ui/KVList'
import { EmptyState } from '../ui/States'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { portfolioIntelligence } from '../../services/portfolioIntel'
import { formatClock } from '../../services/paperFundOps'
import {
  formatCurrency,
  formatNumber,
  formatPercent,
  formatSignedPercent,
  toneForDelta,
} from '../../services/formatters'

// Row — Portfolio Intelligence. A read-only deep dive into how the paper
// portfolio is performing, why, and how reliable the process has been. Every
// value comes from the shared /dashboard/v2 payload; the whole model is
// computed once and passed down to calm, primitive-based sub-panels.
function PortfolioIntelligence() {
  const { data } = useDashboardData()
  const model = useMemo(() => portfolioIntelligence(data), [data])

  return (
    <section className="dv3-intel-portfolio" aria-label="Portfolio Intelligence">
      <div className="dv3-pi-heading">
        <span className="dv3-report__eyebrow">Portfolio Intelligence</span>
        <h2 className="dv3-pi-heading__title">Performance, Health & Process</h2>
      </div>

      <SummaryPanel summary={model.summary} />

      <div className="dv2-row dv2-row--2">
        <AttributionPanel attribution={model.attribution} />
        <HealthPanel health={model.health} />
      </div>

      <div className="dv2-row dv2-row--2">
        <CommitteePanel committee={model.committee} />
        <LearningPanel learning={model.learning} />
      </div>

      <TimelinePanel timeline={model.timeline} />
    </section>
  )
}

function SummaryPanel({ summary }) {
  return (
    <Panel eyebrow="Portfolio" title="Portfolio Summary" className="dv2-panel--wide">
      {!summary.available ? (
        <EmptyState
          title="Portfolio not started"
          message="The paper fund holds no capital yet. Summary metrics appear once the fund runs its first cycle."
        />
      ) : (
        <div className="dv3-pi-summary">
          <StatTile label="Portfolio Value" value={fmtCurrency(summary.portfolioValue)} hint="paper, simulated" />
          <StatTile label="Cash" value={fmtCurrency(summary.cash)} />
          <StatTile label="Invested" value={fmtCurrency(summary.invested)} />
          <StatTile
            label="Total Return"
            value={formatSignedPercent(summary.totalReturn, { fallback: '—' })}
            deltaTone={toneForDelta(summary.totalReturn)}
          />
          <StatTile
            label="Realized P/L"
            value={fmtCurrency(summary.realizedPl)}
            deltaTone={toneForDelta(summary.realizedPl)}
          />
          <StatTile
            label="Unrealized P/L"
            value={fmtCurrency(summary.unrealizedPl)}
            deltaTone={toneForDelta(summary.unrealizedPl)}
          />
          <StatTile label="Open Positions" value={`${summary.openPositions}`} />
          <StatTile
            label="Last Update"
            value={summary.lastUpdate ? formatClock(summary.lastUpdate) : '—'}
          />
        </div>
      )}
    </Panel>
  )
}

function AttributionPanel({ attribution }) {
  const rows = [
    ['Best position', contribLabel(attribution.best)],
    ['Worst position', contribLabel(attribution.worst)],
    ['Largest contributor', driverLabel(attribution.largestContributor)],
    ['Largest detractor', driverLabel(attribution.largestDetractor)],
    [
      'Cash drag',
      attribution.cashDrag
        ? `${formatSignedPercent(attribution.cashDrag.contribution, { fallback: 'n/a' })} · ${formatPercent(attribution.cashDrag.weightPercent, { fallback: 'n/a' })} weight`
        : null,
    ],
  ]
  return (
    <Panel eyebrow="Performance" title="Performance Attribution">
      {!attribution.available ? (
        <EmptyState
          title="Not evaluated"
          message="No attributable position-level P/L is available yet. Attribution appears once the fund holds positions with recorded returns."
        />
      ) : (
        <>
          <KVList rows={rows} emptyMessage="No attribution metrics available." />
          {attribution.sectors.length > 0 ? (
            <>
              <span className="dv3-report__subhead">Sector contribution</span>
              {attribution.sectors.slice(0, 5).map((sector) => (
                <MeterBar
                  key={sector.sector}
                  value={Math.abs(sector.contribution ?? 0)}
                  tone={(sector.contribution ?? 0) >= 0 ? 'positive' : 'warn'}
                  label={`${sector.sector} · ${formatSignedPercent(sector.contribution, { fallback: 'n/a' })}`}
                />
              ))}
            </>
          ) : null}
        </>
      )}
    </Panel>
  )
}

function HealthPanel({ health }) {
  return (
    <Panel eyebrow="Risk" title="Portfolio Health">
      {!health.available ? (
        <EmptyState
          title="Not evaluated"
          message="Portfolio health metrics appear once positions and risk decisions are recorded."
        />
      ) : (
        <>
          <MeterBar
            value={health.score ?? 0}
            tone={health.score >= 70 ? 'positive' : health.score >= 40 ? 'accent' : 'warn'}
            label={`Health score ${health.score !== null ? formatNumber(health.score) : 'n/a'} / 100`}
          />
          <div className="dv3-pi-health__pills">
            {health.scoreStatus ? <StatusPill status={health.scoreStatus} label={health.scoreStatus} /> : null}
            {health.cashReserve.available ? (
              <StatusPill status={health.cashReserve.status ?? 'EVALUATED'} label={`Cash ${formatPercent(health.cashReserve.percent, { fallback: 'n/a' })}`} />
            ) : null}
          </div>
          <KVList
            rows={[
              [
                'Concentration risk',
                health.concentration.available
                  ? formatPercent(health.concentration.percent, { fallback: 'n/a' })
                  : null,
              ],
              ['Largest position', health.concentration.symbol],
              ['Largest sector', health.largestSector],
              [
                'Risk decisions',
                health.riskUtilization.available
                  ? `${health.riskUtilization.decisions} (${health.riskUtilization.rejected} rejected)`
                  : null,
              ],
            ]}
            emptyMessage="No health details available."
          />
          {health.sectors.length > 0 ? (
            <DonutChart data={health.sectors} height={200} emptyMessage="No sector exposure yet." />
          ) : null}
        </>
      )}
    </Panel>
  )
}

function CommitteePanel({ committee }) {
  return (
    <Panel eyebrow="Process" title="Committee Performance">
      {!committee.available ? (
        <EmptyState
          title="Not evaluated"
          message="No committee evaluations are recorded yet. Run an autonomous research cycle to populate committee performance."
        />
      ) : (
        <>
          <div className="dv3-pi-committee">
            <StatTile label="Recommendations" value={`${committee.recommendationCount}`} />
            <StatTile label="Completed" value={`${committee.completed}`} />
            <StatTile
              label="Agreement"
              value={formatPercent(committee.agreementPercent, { fallback: '—' })}
            />
            <StatTile
              label="Reliability"
              value={<GradeBadge grade={committee.reliabilityGrade} score={committee.reliabilityScore} />}
            />
          </div>
          <div className="dv3-pi-verdicts">
            <StatusPill status="BUY" tone="positive" label={`BUY ${committee.buy}`} />
            <StatusPill status="HOLD" tone="neutral" label={`HOLD ${committee.hold}`} />
            <StatusPill status="AVOID" tone="negative" label={`AVOID ${committee.avoid}`} />
          </div>
          {!committee.outcomesAvailable ? (
            <small className="dv3-report__note">
              Outcome accuracy is not shown: no historical recommendation outcomes have been
              evaluated yet.
            </small>
          ) : null}
        </>
      )}
    </Panel>
  )
}

function LearningPanel({ learning }) {
  return (
    <Panel eyebrow="Process" title="Learning Status">
      {!learning.available ? (
        <EmptyState
          title="Not evaluated"
          message="The learning loop has recorded no entries yet. Lessons accrue as simulated cycles complete."
        />
      ) : (
        <>
          <div className="dv3-pi-committee">
            <StatTile
              label="Learning"
              value={<StatusPill status={learning.active ? 'RUNNING' : 'OFF'} label={learning.active ? 'Active' : 'Idle'} />}
            />
            <StatTile label="Entries" value={`${learning.entries}`} />
            <StatTile
              label="Confidence"
              value={learning.confidenceLevel ?? '—'}
              hint={learning.coverage ? `coverage ${learning.coverage}` : 'coverage n/a'}
            />
            <StatTile
              label="History"
              value={learning.historyAvailable === null ? '—' : learning.historyAvailable ? 'Yes' : 'No'}
              hint="historical telemetry"
            />
          </div>
          {learning.latestLesson ? (
            <p className="dv3-intel__lesson">“{learning.latestLesson}”</p>
          ) : (
            <small className="dv3-report__note">No lesson has been recorded yet.</small>
          )}
        </>
      )}
    </Panel>
  )
}

function TimelinePanel({ timeline }) {
  return (
    <Panel eyebrow="Activity" title="Portfolio Timeline" className="dv2-panel--wide">
      <Timeline
        events={timeline.events.map((event) => ({ ...event, at: event.at ? formatClock(event.at) : null }))}
        emptyMessage="No portfolio activity has been recorded yet."
        max={12}
      />
    </Panel>
  )
}

// Currency that shows an em dash (not "$0.00") when the value is truly absent.
function fmtCurrency(value) {
  return value === null || value === undefined ? '—' : formatCurrency(value)
}

function contribLabel(item) {
  if (!item || !item.symbol) return null
  const pct = formatSignedPercent(item.contributionPercent, { fallback: null })
  return pct ? `${item.symbol} · ${pct}` : item.symbol
}

function driverLabel(item) {
  if (!item || !item.symbol) return null
  const value = item.value !== null ? formatCurrency(item.value) : null
  return value ? `${item.symbol} · ${value}` : item.symbol
}

export default memo(PortfolioIntelligence)
