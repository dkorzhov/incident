import { Outlet, useLocation } from "react-router-dom";

import { CurrentUserSelect } from "./CurrentUserSelect";
import { Sidebar } from "./Sidebar";

const PAGE_TITLES: Record<string, string> = {
  "/": "Дашборд",
  "/incidents": "Инциденты",
  "/users": "Пользователи",
};

export function Layout() {
  const { pathname } = useLocation();
  const title = PAGE_TITLES[pathname] ?? "IT Incident Tracker";

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-main">
        <header className="topbar">
          <h1 className="topbar__title">{title}</h1>
          <CurrentUserSelect />
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
