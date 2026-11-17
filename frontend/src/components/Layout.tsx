import { Outlet, useLocation } from "react-router-dom";

import { CurrentUserSelect } from "./CurrentUserSelect";
import { Sidebar } from "./Sidebar";

/** Заголовок в шапке: точные маршруты + «Инцидент INC-NNN» для карточки. */
function resolveTitle(pathname: string): string {
  if (pathname === "/") {
    return "Дашборд";
  }
  if (pathname === "/incidents") {
    return "Инциденты";
  }
  if (pathname === "/incidents/new") {
    return "Новый инцидент";
  }
  if (pathname.startsWith("/incidents/")) {
    const id = decodeURIComponent(pathname.slice("/incidents/".length));
    return id ? `Инцидент ${id}` : "Инцидент";
  }
  if (pathname === "/users") {
    return "Пользователи";
  }
  return "IT Incident Tracker";
}

export function Layout() {
  const { pathname } = useLocation();

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-main">
        <header className="topbar">
          <h1 className="topbar__title">{resolveTitle(pathname)}</h1>
          <CurrentUserSelect />
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
