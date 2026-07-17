function PortfolioCard({ title, value, detail, tone = 'neutral' }) {
  return (
    <article className={`portfolio-card portfolio-card--${tone}`}>
      <p className="portfolio-card__title">{title}</p>
      <strong className="portfolio-card__value">{value}</strong>
      <span className="portfolio-card__detail">{detail}</span>
    </article>
  )
}

export default PortfolioCard
