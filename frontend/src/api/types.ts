/**
 * Типы REST API IT Incident Tracker (TASK.md §3, ADR 0003).
 *
 * Значения enum-ов повторяют backend один в один — UI показывает их как есть
 * и никогда не переводит их «на свою сторону», кроме подписей в фильтрах.
 */

export type IncidentCategory = "Network" | "Mail" | "Portal" | "Database" | "Workplace" | "Other";

export type IncidentPriority = "Critical" | "High" | "Medium" | "Low";

export type IncidentStatus = "New" | "In Progress" | "Resolved" | "Closed";

export type HistoryEventType =
  | "created"
  | "assigned"
  | "status_changed"
  | "priority_changed"
  | "commented"
  | "resolved"
  | "fields_updated";

export type UserRole = "engineer" | "manager";

/** Короткая карточка пользователя во вложенных объектах (`assignee`, `actor`, `author`). */
export interface UserBrief {
  id: number;
  name: string;
}

/** Пользователь из `/api/users` — используется в селекторе текущего пользователя. */
export interface User extends UserBrief {
  role: UserRole;
}

/** Инцидент в реестре (`GET /api/incidents`, ответы на изменения). */
export interface Incident {
  id: string;
  title: string;
  description: string;
  category: IncidentCategory;
  priority: IncidentPriority;
  status: IncidentStatus;
  assignee_id: number | null;
  /** Сервер вкладывает имя ответственного; поле может отсутствовать в старых ответах. */
  assignee?: UserBrief | null;
  resolution?: string | null;
  created_at: string;
  updated_at: string;
}

/** Комментарий в карточке инцидента. */
export interface Comment {
  id: number;
  incident_id: string;
  author_id: number;
  author: UserBrief;
  text: string;
  created_at: string;
}

/** Значение одного поля в истории: «было/стало». */
export interface HistoryChange {
  from?: unknown;
  to?: unknown;
}

/** Payload события истории: `{field: {from, to}}`. */
export type HistoryPayload = Record<string, HistoryChange>;

/** Событие истории инцидента. */
export interface HistoryEvent {
  id: number;
  incident_id: string;
  actor_id: number;
  actor: UserBrief;
  type: HistoryEventType;
  payload: HistoryPayload;
  created_at: string;
}

/** Карточка инцидента: поля реестра + переходы + комментарии + история. */
export interface IncidentDetail extends Incident {
  /** Статусы, в которые можно перевести инцидент сейчас (считает backend). */
  allowed_transitions: IncidentStatus[];
  comments: Comment[];
  history: HistoryEvent[];
}

/** Ссылка на инцидент в ленте активности дашборда. */
export interface IncidentRef {
  id: string;
  title: string;
}

/** Последнее событие истории в ленте дашборда. */
export interface RecentActivity {
  id: number;
  incident_id: string;
  incident: IncidentRef;
  actor: UserBrief;
  type: HistoryEventType;
  payload: HistoryPayload;
  created_at: string;
}

/** KPI-карточки дашборда. */
export interface DashboardCounts {
  open: number;
  new: number;
  in_progress: number;
  critical: number;
  resolved_today: number;
}

/** `by_priority` всегда содержит все четыре ключа, включая нули. */
export type PriorityCounts = Record<IncidentPriority, number>;

/** Ответ `GET /api/dashboard`. */
export interface Dashboard {
  counts: DashboardCounts;
  by_priority: PriorityCounts;
  recent_activity: RecentActivity[];
}

/** Query-параметры реестра. Пустые значения означают «без фильтра». */
export interface IncidentsQuery {
  q?: string;
  status?: IncidentStatus;
  priority?: IncidentPriority;
}

/** Тело `POST /api/incidents`. */
export interface IncidentCreateBody {
  title: string;
  description?: string | null;
  category: IncidentCategory;
  priority: IncidentPriority;
  assignee_id?: number | null;
}

/**
 * Тело `PATCH /api/incidents/{id}`: отсутствующее поле не меняется,
 * явный `null` очищает значение (`description`, `assignee_id`).
 */
export interface IncidentUpdateBody {
  title?: string;
  description?: string | null;
  category?: IncidentCategory;
  priority?: IncidentPriority;
  assignee_id?: number | null;
}

/** Тело `PATCH /api/incidents/{id}/status` — один шаг автомата TASK.md §2. */
export interface IncidentStatusBody {
  status: IncidentStatus;
  resolution?: string | null;
}

/** Тело `POST /api/incidents/{id}/comments`. */
export interface CommentCreateBody {
  text: string;
}

/** Ошибка поля из ответа 400: `{field, reason}`. */
export interface FieldError {
  field: string;
  reason: string;
}

/** Полный набор значений enum-ов для селектов и проверок. */
export const INCIDENT_STATUSES: readonly IncidentStatus[] = [
  "New",
  "In Progress",
  "Resolved",
  "Closed",
] as const;

export const INCIDENT_PRIORITIES: readonly IncidentPriority[] = [
  "Critical",
  "High",
  "Medium",
  "Low",
] as const;

export const INCIDENT_CATEGORIES: readonly IncidentCategory[] = [
  "Network",
  "Mail",
  "Portal",
  "Database",
  "Workplace",
  "Other",
] as const;
