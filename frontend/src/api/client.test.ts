import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "../api/client";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockFetch(): ReturnType<typeof vi.fn> {
  const spy = vi.fn();
  vi.stubGlobal("fetch", spy);
  return spy;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client", () => {
  it("ходит в /api и ставит Accept по умолчанию", async () => {
    const fetchSpy = mockFetch().mockResolvedValue(
      jsonResponse([{ id: 1, name: "Анна", role: "engineer" }]),
    );

    await api.users();

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/users");
    expect(new Headers(init.headers).get("Accept")).toBe("application/json");
  });

  it("сохраняет кастомные заголовки вызывающей стороны", async () => {
    const fetchSpy = mockFetch().mockResolvedValue(
      jsonResponse({ status: "ok", service: "api", version: "1" }),
    );

    await api.health({ headers: { "X-User-Id": "2", Accept: "application/vnd.api+json" } });

    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("X-User-Id")).toBe("2");
    expect(headers.get("Accept")).toBe("application/vnd.api+json");
  });

  it("пробрасывает detail из 4xx как сообщение ApiError", async () => {
    mockFetch().mockResolvedValue(jsonResponse({ detail: "Инцидент не найден" }, 404));

    const error = await api.users().catch((cause: unknown) => cause);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(404);
    expect((error as ApiError).message).toBe("Инцидент не найден");
  });

  it("склеивает detail-массив ошибок валидации FastAPI", async () => {
    mockFetch().mockResolvedValue(
      jsonResponse(
        { detail: [{ msg: "title слишком короткий" }, { msg: "priority неизвестен" }] },
        422,
      ),
    );

    const error = (await api.users().catch((cause: unknown) => cause)) as ApiError;

    expect(error.status).toBe(422);
    expect(error.message).toBe("title слишком короткий; priority неизвестен");
  });

  it("даёт понятный текст, когда сервер вернул пустой body ошибки", async () => {
    mockFetch().mockResolvedValue(new Response("", { status: 404 }));

    const error = (await api.users().catch((cause: unknown) => cause)) as ApiError;

    expect(error.message).toBe("Запрошенные данные не найдены.");
  });

  it("превращает сетевой сбой в ApiError со статусом 0", async () => {
    mockFetch().mockRejectedValue(new TypeError("Failed to fetch"));

    const error = (await api.users().catch((cause: unknown) => cause)) as ApiError;

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(0);
    expect(error.message).toContain("backend запущен");
  });
});
