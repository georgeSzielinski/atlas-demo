import { memo, useEffect, useMemo, useRef } from 'react'
import { createPortal } from 'react-dom'
import StatusPill from '../ui/StatusPill'
import MeterBar from '../ui/MeterBar'
import KVList from '../ui/KVList'
import AlertList from '../ui/AlertList'
import Timeline from '../ui/Timeline'
import { LoadingState, ErrorState, EmptyState } from '../ui/States'
import ReportSection from './ReportSection'
import { HorizonEvidenceBadges } from '../outcomes/OutcomeEvidence'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { useAsyncResource } from '../../services/useAsyncResource'
import {
  getInstitutionalReport,
  getLearningCenter,
  getRecommendationOutcomes,
} from '../../services/api'
import { buildReportModel, voteTone } from '../../services/institutionalReport'
import {
  buildDrawerOutcomeModel,
  outcomeTone,
} from '../../services/recommendationOutcomes'
import {
  LEARNING_RECORD_LIMIT,
  LEARNING_RESOURCE_KEY,
  buildDrawerLearningModel,
} from '../../services/learningIntelligence'
import { actionTone } from '../../services/missionOps'
import { formatClock } from '../../services/paperFundOps'
import {
  formatConfidence,
  formatNumber,
  formatPercent,
  formatSignedPercent,
} from '../../services/formatters'

// Read-only Institutional Research Report, opened from a committee card. Fetches
// GET /institutional-report/{ticker} on open and renders only the sections the
// backend actually supports; everything else degrades to a NOT_EVALUATED state.
function InstitutionalReportDrawer({ card, onClose }) {
  const open = Boolean(card)
  const ticker = card?.ticker ?? null
  const recommendationId = card?.recommendationId ?? null
  const panelRef = useRef(null)
  const { data: dashboard } = useDashboardData()

  const { data: report, isLoading, error } = useAsyncResource(
    `institutional-report/${ticker ?? 'none'}`,
    () => getInstitutionalReport(ticker),
    { enabled: open },
  )
  const {
    data: outcomePayload,
    isLoading: outcomeLoading,
    error: outcomeError,
  } = useAsyncResource(
    `recommendation/${recommendationId ?? 'none'}/outcomes`,
    () => getRecommendationOutcomes(recommendationId),
    { enabled: open && recommendationId !== null },
  )
  const outcomeModel = useMemo(
    () => recommendationId === null
      ? null
      : buildDrawerOutcomeModel(
          Number(outcomePayload?.meta?.recommendation_id) === Number(recommendationId)
            ? outcomePayload
            : null,
          card?.outcomeEvidence,
          recommendationId,
        ),
    [card?.outcomeEvidence, outcomePayload, recommendationId],
  )
  const {
    data: learningPayload,
    isLoading: learningLoading,
    error: learningError,
  } = useAsyncResource(
    LEARNING_RESOURCE_KEY,
    () => getLearningCenter({ limit: LEARNING_RECORD_LIMIT }),
    { enabled: open && recommendationId !== null },
  )
  const learningModel = useMemo(
    () => buildDrawerLearningModel(learningPayload, recommendationId),
    [learningPayload, recommendationId],
  )

  // Escape to close + body scroll lock while the drawer is open.
  useEffect(() => {
    if (!open) return undefined
    const onKey = (event) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = previousOverflow
    }
  }, [open, onClose])

  useEffect(() => {
    if (open && panelRef.current) panelRef.current.focus()
  }, [open])

  if (!open) return null

  const model = report ? buildReportModel(report, card) : null

  // Distinguish a recommendation from an executed paper action: only a real
  // open position or a recorded simulated order counts as "executed".
  const fund = dashboard?.paper_fund ?? {}
  const position = (fund.open_positions ?? {})[ticker] ?? null
  const orders = (Array.isArray(fund.virtual_orders) ? fund.virtual_orders : []).filter(
    (order) => (order.ticker ?? order.symbol) === ticker,
  )
  const hasExecuted = Boolean(position) || orders.length > 0

  const drawer = (
    <div className="dv3-drawer" role="presentation" onClick={onClose}>
      <div
        className="dv3-drawer__panel"
        role="dialog"
        aria-modal="true"
        aria-label={`Institutional research report for ${ticker}`}
        tabIndex={-1}
        ref={panelRef}
        onClick={(event) => event.stopPropagation()}
      >
        <ReportHeader card={card} model={model} onClose={onClose} />

        <div className="dv3-drawer__body">
          {isLoading && !report ? (
            <LoadingState label={`Loading ${ticker} research report…`} />
          ) : error && !report ? (
            <ErrorState message={error.message} />
          ) : !model ? (
            <EmptyState title="No report" message="The report could not be loaded." />
          ) : (
            <ReportBody
              model={model}
              hasExecuted={hasExecuted}
              position={position}
              orders={orders}
              outcome={outcomeModel}
              outcomeLoading={outcomeLoading}
              outcomeError={outcomeError}
              learning={learningModel}
              learningLoading={learningLoading}
              learningError={learningError}
            />
          )}
        </div>
      </div>
    </div>
  )

  return createPortal(drawer, document.body)
}

