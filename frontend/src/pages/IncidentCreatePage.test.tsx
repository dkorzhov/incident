import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Incident, User } from "../api/client";
import { setCurrentUserId } from "../api/currentUser";
import { IncidentCreatePage } from "../pages/IncidentCreatePage";

const USERS: User[] = [
  { id: 1, name: "Иван Петров", role: "engineer" },
  { id: 2, name: "Иванов Иван", role: "engineer" },
];

const CREATED: Incident = {
  id: "INC-042",
  title: "Не работает почта",
  description: "Письма не приходят с 9:00",
  category: "Mail",
  priority: "High",
  status: "New",
  assignee_id: 1,
  assignee: { id: 1, name: "Иван Петров" },
  resolution: null,
  created_at: "2026-11-16T09:15:00Z",
  updated_at: "2026-11-16T09:15:00Z",
};

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

function mockApi(createResponse: () => Response = () => jsonResponse(CREATED, 201)): FetchCall[] {
  const calls: FetchCall[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      calls.push({ url, init });
      if (url.startsWith("/api/users")) {
        return Promise.resolve(jsonResponse(USERS));
      }
      if (url === "/api/incidents" && init?.method === "POST") {
        return Promise.resolve(createResponse());
      }
      if (url.startsWith("/api/incidents/")) {
        // Карточка после успешного создания.
        return Promise.resolve(
          jsonResponse({
            ...CREATED,
            allowed_transitions: ["In Progress"],
            comments: [],
            history: [],
          }),
        );
      }
      return Promise.resolve(jsonResponse({ detail: "Не найдено" }, 404));
    }),
  );
  return calls;
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/incidents/new"]}>
      <Routes>
        <Route path="/incidents/new" element={<IncidentCreatePage />} />
        <Route path="/incidents/:id" element={<div>CARTOCHKA</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

function fillTitle(value: string) {
  fireEvent.change(screen.getByLabelText("Название"), { target: { value } });
}

beforeEach(() => {
  setCurrentUserId(1);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("IncidentCreatePage — форма создания", () => {
  it("показывает поля формы с категорией, приоритетом и ответственным из /api/users", async () => {
    mockApi();
    renderPage();

    expect(screen.getByLabelText("Название")).toBeInTheDocument();
    expect(screen.getByLabelText("Описание")).toBeInTheDocument();
    expect(screen.getByLabelText("Категория")).toBeInTheDocument();
    expect(screen.getByLabelText("Приоритет")).toBeInTheDocument();

    const assignee = screen.getByLabelText("Ответственный");
    await waitFor(() => {
      expect(within(assignee).getByText("Иванов Иван")).toBeInTheDocument();
    });
    expect(within(assignee).getByText("Не назначен")).toBeInTheDocument();
  });

  it("блокирует отправку при коротком title и показывает ошибку поля", async () => {
    const calls = mockApi();
    renderPage();

    fillTitle("abc");
    fireEvent.click(screen.getByRole("button", { name: "Создать инцидент" }));

    expect(await screen.findByText("Минимум 5 символов, сейчас 3.")).toBeInTheDocument();
    expect(screen.getByLabelText("Название")).toHaveAttribute("aria-invalid", "true");
    expect(calls.some((call) => call.init?.method === "POST")).toBe(false);
  });

  it("не отправляет пустое название", async () => {
    const calls = mockApi();
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Создать инцидент" }));

    expect(await screen.findByText("Укажите название инцидента.")).toBeInTheDocument();
    expect(calls.some((call) => call.init?.method === "POST")).toBe(false);
  });

  it("создаёт инцидент и переходит в карточку", async () => {
    const calls = mockApi();
    renderPage();
    await waitFor(() => {
      expect(
        within(screen.getByLabelText("Ответственный")).getByText("Иван Петров"),
      ).toBeInTheDocument();
    });

    fillTitle("Не работает почта");
    fireEvent.change(screen.getByLabelText("Описание"), {
      target: { value: "Письма не приходят с 9:00" },
    });
    fireEvent.change(screen.getByLabelText("Категория"), { target: { value: "Mail" } });
    fireEvent.change(screen.getByLabelText("Приоритет"), { target: { value: "High" } });
    fireEvent.change(screen.getByLabelText("Ответственный"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Создать инцидент" }));

    await waitFor(() => {
      const postCall = calls.find((call) => call.init?.method === "POST");
      expect(postCall).toBeDefined();
      expect(postCall?.url).toBe("/api/incidents");
      expect(JSON.parse(String(postCall?.init?.body))).toEqual({
        title: "Не работает почта",
        description: "Письма не приходят с 9:00",
        category: "Mail",
        priority: "High",
        assignee_id: 1,
      });
    });

    expect(await screen.findByText("CARTOCHKA")).toBeInTheDocument();
  });

  it("отправляет assignee_id: null, если ответственный не выбран", async () => {
    const calls = mockApi();
    renderPage();

    fillTitle("Не работает почта");
    fireEvent.click(screen.getByRole("button", { name: "Создать инцидент" }));

    await waitFor(() => {
      const postCall = calls.find((call) => call.init?.method === "POST");
      expect(postCall).toBeDefined();
      expect(JSON.parse(String(postCall?.init?.body))).toMatchObject({ assignee_id: null });
    });
  });

  it("показывает ошибки полей от сервера (400) понятным текстом", async () => {
    mockApi(() =>
      jsonResponse(
        {
          detail: "Некорректные данные — title: минимум 5 символов",
          errors: [{ field: "title", reason: "минимум 5 символов" }],
        },
        400,
      ),
    );
    renderPage();

    fillTitle("Почта");
    fireEvent.click(screen.getByRole("button", { name: "Создать инцидент" }));

    // Общий текст — в alert, причина поля — под полем.
    expect(await screen.findByRole("alert")).toHaveTextContent("Некорректные данные");
    expect(screen.getByText("минимум 5 символов")).toBeInTheDocument();
    expect(screen.getByLabelText("Название")).toHaveAttribute("aria-invalid", "true");
    expect(screen.queryByText("CARTOCHKA")).not.toBeInTheDocument();
  });

  it("показывает сетевую ошибку и не теряет введённые данные", async () => {
    mockApi(() => jsonResponse({ detail: "Сервис недоступен" }, 503));
    renderPage();

    fillTitle("Не работает почта");
    fireEvent.click(screen.getByRole("button", { name: "Создать инцидент" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Сервис недоступен");
    expect(screen.getByLabelText("Название")).toHaveValue("Не работает почта");
  });

  it("предупреждает и блокирует создание, когда текущий пользователь не выбран", async () => {
    setCurrentUserId(null);
    mockApi();
    renderPage();

    expect(
      await screen.findByText(/Текущий пользователь не выбран/, undefined, { timeout: 2000 }),
    ).toBeInTheDocument();
    // Без X-User-Id сервер вернёт 400 — кнопка недоступна.
    expect(screen.getByRole("button", { name: "Создать инцидент" })).toBeDisabled();
  });
});
