import { LoadingState, ErrorState } from '../components/ui/States'
import StatusPill from '../components/ui/StatusPill'
import StrategyCard from '../components/strategylab/StrategyCard'
import CommitteePanel from '../components/strategylab/CommitteePanel'
import ComparisonCard from '../components/strategylab/ComparisonCard'
import DivergencePanel from '../components/strategylab/DivergencePanel'
import { getStrategies, getStrategyComparison } from '../services/api'
import { useAsyncResource } from '../services/useAsyncResource'
import { formatClock } from '../services/paperFundOps'

// Strategy Lab: read-only view of the research-only strategy registry
// (GET /strategies) and the on-demand comparison (GET /strategies/compare).
// There are deliberately NO activation controls — strategies cannot be armed,
// executed, or connected to the live paper fund from this page.
function StrategyLab() {
  const registry = useAsyncResource('strategies', getStrategies)
  const comparison = useAsyncResource('strategies/compare', getStrategyComparison)

  if (registry.isLoading && !registry.data) {
    return <LoadingState label="Loading Strategy Lab…" />
  }
  if (registry.error && !registry.data) {
    return <ErrorState message={registry.error.message} />
  }

  const strategies = registry.data?.strategies ?? []
  const report = comparison.data
  const inputs = report?.inputs ?? {}

  return (
    <div className="dv2-page">
      <div className="dv2-lab__header">
        <div>
          <h1 className="dv2-lab__title">Strategy Lab</h1>
          <p className="dv2-lab__subtitle">
            Deterministic, research-only strategy specs compared against the
            same stored inputs. No activation, no broker, no real money.
          </p>
        </div>
        <div className="dv2-lab__policy">
          <StatusPill status="NOT_EVALUATED" label="RESEARCH ONLY" />
          <StatusPill status="EVALUATED" label="READ-ONLY" />
          <StatusPill status="EVALUATED" label="PAPER ONLY" />
        </div>
      </div>

      <div className="dv2-row dv2-row--2">
        {strategies.map((strategy) => (
          <StrategyCard strategy={strategy} key={strategy.strategy_id} />
        ))}
      </div>

      <CommitteePanel />

      <div className="dv2-lab__header dv2-lab__header--section">
        <div>
          <h2 className="dv2-lab__section-title">On-Demand Comparison</h2>
          <p className="dv2-lab__subtitle">
            {report
              ? `Generated ${formatClock(report.generated_at)} · run ${inputs.recommendation_run_id ?? '—'} · ` +
                `${inputs.recommendation_count ?? 0} recommendation records · ` +
                `fund ${inputs.paper_fund_status ?? 'OFF'} · nothing persisted`
              : 'Comparison runs on demand against stored recommendations and the paper-fund watchlist.'}
          </p>
        </div>
        <button
          type="button"
          className="dv2-chip"
          onClick={() => comparison.refetch()}
          disabled={comparison.isLoading}
        >
          {comparison.isLoading ? 'Comparing…' : 'Re-run comparison'}
        </button>
      </div>

      {comparison.error && !report ? (
        <ErrorState message={comparison.error.message} />
      ) : comparison.isLoading && !report ? (
        <LoadingState label="Running on-demand comparison…" />
      ) : report ? (
        <>
          <div className="dv2-row dv2-row--2">
            {(report.strategies ?? []).map((result) => (
              <ComparisonCard result={result} key={result.strategy_id} />
            ))}
          </div>
          <DivergencePanel divergence={report.baseline_divergence} />
        </>
      ) : null}
    </div>
  )
}

export default StrategyLab