function ReportHeader({ card, model, onClose }) {
  const header = model?.header ?? {}
  const action = header.action ?? card?.action ?? 'N/A'
  const tone = actionTone(action)
  return (
    <header className="dv3-drawer__head">
      <div className="dv3-drawer__title">
        <span className="dv3-drawer__ticker">{header.ticker ?? card?.ticker}</span>
        <span className={`dv3-verdict dv3-verdict--${tone}`}>{action}</span>
      </div>
      <div className="dv3-drawer__meta">
        <Meta label="Confidence" value={formatConfidence(header.confidence ?? card?.confidence, { fallback: '—' })} />
        <Meta label="Agreement" value={formatPercent(header.agreementPct ?? card?.agreementPct, { fallback: '—' })} />
        <Meta label="Strength" value={header.strength ?? card?.strength ?? '—'} />
        <Meta label="Generated" value={header.generatedAt ? formatClock(header.generatedAt) : '—'} />
      </div>
      <button type="button" className="dv3-drawer__close" onClick={onClose} aria-label="Close report">
        ✕
      </button>
    </header>
  )
}

function Meta({ label, value }) {
  return (
    <div className="dv3-drawer__meta-item">
      <span className="dv3-drawer__meta-k">{label}</span>
      <strong className="dv3-drawer__meta-v">{value}</strong>
    </div>
  )
}

