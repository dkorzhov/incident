import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UsersPage } from "./UsersPage";

const USERS = [
  { id: 1, name: "Иван Петров", role: "engineer" },
  { id: 3, name: "Сидорова Анна", role: "manager" },
];

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockUsers(response: () => Response) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(response())),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("UsersPage", () => {
  it("показывает таблицу пользователей с ролями на русском", async () => {
    mockUsers(() => jsonResponse(USERS));
    render(<UsersPage />);
    expect(await screen.findByText("Иван Петров")).toBeTruthy();
    expect(screen.getByText("Сидорова Анна")).toBeTruthy();
    expect(screen.getByText("Инженер")).toBeTruthy();
    expect(screen.getByText("Менеджер")).toBeTruthy();
    expect(screen.getByText("Всего пользователей: 2")).toBeTruthy();
  });

  it("ошибка загрузки показывает alert и кнопку повтора, повтор восстанавливает данные", async () => {
    let fail = true;
    mockUsers(() =>
      fail ? jsonResponse({ detail: "Сеть недоступна" }, 500) : jsonResponse(USERS),
    );
    render(<UsersPage />);
    const retry = await screen.findByRole("button", { name: "Повторить" });
    fail = false;
    fireEvent.click(retry);
    expect(await screen.findByText("Иван Петров")).toBeTruthy();
  });

  it("пустой список показывает понятное пустое состояние", async () => {
    mockUsers(() => jsonResponse([]));
    render(<UsersPage />);
    expect(await screen.findByText("Пользователей нет")).toBeTruthy();
  });
});
