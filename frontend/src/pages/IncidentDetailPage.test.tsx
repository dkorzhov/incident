import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { HistoryEvent, IncidentDetail, User } from "../api/client";
import { setCurrentUserId } from "../api/currentUser";
import { IncidentDetailPage } from "../pages/IncidentDetailPage";

const USERS: User[] = [
  { id: 1, name: "Иван Петров", role: "engineer" },
  { id: 2, name: "Иванов Иван", role: "engineer" },
];

function makeIncident(overrides: Partial<IncidentDetail> = {}): IncidentDetail {
  return {
    id: "INC-001",
    title: "Не работает почта",
    description: "Письма не приходят с 9:00",
    category: "Mail",
    priority: "High",
    status: "In Progress",
    assignee_id: 1,
    assignee: { id: 1, name: "Иван Петров" },
    resolution: null,
    created_at: "2026-11-16T09:15:00Z",
    updated_at: "2026-11-16T09:20:00Z",
    allowed_transitions: ["Resolved"],
    comments: [],
    history: [],
    ...overrides,
  };
}

const COMMENT = {
  id: 7,
  incident_id: "INC-001",
  author_id: 2,
  author: { id: 2, name: "Иванов Иван" },
  text: "Проверяю журнал почтового шлюза",
  created_at: "2026-11-16T10:05:00Z",
};

