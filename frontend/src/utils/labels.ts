import type { IncidentPriority, IncidentStatus } from "../api/types";

/** Человекочитаемые подписи enum-ов backend (значения в API не меняются). */
export const STATUS_LABELS: Record<IncidentStatus, string> = {
  New: "Новый",
  "In Progress": "В работе",
  Resolved: "Решён",
  Closed: "Закрыт",
};

/** Подписи приоритетов для интерфейса; значения enum в API не меняются. */
export const PRIORITY_LABELS: Record<IncidentPriority, string> = {
  Critical: "Критический",
  High: "Высокий",
  Medium: "Средний",
  Low: "Низкий",
};

/** CSS-модификатор бейджа статуса: `badge--status-new` и т.д. */
export function statusModifier(status: IncidentStatus): string {
  return `badge--status-${status.toLowerCase().replaceAll(" ", "-")}`;
}

/** CSS-модификатор бейджа приоритета: `badge--priority-critical` и т.д. */
export function priorityModifier(priority: IncidentPriority): string {
  return `badge--priority-${priority.toLowerCase()}`;
}

/** Дата из ISO-строки в локальном формате `ДД.ММ.ГГГГ ЧЧ:ММ`. */
export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

/** Время события для ленты активности: `ДД.ММ ЧЧ:ММ`. */
export function formatShortDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
