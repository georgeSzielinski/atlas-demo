function statusModifier(status) {
  return String(status ?? 'unknown').toLowerCase().replace(/\s+/g, '-')
}

function MarketHealthCard({ marketHealth }) {
  const health = marketHealth?.health ?? {}
  const providers = Array.isArray(health.providers) ? health.providers : []
  const cacheStats = marketHealth?.cache_stats ?? {}

  const cards = [
    ['Active Provider', health.active_provider ?? 'mock'],
    ['Healthy', health.healthy ? 'Yes' : 'No'],
    ['Fallback Used', health.fallback_used ? 'Yes' : 'No'],
    ['Offline Capable', health.offline_capable ? 'Yes' : 'No'],
    ['Cache Entries', cacheStats.size ?? 0],
    ['Fallback Entries', cacheStats.fallback_entries ?? 0],
  ]

  return (
    <section className="operations-panel market-health-card">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Market Data</p>
          <h2>Provider Health</h2>
        </div>
        <span className="operations-policy-pill">GRACEFUL FALLBACK</span>
      </div>

      <div className="market-health-grid">
        {cards.map(([label, value]) => (
          <article className="market-health-metric" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </div>

      {providers.length === 0 ? (
        <p className="market-note">No registered market data providers.</p>
      ) : (
        <ul className="market-provider-health-list">
          {providers.map((provider) => (
            <li key={provider.name}>
              <span>{provider.name}</span>
              <span className={`market-health-badge market-health-badge--${statusModifier(provider.status)}`}>
                {provider.status}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default MarketHealthCard
