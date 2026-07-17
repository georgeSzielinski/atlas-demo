function DataProviderCard({ provider }) {
  const details = Array.isArray(provider?.provider_details) ? provider.provider_details : []
  const current = provider?.current_provider ?? 'mock'

  return (
    <section className="operations-panel data-provider-card">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Market Data</p>
          <h2>Data Provider</h2>
        </div>
        <span className="market-provider-pill">{current}</span>
      </div>

      <p className="market-note">
        Default: {provider?.default_provider ?? 'mock'} · Fallback:{' '}
        {provider?.fallback_provider ?? 'mock'}. Mock remains the deterministic default.
      </p>

      {details.length === 0 ? (
        <p className="market-note">No provider details available.</p>
      ) : (
        <table className="market-table">
          <thead>
            <tr>
              <th>Provider</th>
              <th>Available</th>
              <th>Offline</th>
              <th>API Key</th>
              <th>Current</th>
            </tr>
          </thead>
          <tbody>
            {details.map((item) => (
              <tr className={item.current ? 'is-current' : ''} key={item.name}>
                <td>{item.name}</td>
                <td>{item.available ? 'Yes' : 'No'}</td>
                <td>{item.supports_offline ? 'Yes' : 'No'}</td>
                <td>{item.requires_api_key ? 'Yes' : 'No'}</td>
                <td>{item.current ? '●' : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

export default DataProviderCard
