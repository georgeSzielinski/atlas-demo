function PaperLearningCard({ learning }) {
  const learningActive = learning?.learning_active === true
  const latestReplay = learning?.latest_replay_result
  const replaySummary = latestReplay
    ? `${latestReplay.replay_id ?? 'replay'} · ${latestReplay.rows_used_count ?? 0} price rows · ${latestReplay.trades_generated ?? 0} trades`
    : 'No price-backed replay yet.'

  return (
    <section className="paper-panel paper-learning-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">ATLAS LEARNING</p>
          <h2>Learning From Replays</h2>
        </div>
        <span className="paper-policy-pill">
          {learningActive ? 'LEARNING ACTIVE' : 'NOT LEARNING YET'}
        </span>
      </div>
      <p className={learningActive ? 'paper-learning-message' : 'muted-copy'}>
        {learning?.message ?? 'Atlas has not started learning from paper trading yet.'}
      </p>
      <div className="paper-learning-grid">
        <article>
          <span>Latest replay result</span>
          <strong>{replaySummary}</strong>
        </article>
        <article>
          <span>Latest lesson</span>
          <strong>{learning?.latest_lesson ?? 'No lesson recorded yet.'}</strong>
        </article>
        <article>
          <span>Analytics updated</span>
          <strong>{learning?.analytics_updated ? 'Yes' : 'No'}</strong>
        </article>
        <article>
          <span>Active research experiments</span>
          <strong>{learning?.active_experiments ?? 0}</strong>
        </article>
      </div>
    </section>
  )
}

export default PaperLearningCard
