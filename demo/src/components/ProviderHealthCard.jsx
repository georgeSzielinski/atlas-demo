function ProviderHealthCard({ providers = [], health = {} }) {
  const rows = Array.isArray(providers) ? providers : []
  const summary = health.summary ?? {}

  return (
    <section className="workspace-panel provider-panel">
      <div className="panel-heading">
        <p className="eyebrow">Providers</p>
        <h3>Health</h3>
      </div>
      <dl className="compact-metrics">
        <div>
          <dt>Healthy</dt>
          <dd>{summary.healthy_count ?? 0}</dd>
        </div>
        <div>
          <dt>Offline</dt>
          <dd>{summary.offline_capable_count ?? 0}</dd>
        </div>
        <div>
          <dt>Experimental</dt>
          <dd>{summary.status_counts?.Experimental ?? 0}</dd>
        </div>
      </dl>
      <div className="provider-list">
        {rows.slice(0, 8).map((provider) => (
          <div className="provider-row" key={provider.name}>
            <span>{provider.name}</span>
            <strong>{provider.health?.status ?? provider.status}</strong>
          </div>
        ))}
      </div>
    </section>
  )
}

export default ProviderHealthCard
