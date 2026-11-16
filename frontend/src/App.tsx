import { Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { DashboardPage } from "./pages/DashboardPage";
import { IncidentCreatePage } from "./pages/IncidentCreatePage";
import { IncidentDetailPage } from "./pages/IncidentDetailPage";
import { IncidentsPage } from "./pages/IncidentsPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { UsersPage } from "./pages/UsersPage";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="incidents" element={<IncidentsPage />} />
        {/* Заготовки для DMI-9: полную реализацию делает тикет карточки. */}
        <Route path="incidents/new" element={<IncidentCreatePage />} />
        <Route path="incidents/:id" element={<IncidentDetailPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
