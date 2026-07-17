import { memo, useEffect, useMemo, useState } from 'react'
import Panel from '../ui/Panel'
import StatusPill from '../ui/StatusPill'
import GradeBadge from '../ui/GradeBadge'
import KVList from '../ui/KVList'
import Timeline from '../ui/Timeline'
import { EmptyState } from '../ui/States'
import BriefingMemo from './BriefingMemo'
import InstitutionalReportDrawer from './InstitutionalReportDrawer'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { executiveBriefing } from '../../services/executiveBriefing'
import { cycleCountdown, formatClock } from '../../services/paperFundOps'
import {
  formatConfidence,
  formatCurrency,
  formatPercent,
  formatSignedPercent,
} from '../../services/formatters'

// Executive Briefing — a calm, read-only daily memo above the KPI row. One
// shared /dashboard/v2 payload, one memoized view model, four concise columns
// and an events strip. No invented commentary, no predictions, no extra fetches.
function ExecutiveBriefing() {
  const { data } = useDashboardData()
  const briefing = useMemo(() => executiveBriefing(data, new Date()), [data])
  const [selectedCard, setSelectedCard] = useState(null)

  return (
    <Panel className="dv2-panel--wide dv3-briefing">
      <BriefingHeaderRow header={briefing.header} />

      <div className="dv3-briefing__grid">
        <PortfolioColumn portfolio={briefing.portfolio} />
        <MarketColumn market={briefing.market} />
        <ResearchColumn research={briefing.research} onOpenReport={setSelectedCard} />
        <LearningColumn learning={briefing.learning} />
      </div>

      <EventsStrip events={briefing.events} />

      <InstitutionalReportDrawer card={selectedCard} onClose={() => setSelectedCard(null)} />
    </Panel>
  )
}

function BriefingHeaderRow({ header }) {
  return (
    <header className="dv3-briefing__head">
      <div>
        <h2 className="dv3-briefing__greeting">{header.greeting}</h2>
        <p className="dv3-briefing__date">{header.date}</p>
      </div>
      <div className="dv3-briefing__badges">
        {header.mode ? <StatusPill status="EVALUATED" tone="neutral" label={`Mode: ${header.mode}`} /> : null}
        {header.paperOnly ? <StatusPill status="EVALUATED" tone="positive" label="Paper-only" /> : null}
        <span className="dv3-briefing__refresh">
          Refreshed {header.lastRefresh ? formatClock(header.lastRefresh) : '—'}
        </span>
      </div>
    </header>
  )
}

function PortfolioColumn({ portfolio }) {
  if (!portfolio.available) {
    return (
      <BriefingMemo eyebrow="Portfolio" title="Portfolio Brief">
        <EmptyState
          title="No positions yet"
          message="The paper fund holds no positions. Performance figures appear after the first simulated cycle."
        />
      </BriefingMemo>
    )
  }
  const contributors = [
    ['Best contributor', labelContribution(portfolio.best)],
    ['Worst contributor', labelContribution(portfolio.worst)],
  ]
  return (
    <BriefingMemo
      eyebrow="Portfolio"
      title="Portfolio Brief"
      status="EVALUATED"
      statusTone={portfolio.updatedToday ? 'positive' : 'muted'}
      statusLabel={portfolio.updatedToday ? 'Updated today' : 'No update today'}
    >
      <KVList
        rows={[
          ['Portfolio value', portfolio.portfolioValue !== null ? formatCurrency(portfolio.portfolioValue) : null],
          ['Total return', signed(portfolio.totalReturn)],
          ['Daily return', signed(portfolio.dailyReturn)],
          ['Realized P/L', portfolio.realizedPl !== null ? formatCurrency(portfolio.realizedPl) : null],
          ['Unrealized P/L', portfolio.unrealizedPl !== null ? formatCurrency(portfolio.unrealizedPl) : null],
          ['Cash', formatPercent(portfolio.cashPercent, { fallback: null })],
          ['Open positions', `${portfolio.openPositions}`],
        ]}
        emptyMessage="No portfolio metrics available."
      />
      {portfolio.attributionAvailable ? <KVList rows={contributors} emptyMessage="Attribution not evaluated." /> : null}
    </BriefingMemo>
  )
}

function MarketColumn({ market }) {
  const live = useLiveCountdown(market.nextCycle)
  return (
    <BriefingMemo
      eyebrow="Market & Runtime"
      title="Operating Status"
      status={market.marketOpen === null ? 'Unavailable' : market.marketOpen ? 'Open' : 'Closed'}
      statusLabel={market.marketOpen === null ? 'Unavailable' : market.marketOpen ? 'Market open' : 'Market closed'}
    >
      <KVList
        rows={[
          ['Session', market.session],
          ['Provider', providerLabel(market)],
          ['Scheduler', market.scheduler],
          ['Last tick', market.lastTick ? formatClock(market.lastTick) : null],
          ['Last cycle', market.lastCycleResult],
          ['Reason', market.lastCycleReason],
          ['Next cycle', market.nextCycle ? formatClock(market.nextCycle) : null],
          // A live countdown ONLY when a real next-cycle timestamp exists.
          ['Countdown', live ? (live.due ? 'Due now' : live.label) : null],
        ]}
        emptyMessage="No runtime status available."
      />
    </BriefingMemo>
  )
}

