import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { Sidebar } from "../components/Sidebar";

describe("Sidebar", () => {
  it("показывает разделы MVP и подсвечивает активный", () => {
    render(
      <MemoryRouter initialEntries={["/incidents"]}>
        <Sidebar />
      </MemoryRouter>,
    );

    const incidents = screen.getByRole("link", { name: "Инциденты" });
    expect(screen.getByRole("link", { name: "Дашборд" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Пользователи" })).toBeInTheDocument();
    expect(incidents).toHaveClass("sidebar__link--active");
  });
});
