import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useParams } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Dashboard, Incident } from "../api/client";
import { setCurrentUserId } from "../api/currentUser";
import { IncidentsPage } from "../pages/IncidentsPage";

const DASHBOARD: Dashboard = {
  counts: { open: 3, new: 1, in_progress: 2, critical: 1, resolved_today: 4 },
  by_priority: { Critical: 1, High: 2, Medium: 1, Low: 1 },
  recent_activity: [],
};

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
    created_at: "2026-11-16T08:00:00Z",
    updated_at: "2026-11-16T08:00:00Z",
  },
];

interface FetchCall {
  url: string;
  init: RequestInit | undefined;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Мок fetch: реестр отвечает `incidents`, дашборд — фиксированными KPI. */
function mockApi(incidents: Incident[] | (() => Response)): FetchCall[] {
  const calls: FetchCall[] = [];
  const spy = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push({ url, init });
    if (url.startsWith("/api/dashboard")) {
      return Promise.resolve(jsonResponse(DASHBOARD));
    }
    if (url.startsWith("/api/incidents")) {
      return Promise.resolve(
        typeof incidents === "function" ? incidents() : jsonResponse(incidents),
      );
    }
    return Promise.resolve(jsonResponse({ detail: "Не найдено" }, 404));
  });
  vi.stubGlobal("fetch", spy);
  return calls;
}

function incidentsCalls(calls: FetchCall[]): string[] {
  return calls.map((call) => call.url).filter((url) => url.startsWith("/api/incidents"));
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/incidents"]}>
      <IncidentsPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  setCurrentUserId(1);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("IncidentsPage — реестр", () => {
  it("рисует KPI из дашборда и таблицу с бейджами и ответственным", async () => {
    mockApi(INCIDENTS);
    renderPage();

    expect(await screen.findByText("Не работает почта")).toBeInTheDocument();
    expect(screen.getByText("Проблемы с VPN")).toBeInTheDocument();

    // KPI приходят из /api/dashboard, а не считаются по выборке.
    const openKpi = screen.getByText("Всего открытых").closest(".kpi");
    expect(openKpi).not.toBeNull();
    expect(within(openKpi as HTMLElement).getByText("3")).toBeInTheDocument();

    const resolvedKpi = screen.getByText("Решено сегодня").closest(".kpi");
    expect(within(resolvedKpi as HTMLElement).getByText("4")).toBeInTheDocument();

    const table = within(screen.getByRole("table"));
    // Подписи приоритетов русские, значения enum — в data-priority.
    expect(table.getByText("Высокий")).toHaveClass("badge--priority-high");
    expect(table.getByText("Высокий")).toHaveAttribute("data-priority", "High");
    expect(table.getByText("Критический")).toHaveClass("badge--priority-critical");
    expect(table.getByText("Критический")).toHaveAttribute("data-priority", "Critical");
    expect(table.getByText("Новый")).toHaveClass("badge--status-new");
    expect(table.getByText("В работе")).toHaveClass("badge--status-in-progress");
    expect(table.getByText("Иван Петров")).toBeInTheDocument();
    expect(table.getByText("Не назначен")).toBeInTheDocument();
  });

  it("отправляет поисковый запрос параметром q после паузы ввода", async () => {
    const calls = mockApi(INCIDENTS);
    renderPage();
    await screen.findByText("Не работает почта");

    fireEvent.change(screen.getByLabelText("Поиск по ID или названию"), {
      target: { value: "INC-001" },
    });

    await waitFor(() => {
      expect(incidentsCalls(calls)).toContain("/api/incidents?q=INC-001");
    });
  });

  it("передаёт выбранный статус в запрос и сбрасывается кнопкой «Сбросить»", async () => {
    const calls = mockApi(INCIDENTS);
    renderPage();
    await screen.findByText("Не работает почта");

    fireEvent.change(screen.getByLabelText("Статус"), {
      target: { value: "In Progress" },
    });

    await waitFor(() => {
      expect(incidentsCalls(calls)).toContain("/api/incidents?status=In+Progress");
    });

    fireEvent.click(screen.getByRole("button", { name: "Сбросить" }));

    await waitFor(() => {
      expect(incidentsCalls(calls)).toContain("/api/incidents");
    });
    expect(screen.getByLabelText("Статус")).toHaveValue("");
  });

  it("передаёт приоритет в запрос вместе с поиском", async () => {
    const calls = mockApi(INCIDENTS);
    renderPage();
    await screen.findByText("Не работает почта");

    fireEvent.change(screen.getByLabelText("Поиск по ID или названию"), {
      target: { value: "почта" },
    });
    fireEvent.change(screen.getByLabelText("Приоритет"), { target: { value: "High" } });

    await waitFor(() => {
      const url = incidentsCalls(calls).at(-1);
      expect(url).toContain("q=%D0%BF%D0%BE%D1%87%D1%82%D0%B0");
      expect(url).toContain("priority=High");
    });
  });

  it("показывает пустое состояние, когда инцидентов нет", async () => {
    mockApi([]);
    renderPage();

    expect(await screen.findByText("Инцидентов пока нет")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("различает «ничего не найдено» при активных фильтрах", async () => {
    mockApi([]);
    renderPage();
    await screen.findByText("Инцидентов пока нет");

    fireEvent.change(screen.getByLabelText("Поиск по ID или названию"), {
      target: { value: "несуществующий" },
    });

    expect(await screen.findByText("Ничего не найдено")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Сбросить фильтры" })).toBeInTheDocument();
  });

  it("показывает понятный текст ошибки сервера и повторяет запрос", async () => {
    const calls = mockApi(() => jsonResponse({ detail: "Внутренняя ошибка сервера" }, 500));
    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent("Внутренняя ошибка сервера");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();

    const before = incidentsCalls(calls).length;
    fireEvent.click(screen.getByRole("button", { name: "Повторить" }));
    await waitFor(() => {
      expect(incidentsCalls(calls).length).toBeGreaterThan(before);
    });
  });

  it("не подменяет ошибку дашборда ложными нулями в KPI", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.startsWith("/api/dashboard")) {
          return Promise.resolve(jsonResponse({ detail: "Сервис недоступен" }, 503));
        }
        return Promise.resolve(jsonResponse(INCIDENTS));
      }),
    );
    renderPage();

    await screen.findByText("Не работает почта");
    const openKpi = screen.getByText("Всего открытых").closest(".kpi") as HTMLElement;
    expect(openKpi).toHaveTextContent("—");
    expect(openKpi).not.toHaveTextContent("0");
    expect(screen.getByText("Показатели недоступны: Сервис недоступен")).toBeInTheDocument();
  });
});

function IdProbe() {
  const { id } = useParams();
  return <div>opened {id}</div>;
}

it("клик по строке реестра открывает карточку инцидента", async () => {
  mockApi(INCIDENTS);
  render(
    <MemoryRouter initialEntries={["/incidents"]}>
      <Routes>
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/incidents/:id" element={<IdProbe />} />
      </Routes>
    </MemoryRouter>,
  );
  fireEvent.click(await screen.findByText("Не работает почта"));
  expect(await screen.findByText("opened INC-001")).toBeTruthy();
});
