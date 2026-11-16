import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AssigneeText, PriorityBadge, StatusBadge } from "../components/Badges";

describe("Badges", () => {
  it.each([
    ["Critical", "badge--priority-critical"],
    ["High", "badge--priority-high"],
    ["Medium", "badge--priority-medium"],
    ["Low", "badge--priority-low"],
  ] as const)("бейдж приоритета %s имеет свой цветовой класс", (priority, modifier) => {
    render(<PriorityBadge priority={priority} />);

    const badge = screen.getByText(priority);
    expect(badge).toHaveClass("badge", "badge--priority", modifier);
    expect(badge).toHaveAttribute("data-priority", priority);
  });

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
