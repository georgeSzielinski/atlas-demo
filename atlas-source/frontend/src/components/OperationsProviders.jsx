function formatProviderHealth(providerHealth) {
  if (!providerHealth) {
    return []
  }

  if (Array.isArray(providerHealth.providers)) {
    return providerHealth.providers
  }

  if (providerHealth.summary) {
    return Object.entries(providerHealth.summary).map(([name, value]) => ({
      name,
      healthy: value,
    }))
  }

  return Object.entries(providerHealth).map(([name, value]) => ({
    name,
    healthy: typeof value === 'object' ? value.healthy : value,
  }))
}

function OperationsProviders({ providerHealth }) {
  const rows = formatProviderHealth(providerHealth).slice(0, 8)

  return (
    <section className="operations-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Providers</p>
          <h2>Provider Health</h2>
        </div>
      </div>
      {rows.length === 0 ? (
        <p className="muted-copy">Provider health is unavailable.</p>
      ) : (
        <div className="operations-provider-list">
          {rows.map((provider) => {
            const name = provider.name ?? provider.provider_name ?? provider.active_provider ?? 'Provider'
            const healthy = provider.healthy !== false

            return (
              <article className="operations-provider-row" key={name}>
                <strong>{name}</strong>
                <span className={healthy ? 'operations-status operations-status--ok' : 'operations-status operations-status--warn'}>
                  {healthy ? 'Healthy' : 'Unhealthy'}
                </span>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}

export default OperationsProviders