function ReportBody({
  model,
  hasExecuted,
  position,
  orders,
  outcome,
  outcomeLoading,
  outcomeError,
  learning,
  learningLoading,
  learningError,
}) {
  const thesis = model.thesis
  const technical = model.technical
  const fundamental = model.fundamental
  const risks = model.risks

  return (
    <>
      {!model.hasRecommendation ? (
        <div className="dv3-report__notice" role="status">
          No stored recommendation record exists for {model.ticker} yet. This report shows
          only the baseline data sources currently available; analytic sections remain
          unevaluated until a research cycle records a recommendation.
        </div>
      ) : null}

      <ReportSection
        title="Executive Summary"
        eyebrow="Overview"
        available={Boolean(model.executiveSummary.summary)}
        emptyMessage="No executive summary has been generated for this ticker."
      >
        <p className="dv3-report__prose">{model.executiveSummary.summary}</p>
        {model.executiveSummary.secFilings ? (
          <small className="dv3-report__note">
            Backed by {model.executiveSummary.secFilings} SEC filing(s).
          </small>
        ) : null}
      </ReportSection>

      <ReportSection
        title="Investment Thesis"
        eyebrow="Reasoning"
        available={Boolean(
          thesis.rating || thesis.overallScore || thesis.signalLabel || thesis.evidence.length,
        )}
        emptyMessage="No deterministic thesis evidence is recorded for this ticker."
      >
        <KVList
          rows={[
            ['Rating', thesis.rating],
            ['Overall score', thesis.overallScore !== null ? formatNumber(thesis.overallScore) : null],
            ['Validation', thesis.validationStatus],
            ['Signal', thesis.signalLabel],
            [
              'Signal quality',
              thesis.signalQuality !== null ? formatNumber(thesis.signalQuality) : null,
            ],
          ]}
          emptyMessage="No thesis metrics available."
        />
        {thesis.evidence.length ? (
          <AlertList items={thesis.evidence} tone="neutral" emptyTitle="No evidence" max={8} />
        ) : null}
      </ReportSection>

      <div className="dv3-report__split">
        <ReportSection
          title="Bull Case"
          eyebrow="For"
          available={model.bullCase.length > 0}
          emptyMessage="No bullish arguments recorded by the committee."
        >
          <AlertList items={model.bullCase} tone="positive" max={8} />
        </ReportSection>
        <ReportSection
          title="Bear Case"
          eyebrow="Against"
          available={model.bearCase.length > 0}
          emptyMessage="No bearish arguments recorded by the committee."
        >
          <AlertList items={model.bearCase} tone="negative" max={8} />
        </ReportSection>
      </div>

      <ReportSection
        title="Catalysts"
        eyebrow="Events"
        available={model.catalysts.length > 0}
        emptyMessage="No catalyst records exist for this ticker."
      >
        <Timeline
          events={model.catalysts.map((catalyst) => ({
            title: catalyst.title ?? catalyst.name ?? catalyst.event ?? String(catalyst),
            detail: catalyst.detail ?? catalyst.description ?? null,
            at: catalyst.date ?? catalyst.at ?? null,
            tone: 'neutral',
          }))}
          emptyMessage="No catalysts."
        />
      </ReportSection>

      <ReportSection
        title="Risks"
        eyebrow="Downside"
        available={risks.items.length > 0 || risks.score !== null || risks.falsePositives.length > 0}
        emptyMessage="No risk factors are recorded for this ticker."
      >
        {risks.score !== null ? (
          <MeterBar value={risks.score} tone="warn" label={`Risk score ${formatNumber(risks.score)}`} />
        ) : null}
        {risks.items.length ? <AlertList items={risks.items} tone="warn" max={8} /> : null}
        {risks.falsePositives.length ? (
          <>
            <span className="dv3-report__subhead">False-positive warnings</span>
            <AlertList items={risks.falsePositives} tone="warn" max={6} />
          </>
        ) : null}
      </ReportSection>

      <div className="dv3-report__split">
        <ReportSection
          title="Technical Evidence"
          eyebrow="Price & forecast"
          available={Boolean(
            technical.technicalScore || technical.score || technical.forecastDirection,
          )}
          emptyMessage="No technical scores are available."
        >
          <KVList
            rows={[
              ['Technical score', technical.technicalScore !== null ? formatNumber(technical.technicalScore) : null],
              ['Composite score', technical.score !== null ? formatNumber(technical.score) : null],
              ['Forecast direction', technical.forecastDirection],
              [
                'Forecast confidence',
                technical.forecastConfidence !== null ? formatNumber(technical.forecastConfidence) : null,
              ],
              [
                'Expected change',
                technical.expectedChange !== null ? formatSignedPercent(technical.expectedChange) : null,
              ],
            ]}
            emptyMessage="No technical metrics available."
          />
        </ReportSection>

        <ReportSection
          title="Fundamental Evidence"
          eyebrow="Filings & value"
          available={Boolean(fundamental.fundamentalScore || fundamental.filingCount)}
          emptyMessage="No fundamental scores or filings are available."
        >
          <KVList
            rows={[
              ['Fundamental score', fundamental.fundamentalScore !== null ? formatNumber(fundamental.fundamentalScore) : null],
              ['SEC filings', fundamental.filingCount !== null ? formatNumber(fundamental.filingCount) : null],
              ['SEC provider', fundamental.secProvider],
              [
                'Sections covered',
                fundamental.sectionCoverage.length ? `${fundamental.sectionCoverage.length}` : null,
              ],
            ]}
            emptyMessage="No fundamental metrics available."
          />
        </ReportSection>
      </div>

      <ReportSection
        title="Committee Breakdown"
        eyebrow="Votes"
        available={model.committee.members.length > 0}
        emptyMessage="No committee member votes are recorded for this ticker."
      >
        {model.committee.agreement !== null ? (
          <MeterBar
            value={model.committee.agreement}
            tone="accent"
            label={`Committee agreement ${formatPercent(model.committee.agreement, { fallback: 'n/a' })}`}
          />
        ) : null}
        <ul className="dv3-report__members">
          {model.committee.members.map((member, index) => (
            <li className="dv3-report__member" key={`${member.name}-${index}`}>
              <span className="dv3-report__member-name">{member.name}</span>
              <StatusPill
                status={member.vote}
                tone={voteTone(member.vote)}
                label={member.vote}
              />
            </li>
          ))}
        </ul>
        <small className="dv3-report__note">
          Per-member confidence and rationale are not exposed at report granularity; the
          bull and bear cases above carry the committee's narrative.
        </small>
      </ReportSection>

      {model.recommendationId !== null ? (
        <>
          <OutcomeEvidenceSection
            outcome={outcome}
            isLoading={outcomeLoading}
            error={outcomeError}
          />
          <LearningIntelligenceSection
            learning={learning}
            outcome={outcome}
            isLoading={learningLoading}
            error={learningError}
          />
        </>
      ) : null}

      <ReportSection title="Construction & Risk Context" eyebrow="Recommendation vs. execution">
        <KVList
          rows={[
            ['Portfolio score', model.construction.portfolioScore !== null ? formatNumber(model.construction.portfolioScore) : null],
            ['Overall conviction', model.construction.overallConviction !== null ? formatNumber(model.construction.overallConviction) : null],
          ]}
          emptyMessage="No proposed construction metrics are exposed by the backend."
        />
        <div className={`dv3-report__exec dv3-report__exec--${hasExecuted ? 'live' : 'none'}`}>
          {hasExecuted ? (
            <>
              <StatusPill status="EVALUATED" label="Executed (simulated)" />
              <p>
                A simulated paper position/order exists for {model.ticker}:{' '}
                {position
                  ? `${formatNumber(position.quantity)} share(s) held`
                  : `${orders.length} recorded order(s)`}
                . This reflects an actual paper-fund action, not real money.
              </p>
            </>
          ) : (
            <>
              <StatusPill status="NOT_EVALUATED" label="Recommendation only" />
              <p>
                This is a research recommendation. No paper-fund order or position exists for{' '}
                {model.ticker}; nothing has been executed.
              </p>
            </>
          )}
        </div>
      </ReportSection>

      <AuditSection audit={model.audit} />
    </>
  )
}