function ResearchColumn({ research, onOpenReport }) {
  if (!research.available) {
    return (
      <BriefingMemo eyebrow="Research & Committee" title="Latest Research">
        <EmptyState
          title="No recommendations"
          message={
            research.enabled
              ? 'The latest research cycle produced no recommendations yet.'
              : 'Autonomous research is disabled, so no new recommendations have been generated.'
          }
        />
      </BriefingMemo>
    )
  }
  return (
    <BriefingMemo eyebrow="Research & Committee" title="Latest Research">
      <div className="dv3-briefing__verdicts">
        <StatusPill status="BUY" tone="positive" label={`BUY ${research.buy}`} />
        <StatusPill status="HOLD" tone="neutral" label={`HOLD ${research.hold}`} />
        <StatusPill status="AVOID" tone="negative" label={`AVOID ${research.avoid}`} />
      </div>
      <KVList
        rows={[
          ['Recommendations', `${research.recommendationCount}`],
          ['Provider', research.provider],
          ['Latest', research.latestAt ? formatClock(research.latestAt) : null],
        ]}
        emptyMessage="No research metrics available."
      />
      <div className="dv3-briefing__recs">
        <RecChip label="Top confidence" card={research.highestConfidence} metric="confidence" onOpen={onOpenReport} />
        <RecChip label="Weakest agreement" card={research.weakestAgreement} metric="agreement" onOpen={onOpenReport} />
      </div>
      <small className="dv3-report__note">A recommendation is research only — it is not an executed trade.</small>
    </BriefingMemo>
  )
}

function RecChip({ label, card, metric, onOpen }) {
  if (!card) return null
  const value =
    metric === 'confidence'
      ? formatConfidence(card.confidence, { fallback: '—' })
      : formatPercent(card.agreementPct, { fallback: '—' })
  return (
    <button type="button" className="dv3-briefing__rec" onClick={() => onOpen(card)}>
      <span className="dv3-briefing__rec-k">{label}</span>
      <span className="dv3-briefing__rec-v">
        {card.ticker} · {card.action ?? 'N/A'} · {value}
      </span>
      <span className="dv3-briefing__rec-cta">Open report →</span>
    </button>
  )
}

function LearningColumn({ learning }) {
  const warnErr = learning.warningCount + learning.errorCount + learning.criticalCount
  return (
    <BriefingMemo
      eyebrow="Learning & Reliability"
      title="Process Health"
      status={learning.reliabilityGrade ? undefined : 'NOT_EVALUATED'}
    >
      <div className="dv3-briefing__reliability">
        <GradeBadge grade={learning.reliabilityGrade} score={learning.reliabilityScore} />
        {learning.reliabilityStatus ? (
          <span className="dv3-briefing__reliability-status">{learning.reliabilityStatus}</span>
        ) : null}
      </div>
      <KVList
        rows={[
          ['Learning', learning.learningActive ? 'Active' : 'Inactive'],
          ['Learning entries', `${learning.learningEntries}`],
          ['Incidents', `${learning.incidentCount}`],
          ['Warnings / errors', `${warnErr}`],
          ['Confidence', learning.confidenceLevel],
          ['Historical coverage', learning.historyAvailable === null ? null : learning.historyAvailable ? (learning.coverage ?? 'Yes') : 'Limited'],
        ]}
        emptyMessage="No reliability metrics available."
      />
      {learning.latestLesson ? (
        <p className="dv3-intel__lesson">“{learning.latestLesson}”</p>
      ) : (
        <small className="dv3-report__note">No lesson recorded yet.</small>
      )}
    </BriefingMemo>
  )
}

function EventsStrip({ events }) {
  return (
    <div className="dv3-briefing__events">
      <span className="dv3-report__eyebrow">Important events</span>
      {events.length === 0 ? (
        <EmptyState title="All clear" message="No critical events, failures, orders, or new recommendations to report." />
      ) : (
        <Timeline
          events={events.map((event) => ({
            title: event.title,
            detail: event.detail,
            at: event.at ? formatClock(event.at) : null,
            tone: event.tone === 'warn' ? 'neutral' : event.tone,
          }))}
          max={5}
        />
      )}
    </div>
  )
}

// Ticking countdown (1s) that only runs while a next-cycle timestamp exists.
function useLiveCountdown(nextCycle) {
  const [, setTick] = useState(0)
  useEffect(() => {
    if (!nextCycle) return undefined
    const id = setInterval(() => setTick((value) => value + 1), 1000)
    return () => clearInterval(id)
  }, [nextCycle])
  return nextCycle ? cycleCountdown(nextCycle) : null
}

function signed(value) {
  return formatSignedPercent(value, { fallback: null })
}

function labelContribution(item) {
  if (!item || !item.symbol) return null
  const pct = formatSignedPercent(item.contributionPercent, { fallback: null })
  return pct ? `${item.symbol} · ${pct}` : item.symbol
}

function providerLabel(market) {
  if (!market.provider) return null
  if (market.providerHealthy === false) return `${market.provider} (unhealthy)`
  if (market.providerFallback) return `${market.provider} (fallback)`
  return market.provider
}

export default memo(ExecutiveBriefing)
