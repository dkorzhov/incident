import { describe, expect, it } from "vitest";

import type { Incident } from "../api/types";
import { buildDynamics } from "../components/DynamicsChart";

function incident(overrides: Partial<Incident>): Incident {
  return {
    id: "INC-001",
    title: "Инцидент",
    description: "",
    category: "Other",
    priority: "Low",
    status: "New",
    assignee_id: null,
    assignee: null,
    resolution: null,
    created_at: "2026-11-16T10:00:00",
    updated_at: "2026-11-16T10:00:00",
    ...overrides,
  };
}

describe("buildDynamics", () => {
  const now = new Date(2026, 10, 16, 15, 0, 0);

  it("строит ровно 7 дней и считает созданные по created_at", () => {
    const points = buildDynamics(
      [
        incident({ created_at: "2026-11-16T09:00:00" }),
        incident({ id: "INC-002", created_at: "2026-11-16T11:00:00" }),
        incident({ id: "INC-003", created_at: "2026-11-14T12:00:00" }),
      ],
      7,
      now,
    );

    expect(points).toHaveLength(7);
    const today = points.at(-1);
    expect(today?.created).toBe(2);
    expect(today?.closed).toBe(0);
    expect(points.find((point) => point.key === "2026-11-14")?.created).toBe(1);
  });

  it("считает закрытые по updated_at только для статуса Closed", () => {
    const points = buildDynamics(
      [
        incident({ status: "Closed", updated_at: "2026-11-15T16:00:00" }),
        incident({ id: "INC-002", status: "Resolved", updated_at: "2026-11-15T16:00:00" }),
      ],
      7,
      now,
    );

    const day = points.find((point) => point.key === "2026-11-15");
    expect(day?.closed).toBe(1);
    // Созданы оба сегодня (created_at по умолчанию 16.11), поэтому 15-го — ноль.
    expect(day?.created).toBe(0);
  });

  it("игнорирует инциденты за пределами окна", () => {
    const points = buildDynamics([incident({ created_at: "2026-10-01T09:00:00" })], 7, now);

    expect(points.every((point) => point.created === 0)).toBe(true);
  });
});