const HISTORY: HistoryEvent[] = [
  {
    id: 1,
    incident_id: "INC-001",
    actor_id: 1,
    actor: { id: 1, name: "Иван Петров" },
    type: "created",
    payload: { title: { from: null, to: "Не работает почта" } },
    created_at: "2026-11-16T09:15:00Z",
  },
  {
    id: 2,
    incident_id: "INC-001",
    actor_id: 2,
    actor: { id: 2, name: "Иванов Иван" },
    type: "status_changed",
    payload: { status: { from: "New", to: "In Progress" } },
    created_at: "2026-11-16T09:20:00Z",
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

interface MockOptions {
  incident: IncidentDetail | (() => Response);
  /** Ответ на PATCH/POST — по умолчанию успешный инцидент. */
  mutate?: () => Response;
  users?: () => Response;
}

/**
 * Мок fetch для карточки: `/api/incidents/{id}` отдаёт инцидент, изменения —
 * `mutate`, `/api/users` — справочник.
 */
function mockApi(options: MockOptions): FetchCall[] {
  const calls: FetchCall[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      calls.push({ url, init });
      if (url.startsWith("/api/users")) {
        return Promise.resolve(options.users?.() ?? jsonResponse(USERS));
      }
      if (url === "/api/incidents/INC-001") {
        if (init?.method === "GET" || init?.method === undefined) {
          return Promise.resolve(
            typeof options.incident === "function"
              ? options.incident()
              : jsonResponse(options.incident),
          );
        }
        // PATCH /api/incidents/INC-001 (смена assignee).
        return Promise.resolve(options.mutate?.() ?? jsonResponse(makeIncident()));
      }
      if (url.startsWith("/api/incidents/INC-001/")) {
        return Promise.resolve(options.mutate?.() ?? jsonResponse(COMMENT, 201));
      }
      return Promise.resolve(jsonResponse({ detail: "Не найдено" }, 404));
    }),
  );
  return calls;
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/incidents/INC-001"]}>
      <Routes>
        <Route path="/incidents/:id" element={<IncidentDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  setCurrentUserId(1);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("IncidentDetailPage — карточка", () => {
  it("показывает номер, название, бейджи и ответственного", async () => {
    mockApi({ incident: makeIncident() });
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "INC-001 · Не работает почта" }),
    ).toBeInTheDocument();

    expect(screen.getByText("В работе")).toHaveClass("badge--status-in-progress");
    // Подпись приоритета русская (DMI-8), значение enum осталось в data-priority.
    expect(screen.getByText("Высокий")).toHaveClass("badge--priority-high");
    expect(screen.getByText("Высокий")).toHaveAttribute("data-priority", "High");
    expect(screen.getAllByText("Почта")[0]).toHaveClass("badge--category");
    expect(screen.getAllByText("Почта")[0]).toHaveAttribute("data-category", "Mail");
    expect(screen.getByText(/Ответственный:/)).toHaveTextContent("Иван Петров");
  });

  it("для New рисует только «Взять в работу»", async () => {
    mockApi({
      incident: makeIncident({ status: "New", allowed_transitions: ["In Progress"] }),
    });
    renderPage();

    expect(await screen.findByRole("button", { name: "Взять в работу" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Решить" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Закрыть" })).not.toBeInTheDocument();
  });

  it("для Resolved рисует «Закрыть», а для Closed — ни одного действия", async () => {
    mockApi({
      incident: makeIncident({ status: "Resolved", allowed_transitions: ["Closed"] }),
    });
    const { unmount } = renderPage();

    expect(await screen.findByRole("button", { name: "Закрыть" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Решить" })).not.toBeInTheDocument();
    unmount();

    mockApi({ incident: makeIncident({ status: "Closed", allowed_transitions: [] }) });
    renderPage();

    await screen.findByRole("heading", { name: "INC-001 · Не работает почта" });
    for (const label of ["Взять в работу", "Решить", "Закрыть", "Подтвердить решение"]) {
      expect(screen.queryByRole("button", { name: label })).not.toBeInTheDocument();
    }
    expect(screen.getByText(/Инцидент закрыт: действий по статусу нет/)).toBeInTheDocument();
  });

  it("требует resolution в форме решения и отправляет его на сервер", async () => {
    const calls = mockApi({ incident: makeIncident() });
    renderPage();
    await screen.findByRole("button", { name: "Решить" });

    fireEvent.click(screen.getByRole("button", { name: "Решить" }));
    fireEvent.click(screen.getByRole("button", { name: "Подтвердить решение" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Опишите решение");
    expect(calls.some((call) => call.url.endsWith("/status"))).toBe(false);

    fireEvent.change(screen.getByLabelText("Описание решения (обязательно)"), {
      target: { value: "Перезапущен почтовый шлюз" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Подтвердить решение" }));

    await waitFor(() => {
      const statusCall = calls.find((call) => call.url.endsWith("/status"));
      expect(statusCall).toBeDefined();
      expect(statusCall?.init?.method).toBe("PATCH");
      expect(JSON.parse(String(statusCall?.init?.body))).toEqual({
        status: "Resolved",
        resolution: "Перезапущен почтовый шлюз",
      });
    });
  });

  it("не даёт закрыть инцидент напрямую из In Progress (нет кнопки)", async () => {
    mockApi({ incident: makeIncident() });
    renderPage();

    await screen.findByRole("button", { name: "Решить" });
    expect(screen.queryByRole("button", { name: "Закрыть" })).not.toBeInTheDocument();
  });

  it("рисует комментарии и историю с «было → стало»", async () => {
    mockApi({
      incident: makeIncident({ comments: [COMMENT], history: HISTORY }),
    });
    renderPage();

    fireEvent.click(await screen.findByRole("tab", { name: /Комментарии/ }));
    const comment = screen.getByText("Проверяю журнал почтового шлюза").closest(".comment");
    expect(comment).not.toBeNull();
    expect(within(comment as HTMLElement).getByText("Иванов Иван")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "История" }));
    expect(screen.getByText("Создание")).toBeInTheDocument();
    expect(screen.getByText("Смена статуса")).toBeInTheDocument();
    expect(screen.getByText("Статус: Новый → В работе")).toBeInTheDocument();
  });

  it("добавляет комментарий и перечитывает карточку", async () => {
    const calls = mockApi({ incident: makeIncident() });
    renderPage();

    fireEvent.click(await screen.findByRole("tab", { name: "Комментарии" }));
    fireEvent.change(screen.getByLabelText("Новый комментарий"), {
      target: { value: "Уточните время события" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Добавить комментарий" }));

    await waitFor(() => {
      const commentCall = calls.find((call) => call.url.endsWith("/comments"));
      expect(commentCall).toBeDefined();
      expect(JSON.parse(String(commentCall?.init?.body))).toEqual({
        text: "Уточните время события",
      });
    });

    // После успеха карточка перечитывается, чтобы список обновился.
    await waitFor(() => {
      const getCalls = calls.filter(
        (call) => call.url === "/api/incidents/INC-001" && !call.init?.method,
      );
      expect(getCalls.length).toBeGreaterThan(1);
    });
  });

  it("показывает пустые состояния комментариев и истории", async () => {
    mockApi({ incident: makeIncident() });
    renderPage();
    await screen.findByRole("button", { name: "Решить" });

    fireEvent.click(screen.getByRole("tab", { name: "Комментарии" }));
    expect(screen.getByText("Комментариев пока нет")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "История" }));
    expect(screen.getByText("История пуста")).toBeInTheDocument();
  });

  it("для Closed не показывает форму комментария", async () => {
    mockApi({
      incident: makeIncident({ status: "Closed", allowed_transitions: [], comments: [COMMENT] }),
    });
    renderPage();
    await screen.findByRole("heading", { name: "INC-001 · Не работает почта" });

    fireEvent.click(screen.getByRole("tab", { name: /Комментарии/ }));
    expect(screen.getByText("Проверяю журнал почтового шлюза")).toBeInTheDocument();
    expect(screen.queryByLabelText("Новый комментарий")).not.toBeInTheDocument();
    expect(screen.getByText(/Инцидент закрыт: новые комментарии/)).toBeInTheDocument();
  });

  it("на 409 показывает текст ошибки и перезагружает карточку", async () => {
    const calls = mockApi({
      incident: makeIncident({ status: "New", allowed_transitions: ["In Progress"] }),
      mutate: () => jsonResponse({ detail: "Недопустимый переход статуса: New → Resolved" }, 409),
    });
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "Взять в работу" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Недопустимый переход статуса");
    expect(screen.getByRole("alert")).toHaveTextContent("перезагружены");

    await waitFor(() => {
      const getCalls = calls.filter(
        (call) => call.url === "/api/incidents/INC-001" && !call.init?.method,
      );
      expect(getCalls.length).toBeGreaterThan(1);
    });
  });

  it("показывает ошибку загрузки карточки и повторяет запрос", async () => {
    let attempt = 0;
    mockApi({
      incident: () => {
        attempt += 1;
        return attempt === 1
          ? jsonResponse({ detail: "Инцидент INC-404 не найден" }, 404)
          : jsonResponse(makeIncident());
      },
    });
    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent("Инцидент INC-404 не найден");

    fireEvent.click(screen.getByRole("button", { name: "Повторить" }));
    expect(
      await screen.findByRole("heading", { name: "INC-001 · Не работает почта" }),
    ).toBeInTheDocument();
  });

  it("меняет ответственного через PATCH", async () => {
    const calls = mockApi({ incident: makeIncident() });
    renderPage();
    await screen.findByRole("heading", { name: "INC-001 · Не работает почта" });

    const select = await screen.findByLabelText("Ответственный");
    await waitFor(() => {
      expect(within(select).getByText("Иванов Иван")).toBeInTheDocument();
    });
    fireEvent.change(select, { target: { value: "2" } });

    await waitFor(() => {
      const patchCall = calls.find(
        (call) => call.url === "/api/incidents/INC-001" && call.init?.method === "PATCH",
      );
      expect(patchCall).toBeDefined();
      expect(JSON.parse(String(patchCall?.init?.body))).toEqual({ assignee_id: 2 });
    });
  });
});

describe("IncidentDetailPage — вкладки", () => {
  it("по умолчанию открыта информация, вкладки переключаются", async () => {
    mockApi({ incident: makeIncident({ history: HISTORY, comments: [COMMENT] }) });
    renderPage();

    const infoTab = await screen.findByRole("tab", { name: "Информация" });
    expect(infoTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Письма не приходят с 9:00");

    fireEvent.click(screen.getByRole("tab", { name: "История" }));
    expect(screen.getByRole("tab", { name: "История" })).toHaveAttribute("aria-selected", "true");
  });
});
