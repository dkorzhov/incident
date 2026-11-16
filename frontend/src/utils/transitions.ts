import type { IncidentStatus } from "../api/types";
import { STATUS_LABELS } from "./labels";

/**
 * Подписи кнопок для переходов, которые разрешил backend.
 *
 * Набор доступных действий UI не вычисляет: он берётся из
 * `allowed_transitions` карточки (ADR 0003 §4). Здесь только человеческие
 * подписи — если сервер однажды разрешит новый переход, кнопка появится
 * с понятным названием, а не исчезнет.
 */
export type StatusActionKind = "take" | "close" | "generic";

export interface StatusAction {
  target: IncidentStatus;
  label: string;
  kind: StatusActionKind;
}

/** Целевой статус, для которого нужен текст решения (TASK.md §2). */
export const RESOLVE_TARGET: IncidentStatus = "Resolved";

const KNOWN_ACTIONS: Partial<Record<IncidentStatus, { label: string; kind: StatusActionKind }>> = {
  "In Progress": { label: "Взять в работу", kind: "take" },
  Closed: { label: "Закрыть", kind: "close" },
};

/** Кнопки немедленных действий: все переходы, кроме требующего resolution. */
export function immediateStatusActions(transitions: readonly IncidentStatus[]): StatusAction[] {
  return transitions
    .filter((target) => target !== RESOLVE_TARGET)
    .map((target) => {
      const known = KNOWN_ACTIONS[target];
      if (known) {
        return { target, label: known.label, kind: known.kind };
      }
      return {
        target,
        label: `Перевести в «${STATUS_LABELS[target]}»`,
        kind: "generic" as const,
      };
    });
}

/** Можно ли сейчас перевести инцидент в Resolved (форма решения). */
export function canResolve(transitions: readonly IncidentStatus[]): boolean {
  return transitions.includes(RESOLVE_TARGET);
}
