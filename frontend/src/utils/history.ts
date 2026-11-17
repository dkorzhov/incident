import type {
  HistoryEventType,
  HistoryPayload,
  IncidentPriority,
  IncidentStatus,
} from "../api/types";
import { PRIORITY_LABELS, STATUS_LABELS } from "./labels";

/** Короткая подпись типа события истории. */
export const HISTORY_TYPE_LABELS: Record<HistoryEventType, string> = {
  created: "Создание",
  assigned: "Назначение",
  status_changed: "Смена статуса",
  priority_changed: "Смена приоритета",
  commented: "Комментарий",
  resolved: "Решение",
  fields_updated: "Изменение полей",
};

const STATUS_VALUES = new Set<string>(["New", "In Progress", "Resolved", "Closed"]);
const PRIORITY_VALUES = new Set<string>(["Critical", "High", "Medium", "Low"]);

function asString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

/** Значение поля из payload для показа человеку. */
function humanizeValue(raw: unknown): string {
  if (raw === null || raw === undefined || raw === "") {
    return "—";
  }
  const text = String(raw);
  if (STATUS_VALUES.has(text)) {
    return STATUS_LABELS[text as IncidentStatus];
  }
  if (PRIORITY_VALUES.has(text)) {
    return PRIORITY_LABELS[text as IncidentPriority];
  }
  return text;
}

/**
 * Человекочитаемое описание события истории по payload backend
 * (`{field: {from, to}}`), например «Статус: Новый → В работе».
 */
export function describeHistoryEvent(type: HistoryEventType, payload: HistoryPayload): string {
  switch (type) {
    case "created":
      return "Инцидент создан";
    case "commented": {
      const text = asString(payload.text?.to);
      return text ? `Добавлен комментарий: «${truncate(text, 80)}»` : "Добавлен комментарий";
    }
    case "resolved": {
      const resolution = asString(payload.resolution?.to);
      return resolution ? `Решение: «${truncate(resolution, 80)}»` : "Инцидент решён";
    }
    case "assigned": {
      const before = asString(payload.assignee?.from) ?? "без ответственного";
      const after = asString(payload.assignee?.to) ?? "без ответственного";
      return `Ответственный: ${before} → ${after}`;
    }
    default:
      break;
  }

  const parts: string[] = [];
  for (const [field, change] of Object.entries(payload)) {
    if (field === "assignee_name") {
      continue;
    }
    parts.push(
      `${FIELD_LABELS[field] ?? field}: ${humanizeValue(change?.from)} → ${humanizeValue(change?.to)}`,
    );
  }
  if (parts.length === 0) {
    return HISTORY_TYPE_LABELS[type];
  }
  const prefix = type === "fields_updated" ? "Изменены поля — " : "";
  return `${prefix}${parts.join("; ")}`;
}

const FIELD_LABELS: Record<string, string> = {
  title: "Название",
  description: "Описание",
  category: "Категория",
  priority: "Приоритет",
  status: "Статус",
  assignee_id: "Ответственный",
  assignee: "Ответственный",
  resolution: "Решение",
  text: "Комментарий",
};

function truncate(value: string, limit: number): string {
  return value.length > limit ? `${value.slice(0, limit - 1)}…` : value;
}
