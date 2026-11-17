import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { NotFoundPage } from "../pages/NotFoundPage";

describe("NotFoundPage", () => {
  it("показывает заглушку 404 и ссылку на дашборд", () => {
    render(
      <MemoryRouter initialEntries={["/nope"]}>
        <NotFoundPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Страница не найдена" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Вернуться на дашборд" })).toHaveAttribute("href", "/");
  });
});
