import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AssigneeText, PriorityBadge, StatusBadge } from "../components/Badges";

describe("Badges", () => {
  it.each([
    ["Critical", "Критический", "badge--priority-critical"],
    ["High", "Высокий", "badge--priority-high"],
    ["Medium", "Средний", "badge--priority-medium"],
    ["Low", "Низкий", "badge--priority-low"],
  ] as const)(
    "бейдж приоритета %s подписан по-русски и имеет свой цветовой класс",
    (priority, label, modifier) => {
      render(<PriorityBadge priority={priority} />);

      const badge = screen.getByText(label);
      expect(badge).toHaveClass("badge", "badge--priority", modifier);
      // Значение enum не меняется — по нему UI красит и подписывает бейдж.
      expect(badge).toHaveAttribute("data-priority", priority);
      expect(badge).toHaveAttribute("title", `Приоритет: ${label}`);
    },
  );

  it.each([
    ["New", "badge--status-new"],
    ["In Progress", "badge--status-in-progress"],
    ["Resolved", "badge--status-resolved"],
    ["Closed", "badge--status-closed"],
  ] as const)("бейдж статуса %s имеет свой цветовой класс", (status, modifier) => {
    render(<StatusBadge status={status} />);

    const badge = screen.getByTitle(`Статус: ${labelFor(status)}`);
    expect(badge).toHaveClass("badge", "badge--status", modifier);
    expect(badge).toHaveAttribute("data-status", status);
    expect(badge).toHaveTextContent(labelFor(status));
  });

  it("показывает имя ответственного или «Не назначен»", () => {
    const { rerender } = render(<AssigneeText assignee={{ id: 1, name: "Иван Петров" }} />);
    expect(screen.getByText("Иван Петров")).toBeInTheDocument();

    rerender(<AssigneeText assignee={null} />);
    expect(screen.getByText("Не назначен")).toHaveClass("table__muted");
  });
});

function labelFor(status: string): string {
  const labels: Record<string, string> = {
    New: "Новый",
    "In Progress": "В работе",
    Resolved: "Решён",
    Closed: "Закрыт",
  };
  return labels[status] ?? status;
}
