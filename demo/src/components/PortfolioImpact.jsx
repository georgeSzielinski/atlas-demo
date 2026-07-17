function PortfolioImpact({ recommendation = {}, portfolio = {} }) {
  const allocation = recommendation.suggested_allocation ?? recommendation.portfolio_weight ?? 'Research only'
  const diversification = portfolio.diversification ?? recommendation.diversification ?? 'Monitor concentration'

  return (
    <section className="workspace-panel">
      <div className="panel-heading">
        <p className="eyebrow">Portfolio</p>
        <h3>Impact</h3>
      </div>
      <dl className="portfolio-impact">
        <div>
          <dt>Current Impact</dt>
          <dd>{recommendation.portfolio_score ?? 0}</dd>
        </div>
        <div>
          <dt>Suggested Allocation</dt>
          <dd>{allocation}</dd>
        </div>
        <div>
          <dt>Diversification</dt>
          <dd>{diversification}</dd>
        </div>
      </dl>
    </section>
  )
}

export default PortfolioImpact
