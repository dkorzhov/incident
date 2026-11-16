import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

interface NavItem {
  to: string;
  label: string;
  end: boolean;
  icon: ReactNode;
}

/** Иконки разделов — простые SVG без внешних библиотек. */
function DashboardIcon() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <rect x="1.5" y="1.5" width="5" height="5" rx="1" />
      <rect x="9.5" y="1.5" width="5" height="5" rx="1" />
      <rect x="1.5" y="9.5" width="5" height="5" rx="1" />
      <rect x="9.5" y="9.5" width="5" height="5" rx="1" />
    </svg>
  );
}

function IncidentsIcon() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path d="M5 3.5h9M5 8h9M5 12.5h9" />
      <circle cx="2" cy="3.5" r="1" />
      <circle cx="2" cy="8" r="1" />
      <circle cx="2" cy="12.5" r="1" />
    </svg>
  );
}

function UsersIcon() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <circle cx="6" cy="5.5" r="2.5" />
      <path d="M1.5 14c0-2.5 2-4 4.5-4s4.5 1.5 4.5 4" />
      <path d="M10.5 3.6a2.5 2.5 0 0 1 0 4.8M12 10.4c1.6.5 2.5 1.7 2.5 3.6" />
    </svg>
  );
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Дашборд", end: true, icon: <DashboardIcon /> },
  { to: "/incidents", label: "Инциденты", end: false, icon: <IncidentsIcon /> },
  { to: "/users", label: "Пользователи", end: false, icon: <UsersIcon /> },
];

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
            <span className="sidebar__icon">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <p className="sidebar__footer">MVP · FastAPI + React</p>
    </aside>
  );
}
