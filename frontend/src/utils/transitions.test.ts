import { describe, expect, it } from "vitest";

import type { IncidentStatus } from "../api/types";
import { canResolve, immediateStatusActions } from "../utils/transitions";

describe("transitions", () => {
  it("строит кнопки по переходам сервера, кроме Resolved", () => {
    const actions = immediateStatusActions(["In Progress"]);
    expect(actions).toEqual([{ target: "In Progress", label: "Взять в работу", kind: "take" }]);

    expect(immediateStatusActions(["Closed"])).toEqual([
      { target: "Closed", label: "Закрыть", kind: "close" },
    ]);
  });

  it("не предлагает немедленных действий, если доступен только Resolved", () => {
    expect(immediateStatusActions(["Resolved"])).toEqual([]);
    expect(canResolve(["Resolved"])).toBe(true);
  });

  it("для пустого набора переходов ничего не показывает (Closed)", () => {
    const transitions: IncidentStatus[] = [];
    expect(immediateStatusActions(transitions)).toEqual([]);
    expect(canResolve(transitions)).toBe(false);
  });

  it("сохраняет порядок переходов из ответа API", () => {
    const actions = immediateStatusActions(["In Progress", "Closed"]);
    expect(actions.map((action) => action.target)).toEqual(["In Progress", "Closed"]);
  });
});