function LearningIntelligenceSection({ learning, outcome, isLoading, error }) {
  const context = learning?.context
  const quality = learning?.evidenceQuality ?? {}
  return (
    <ReportSection
      title="Learning Intelligence"
      eyebrow="Historical evidence"
      available={Boolean(context) || learning?.historicalAccuracy !== null}
      emptyMessage="NOT_EVALUATED: no exact historical learning context is available for this recommendation."
    >
      {isLoading ? <small className="dv3-report__note">Loading Learning Intelligence…</small> : null}
      {error ? (
        <div className="dv3-report__notice" role="status">
          Learning Intelligence is unavailable; no historical values are inferred.
        </div>
      ) : null}
      {learning?.source?.truncated ? (
        <div className="dv3-report__notice" role="status">
          {learning.source.warning} Analyzed {learning.source.analyzedRowCount} of{' '}
          {learning.source.sourceTotalRowCount} source rows.
        </div>
      ) : null}
      <KVList
        rows={[
          ['Committee', context?.committee ?? 'NOT_EVALUATED'],
          [
            'Committee historical accuracy',
            context?.committeeHistoricalAccuracy !== null && context?.committeeHistoricalAccuracy !== undefined
              ? formatPercent(context.committeeHistoricalAccuracy, { fallback: 'Unavailable' })
              : 'NOT_EVALUATED',
          ],
          ['Primary stored engine', context?.primaryEngine ?? 'NOT_EVALUATED'],
          [
            'Primary engine historical accuracy',
            context?.engineHistoricalAccuracy !== null && context?.engineHistoricalAccuracy !== undefined
              ? formatPercent(context.engineHistoricalAccuracy, { fallback: 'Unavailable' })
              : 'NOT_EVALUATED',
          ],
          [
            'Calibration gap',
            learning?.calibrationGap !== null && learning?.calibrationGap !== undefined
              ? formatSignedPercent(learning.calibrationGap, { fallback: 'Unavailable' })
              : 'NOT_EVALUATED',
          ],
          [
            'Evaluation coverage',
            context?.evaluationCoverage !== null && context?.evaluationCoverage !== undefined
              ? formatPercent(context.evaluationCoverage, { fallback: 'Unavailable' })
              : 'NOT_EVALUATED',
          ],
          ['Recommendation maturity', context?.recommendationMaturity ?? 'NOT_EVALUATED'],
          [
            'Historical accuracy',
            learning?.historicalAccuracy !== null && learning?.historicalAccuracy !== undefined
              ? formatPercent(learning.historicalAccuracy, { fallback: 'Unavailable' })
              : 'NOT_EVALUATED',
          ],
          ['Evidence quality', quality.status ?? 'NOT_EVALUATED'],
          ['Latest outcome summary', outcome?.latestResult ?? 'Not evaluated'],
          [
            'Latest outcome horizon',
            outcome?.latestCompletedHorizon ? `${outcome.latestCompletedHorizon}d` : 'Not evaluated',
          ],
        ]}
        emptyMessage="No Learning Intelligence evidence is available."
      />
      <small className="dv3-report__note">
        Historical association is descriptive only. It does not prove causation or imply execution.
      </small>
    </ReportSection>
  )
}

