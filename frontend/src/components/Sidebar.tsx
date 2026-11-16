import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Дашборд", end: true },
  { to: "/incidents", label: "Инциденты", end: false },
  { to: "/users", label: "Пользователи", end: false },
] as const;

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__logo" aria-hidden="true">
          !
        </span>
        <span className="sidebar__brand-text">
          <strong>IT Incident</strong>
          <span>Tracker</span>
        </span>
      </div>

      <nav className="sidebar__nav" aria-label="Основная навигация">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <p className="sidebar__footer">MVP · FastAPI + React</p>
    </aside>
  );
}
