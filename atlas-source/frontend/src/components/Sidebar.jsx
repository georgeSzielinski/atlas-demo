import { primaryNav, secondaryNav } from '../navigation'

function NavButton({ item, activePage, onNavigate }) {
  return (
    <button
      className={item.key === activePage ? 'sidebar__link is-active' : 'sidebar__link'}
      key={item.key}
      onClick={() => onNavigate(item.key)}
      type="button"
    >
      {item.label}
    </button>
  )
}

function Sidebar({ activePage, onNavigate }) {
  return (
    <aside className="sidebar" aria-label="Primary navigation">
      <div className="sidebar__brand">
        <span className="sidebar__mark">A</span>
        <span>Atlas</span>
      </div>
      <nav className="sidebar__nav">
        {primaryNav.map((item) => (
          <NavButton key={item.key} item={item} activePage={activePage} onNavigate={onNavigate} />
        ))}
        <p className="sidebar__group-label">More</p>
        {secondaryNav.map((item) => (
          <NavButton key={item.key} item={item} activePage={activePage} onNavigate={onNavigate} />
        ))}
      </nav>
    </aside>
  )
}

export default Sidebar
