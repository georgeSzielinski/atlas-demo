import { useEffect, useMemo, useState } from 'react'
import ArenaComparison from '../components/ArenaComparison'
import ExperimentComparison from '../components/ExperimentComparison'
import ExperimentHistory from '../components/ExperimentHistory'
import ExperimentQueue from '../components/ExperimentQueue'
import ResearchRoadmap from '../components/ResearchRoadmap'
import ValidationResults from '../components/ValidationResults'
import { getResearchLab } from '../services/api'

const TIMELINE_COLUMNS = [
  ['planned', 'Planned'],
  ['active', 'Active'],
  ['completed', 'Completed'],
  ['rejected', 'Rejected'],
]

function pickInitialExperiment(experiments) {
  if (!Array.isArray(experiments) || experiments.length === 0) {
    return null
  }

  const withMetrics = experiments.find(
    (item) => item.arena_metrics && Object.keys(item.arena_metrics).length > 0,
  )

  return withMetrics ?? experiments[0]
}

function ResearchLab() {
  const [data, setData] = useState(null)
  const [selectedExperiment, setSelectedExperiment] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let isCurrent = true

    async function loadLab() {
      setIsLoading(true)
      try {
        const labData = await getResearchLab()
        if (!isCurrent) return
        setData(labData)
        setSelectedExperiment(pickInitialExperiment(labData.experiments))
        setError('')
      } catch (requestError) {
        if (!isCurrent) return
        setError(requestError.message)
        setData(null)
      } finally {
        if (isCurrent) {
          setIsLoading(false)
        }
      }
    }

    loadLab()

    return () => {
      isCurrent = false
    }
  }, [])

  const operations = data?.operations_summary ?? {}
  const progress = operations.research_progress ?? {}
  const timeline = data?.timeline ?? {}

  const summaryCards = useMemo(
    () => [
      ['Active Experiments', operations.active_experiment_count ?? 0],
      ['Total Experiments', progress.total_experiments ?? 0],
      ['Latest Decision', operations.latest_adoption_decision ?? 'Not Enough Evidence'],
      ['Completion Rate', `${progress.completion_rate ?? 0}%`],
      ['Adopted', progress.adopted ?? 0],
    ],
    [operations, progress],
  )

  if (isLoading) {
    return <section className="dashboard-state">Loading Research Laboratory...</section>
  }

  if (error && !data) {
    return (
      <section className="dashboard-state dashboard-state--error">
        {error} Start the FastAPI backend and refresh to load the Research Laboratory.
      </section>
    )
  }

  return (
    <div className="research-lab">
      <section className="lab-hero">
        <div>
          <p className="eyebrow">Research Laboratory</p>
          <h2>Every idea earns its place through evidence</h2>
          <p>
            RESEARCH ONLY. SIMULATED. NO BROKER CONNECTED. NO REAL MONEY. Nothing is adopted
            because it sounds better. Adoption always requires human approval.
          </p>
        </div>
        <div className="lab-hero__badges">
          <span>DETERMINISTIC</span>
          <span>PAPER ONLY</span>
          <span>HUMAN APPROVAL REQUIRED</span>
        </div>
      </section>

      <section className="lab-summary">
        {summaryCards.map(([label, value]) => (
          <article className="lab-summary__card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </section>

      <ExperimentQueue
        onSelect={setSelectedExperiment}
        queue={data?.queue}
        selectedId={selectedExperiment?.experiment_id}
      />

      <div className="lab-grid lab-grid--two">
        <ExperimentComparison experiment={selectedExperiment} />
        <ValidationResults validation={data?.latest_validation} />
      </div>

      <ArenaComparison arena={data?.latest_arena} />

      <section className="lab-panel">
        <div className="lab-panel__heading">
          <div>
            <p className="eyebrow">Research Timeline</p>
            <h3>Planned, Active, Completed, Rejected</h3>
          </div>
        </div>
        <div className="lab-timeline">
          {TIMELINE_COLUMNS.map(([key, label]) => {
            const items = Array.isArray(timeline[key]) ? timeline[key] : []

            return (
              <div className={`lab-timeline__column lab-timeline__column--${key}`} key={key}>
                <header>
                  <span>{label}</span>
                  <strong>{items.length}</strong>
                </header>
                {items.length === 0 ? (
                  <p className="lab-empty">None.</p>
                ) : (
                  <ul>
                    {items.map((experiment) => (
                      <li key={experiment.experiment_id}>
                        <button
                          onClick={() => setSelectedExperiment(experiment)}
                          type="button"
                        >
                          {experiment.title}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )
          })}
        </div>
      </section>

      <ResearchRoadmap roadmap={data?.roadmap} />

      <ExperimentHistory history={data?.history} onSelect={setSelectedExperiment} />
    </div>
  )
}

export default ResearchLab
