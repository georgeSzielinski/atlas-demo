function Header({ title = 'Dashboard' }) {
  return (
    <header className="header">
      <div>
        <p className="eyebrow">Atlas Research Platform</p>
        <h1>{title}</h1>
      </div>
      <div className="header__status">
        <span className="status-dot" aria-hidden="true" />
        Live API dashboard
      </div>
    </header>
  )
}

export default Header
