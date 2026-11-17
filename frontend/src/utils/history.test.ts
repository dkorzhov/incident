import { describe, expect, it } from "vitest";

import { describeHistoryEvent, HISTORY_TYPE_LABELS } from "../utils/history";

describe("describeHistoryEvent", () => {
  it("переводит смену статуса на русские подписи", () => {
    expect(
      describeHistoryEvent("status_changed", { status: { from: "New", to: "In Progress" } }),
    ).toBe("Статус: Новый → В работе");
  });

  it("показывает решение и комментарий по payload", () => {
    expect(
      describeHistoryEvent("resolved", {
        status: { from: "In Progress", to: "Resolved" },
        resolution: { from: null, to: "Перезапущен шлюз" },
      }),
    ).toBe("Решение: «Перезапущен шлюз»");

    expect(describeHistoryEvent("commented", { text: { from: null, to: "Проверяю" } })).toBe(
      "Добавлен комментарий: «Проверяю»",
    );
  });

  it("показывает ответственного и его снятие", () => {
    expect(
      describeHistoryEvent("assigned", {
        assignee_id: { from: 1, to: 2 },
        assignee: { from: "Иван Петров", to: "Иванов Иван" },
      }),
    ).toBe("Ответственный: Иван Петров → Иванов Иван");

    expect(describeHistoryEvent("assigned", { assignee: { from: "Иван Петров", to: null } })).toBe(
      "Ответственный: Иван Петров → без ответственного",
    );
  });

  it("описывает изменение полей и пустой payload без падения", () => {
    expect(describeHistoryEvent("fields_updated", { title: { from: "A", to: "B" } })).toBe(
      "Изменены поля — Название: A → B",
    );
    expect(describeHistoryEvent("created", {})).toBe("Инцидент создан");
    expect(describeHistoryEvent("priority_changed", {})).toBe(HISTORY_TYPE_LABELS.priority_changed);
  });
});
