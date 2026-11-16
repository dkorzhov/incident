import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiError, api } from "../api/client";
import { setCurrentUserId } from "../api/currentUser";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockFetch(response: Response | (() => Response) = () => jsonResponse([])) {
  const spy = vi.fn(() => Promise.resolve(typeof response === "function" ? response() : response));
  vi.stubGlobal("fetch", spy);
  return spy;
}

function lastCall(spy: ReturnType<typeof vi.fn>): { url: string; init: RequestInit } {
  const call = spy.mock.calls.at(-1) as unknown as [string, RequestInit];
  return { url: call[0], init: call[1] };
}

beforeEach(() => {
  setCurrentUserId(null);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client — реестр", () => {
  it("собирает query-строку только из непустых фильтров", async () => {
    const spy = mockFetch();

    await api.incidents.list({ q: "  почта  ", status: "New" });
    expect(lastCall(spy).url).toBe("/api/incidents?q=%D0%BF%D0%BE%D1%87%D1%82%D0%B0&status=New");

    await api.incidents.list({ q: "   ", status: undefined, priority: "Critical" });
    expect(lastCall(spy).url).toBe("/api/incidents?priority=Critical");

    await api.incidents.list();
    expect(lastCall(spy).url).toBe("/api/incidents");
  });

  it("кодирует id инцидента в пути", async () => {
    const spy = mockFetch(jsonResponse({ detail: "Инцидент INC-001 не найден" }, 404));

    await api.incidents.get("INC 001").catch(() => undefined);
    expect(lastCall(spy).url).toBe("/api/incidents/INC%20001");
  });
});

describe("api client — X-User-Id", () => {
  it("отправляет заголовок в mutating-запросах, когда пользователь выбран", async () => {
    setCurrentUserId(3);
    const spy = mockFetch(jsonResponse({ id: "INC-001" }, 201));

    await api.incidents.create({ title: "Не работает почта", category: "Mail", priority: "High" });

    const { init } = lastCall(spy);
    expect(new Headers(init.headers).get("X-User-Id")).toBe("3");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(
      JSON.stringify({ title: "Не работает почта", category: "Mail", priority: "High" }),
    );
  });

  it("передаёт заголовок при смене статуса, PATCH и комментарии", async () => {
    setCurrentUserId(2);
    const spy = mockFetch(() => jsonResponse({}));

    await api.incidents.changeStatus("INC-001", { status: "In Progress" });
    expect(lastCall(spy).url).toBe("/api/incidents/INC-001/status");
    expect(lastCall(spy).init.method).toBe("PATCH");
    expect(new Headers(lastCall(spy).init.headers).get("X-User-Id")).toBe("2");

    await api.incidents.update("INC-001", { assignee_id: 1 });
    expect(lastCall(spy).init.method).toBe("PATCH");
    expect(new Headers(lastCall(spy).init.headers).get("X-User-Id")).toBe("2");

    await api.incidents.addComment("INC-001", { text: "Проверяю" });
    expect(lastCall(spy).url).toBe("/api/incidents/INC-001/comments");
    expect(new Headers(lastCall(spy).init.headers).get("X-User-Id")).toBe("2");
  });

  it("не отправляет заголовок, пока пользователь не выбран, и не мешает чтению", async () => {
    const spy = mockFetch();
    await api.incidents.list();
    expect(new Headers(lastCall(spy).init.headers).get("X-User-Id")).toBeNull();
  });

  it("сохраняет выбранного пользователя в localStorage", async () => {
    setCurrentUserId(5);
    expect(window.localStorage.getItem("it-incident-tracker.current-user-id")).toBe("5");

    setCurrentUserId(null);
    expect(window.localStorage.getItem("it-incident-tracker.current-user-id")).toBeNull();
  });
});

describe("api client — ошибки", () => {
  it("кладёт detail и errors 400 в ApiError", async () => {
    mockFetch(
      jsonResponse(
        {
          detail: "Некорректные данные",
          errors: [{ field: "title", reason: "минимум 5 символов" }],
        },
        400,
      ),
    );

    const error = (await api.incidents
      .create({ title: "abc", category: "Other", priority: "Low" })
      .catch((cause: unknown) => cause)) as ApiError;

    expect(error.status).toBe(400);
    expect(error.message).toBe("Некорректные данные");
    expect(error.errors).toEqual([{ field: "title", reason: "минимум 5 символов" }]);
  });

  it("даёт понятный текст для 409 без detail", async () => {
    mockFetch(new Response("", { status: 409 }));

    const error = (await api.incidents
      .changeStatus("INC-001", { status: "Closed" })
      .catch((cause: unknown) => cause)) as ApiError;

    expect(error.status).toBe(409);
    expect(error.message).toContain("409");
  });
});
