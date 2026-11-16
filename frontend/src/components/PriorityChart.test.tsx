import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PriorityChart } from "../components/PriorityChart";

describe("PriorityChart", () => {
  it("рисует сегменты stroke-цветами из CSS-переменных тех же приоритетов", () => {
    const { container } = render(
      <PriorityChart byPriority={{ Critical: 2, High: 1, Medium: 1, Low: 1 }} />,
    );

    const segments = Array.from(container.querySelectorAll(".priority-chart__segment"));
    expect(segments.map((segment) => segment.getAttribute("stroke"))).toEqual([
      "var(--priority-critical)",
      "var(--priority-high)",
      "var(--priority-medium)",
      "var(--priority-low)",
    ]);
    expect(segments.map((segment) => segment.getAttribute("data-priority"))).toEqual([
      "Critical",
      "High",
      "Medium",
      "Low",
    ]);
    // Фон кольца тоже из переменной — в SVG не остаётся хардкода.
    expect(container.querySelector(".priority-chart__track")).toHaveAttribute(
      "stroke",
      "var(--priority-chart-track)",
    );

    // В компоненте не должно оставаться захардкоженных оттенков.
    expect(container.innerHTML).not.toMatch(/#[0-9a-f]{6}/i);
  });

  it("точки легенды используют те же классы приоритетов, что и бейджи", () => {
    const { container } = render(
      <PriorityChart byPriority={{ Critical: 1, High: 1, Medium: 1, Low: 1 }} />,
    );

    const dots = Array.from(container.querySelectorAll(".priority-chart__dot"));
    expect(dots).toHaveLength(4);
    expect(dots.map((dot) => dot.getAttribute("data-priority"))).toEqual([
      "Critical",
      "High",
      "Medium",
      "Low",
    ]);
    expect(dots[1]).toHaveClass("badge--priority-high");
    expect(dots[2]).toHaveClass("badge--priority-medium");
  });

  it("не рисует сегменты при нулевых значениях и показывает 0 в центре", () => {
    const { container } = render(
      <PriorityChart byPriority={{ Critical: 0, High: 0, Medium: 0, Low: 0 }} />,
    );

    expect(container.querySelectorAll(".priority-chart__segment")).toHaveLength(0);
    expect(screen.getByTestId("priority-chart")).toHaveTextContent("0");
  });
});
