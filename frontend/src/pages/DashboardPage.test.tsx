import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Dashboard, Incident } from "../api/client";
import { DashboardPage } from "../pages/DashboardPage";

const INCIDENTS: Incident[] = [
  {
    id: "INC-001",
    title: "Не работает почта",
    description: "",
    category: "Mail",
    priority: "High",
    status: "In Progress",
    assignee_id: 1,
    assignee: { id: 1, name: "Иван Петров" },
    resolution: null,
    created_at: "2026-11-16T09:15:00Z",
    updated_at: "2026-11-16T09:15:00Z",
  },
  {
    id: "INC-002",
    title: "Проблемы с VPN",
    description: "",
    category: "Network",
    priority: "Critical",
    status: "New",
    assignee_id: null,
    assignee: null,
    resolution: null,
    created_at: "2026-11-15T08:00:00Z",
    updated_at: "2026-11-15T08:00:00Z",
  },
];

const DASHBOARD: Dashboard = {
  counts: { open: 2, new: 1, in_progress: 1, critical: 1, resolved_today: 3 },
  by_priority: { Critical: 1, High: 1, Medium: 4, Low: 2 },
  recent_activity: [
    {
      id: 10,
      incident_id: "INC-001",
      incident: { id: "INC-001", title: "Не работает почта" },
      actor: { id: 1, name: "Иван Петров" },
      type: "status_changed",
      payload: { status: { from: "New", to: "In Progress" } },
      created_at: "2026-11-16T09:20:00Z",
    },
  ],
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockApi(overrides: { dashboard?: () => Response; incidents?: () => Response } = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.startsWith("/api/dashboard")) {
        return Promise.resolve(overrides.dashboard?.() ?? jsonResponse(DASHBOARD));
      }
      if (url.startsWith("/api/incidents")) {
        return Promise.resolve(overrides.incidents?.() ?? jsonResponse(INCIDENTS));
      }
      return Promise.resolve(jsonResponse({ detail: "Не найдено" }, 404));
    }),
  );
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <DashboardPage />
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("DashboardPage", () => {
  it("рисует KPI, разрез по приоритетам и ленту активности", async () => {
    mockApi();
    renderPage();

    const openKpi = await waitFor(() => {
      const element = screen.getByText("Всего открытых").closest(".kpi");
      expect(element).not.toBeNull();
      return element as HTMLElement;
    });
    expect(openKpi).toHaveTextContent("2");

    const resolvedKpi = screen.getByText("Решено сегодня").closest(".kpi") as HTMLElement;
    expect(resolvedKpi).toHaveTextContent("3");

    // Легенда диаграммы показывает все приоритеты по-русски, включая нулевые.
    const chart = screen.getByTestId("priority-chart");
    expect(chart).toHaveTextContent("Критический");
    expect(chart).toHaveTextContent("Высокий");
    expect(chart).toHaveTextContent("Средний");
    expect(chart).toHaveTextContent("Низкий");
    expect(chart).toHaveTextContent("8"); // всего инцидентов в by_priority

    expect(screen.getByText("Недавняя активность")).toBeInTheDocument();
    expect(screen.getByText("Иван Петров · Смена статуса", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Статус: Новый → В работе")).toBeInTheDocument();
  });

  it("показывает ошибку дашборда понятным текстом и не рисует ложные нули", async () => {
    mockApi({ dashboard: () => jsonResponse({ detail: "Сервис недоступен" }, 503) });
    renderPage();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Сервис недоступен");
    expect(screen.getByRole("button", { name: "Повторить" })).toBeInTheDocument();
  });

  it("сообщает о пустой активности", async () => {
    mockApi({ dashboard: () => jsonResponse({ ...DASHBOARD, recent_activity: [] }) });
    renderPage();

    expect(await screen.findByText("Активности пока нет")).toBeInTheDocument();
  });
});