function OutcomeEvidenceSection({ outcome, isLoading, error }) {
  const state = outcome ?? buildDrawerOutcomeModel(null)
  const evaluatedHorizons = state.horizonsEvaluated.length
    ? state.horizonsEvaluated.map((horizon) => `${horizon}d`).join(', ')
    : 'Not evaluated'

  return (
    <ReportSection title="Outcome Evidence" eyebrow="Read-only paper evaluation">
      {error ? (
        <div className="dv3-report__notice" role="status">
          Complete outcome evidence is unavailable. Any visible badges come from the bounded
          shared records projection and may be incomplete.
        </div>
      ) : isLoading ? (
        <small className="dv3-report__note">Loading complete outcome evidence…</small>
      ) : null}
      <KVList
        rows={[
          ['Recommendation ID', state.recommendationId ?? 'Unavailable'],
          ['Horizons evaluated', evaluatedHorizons],
          ['Completed', String(state.counts.completed)],
          ['Pending', String(state.counts.pending)],
          ['Deferred', String(state.counts.deferred)],
          ['Latest completed horizon', state.latestCompletedHorizon ? `${state.latestCompletedHorizon}d` : 'Not evaluated'],
          ['Latest completed result', state.latestCompletedResult],
          [
            'Latest raw return',
            state.latestRawReturn !== null
              ? formatSignedPercent(state.latestRawReturn, { fallback: 'Unavailable' })
              : 'Unavailable',
          ],
          ['Evaluation source', state.evaluationSource ?? 'Unavailable'],
          ['Entry timestamp', state.entryAt ? formatClock(state.entryAt) : 'Unavailable'],
          ['Latest evaluation timestamp', state.latestEvaluationAt ? formatClock(state.latestEvaluationAt) : 'Unavailable'],
        ]}
        emptyMessage="No outcome evidence is available."
      />
      <div className="dv3-report__outcome-state">
        <StatusPill
          status={state.latestResult}
          label={state.latestResult}
          tone={outcomeTone(state.latestResult)}
        />
        <span>Latest stored evidence state</span>
      </div>
      <HorizonEvidenceBadges badges={state.horizonBadges} />
      <div className="dv3-report__notices">
        <span className="dv3-report__tag">Paper-only outcome evidence</span>
        <span className="dv3-report__tag">Read-only</span>
      </div>
      <small className="dv3-report__note">
        Outcome evidence records observed results; it does not prove causation and does not show
        that this recommendation was executed. Execution requires an actual recorded paper order.
      </small>
    </ReportSection>
  )
}

function AuditSection({ audit }) {
  const policy = audit.policy ?? {}
  return (
    <ReportSection title="Audit & Provenance" eyebrow="Read-only">
      <KVList
        rows={[
          ['Report version', audit.reportVersion],
          ['Generated', audit.generatedAt ? formatClock(audit.generatedAt) : null],
          ['SEC provider', audit.secProvider],
          ['Data sources', audit.dataSources.length ? `${audit.dataSources.length} source(s)` : null],
          ['Active providers', audit.activeProviders.length ? `${audit.activeProviders.length}` : null],
        ]}
        emptyMessage="No provenance metadata available."
      />
      <div className="dv3-report__notices">
        <span className="dv3-report__tag">Paper-only · no real money</span>
        {policy.deterministic ? <span className="dv3-report__tag">Deterministic</span> : null}
        {policy.uses_llm === false ? <span className="dv3-report__tag">No LLM</span> : null}
        <span className="dv3-report__tag">Read-only · does not change recommendations</span>
      </div>
    </ReportSection>
  )
}

export default memo(InstitutionalReportDrawer)
