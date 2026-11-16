import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getCurrentUserId, setCurrentUserId } from "../api/currentUser";
import { CurrentUserSelect } from "../components/CurrentUserSelect";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const USERS = [
  { id: 1, name: "Иван Петров", role: "engineer" },
  { id: 2, name: "Сидорова Анна", role: "manager" },
];

beforeEach(() => {
  setCurrentUserId(null);
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/users") {
        return Promise.resolve(jsonResponse(USERS));
      }
      return Promise.resolve(jsonResponse({ detail: "Не найдено" }, 404));
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("CurrentUserSelect", () => {
  it("выбирает первого пользователя по умолчанию и делает его текущим для API", async () => {
    render(<CurrentUserSelect />);

    const select = (await screen.findByRole("combobox", {
      name: "Текущий пользователь",
    })) as HTMLSelectElement;

    await waitFor(() => {
      expect(select.value).toBe("1");
      expect(getCurrentUserId()).toBe(1);
    });
  });

  it("передаёт выбранного пользователя в общий store", async () => {
    render(<CurrentUserSelect />);

    const select = await screen.findByRole("combobox", { name: "Текущий пользователь" });
    await waitFor(() => expect(getCurrentUserId()).toBe(1));

    fireEvent.change(select, { target: { value: "2" } });

    expect(getCurrentUserId()).toBe(2);
    expect(window.localStorage.getItem("it-incident-tracker.current-user-id")).toBe("2");
  });

  it("показывает ошибку загрузки справочника", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse({ detail: "Справочник недоступен" }, 500))),
    );

    render(<CurrentUserSelect />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Справочник недоступен");
  });
});
