function DashboardCard({ title, value, detail, tone = 'neutral' }) {
  return (
    <article className={`dashboard-card dashboard-card--${tone}`}>
      <p className="dashboard-card__title">{title}</p>
      <strong className="dashboard-card__value">{value}</strong>
      <span className="dashboard-card__detail">{detail}</span>
    </article>
  )
}

export default DashboardCard
