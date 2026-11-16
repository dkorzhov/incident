import { getCurrentUserId } from "./currentUser";
import type {
  Comment,
  CommentCreateBody,
  Dashboard,
  Incident,
  IncidentCreateBody,
  IncidentDetail,
  IncidentStatusBody,
  IncidentsQuery,
  IncidentUpdateBody,
  User,
} from "./types";

export type {
  Comment,
  CommentCreateBody,
  Dashboard,
  DashboardCounts,
  FieldError,
  HistoryChange,
  HistoryEvent,
  HistoryEventType,
  HistoryPayload,
  Incident,
  IncidentCategory,
  IncidentCreateBody,
  IncidentDetail,
  IncidentPriority,
  IncidentRef,
  IncidentStatus,
  IncidentStatusBody,
  IncidentsQuery,
  IncidentUpdateBody,
  PriorityCounts,
  RecentActivity,
  User,
  UserBrief,
  UserRole,
} from "./types";
export { INCIDENT_CATEGORIES, INCIDENT_PRIORITIES, INCIDENT_STATUSES } from "./types";

/** Ошибка API: HTTP-статус, понятный текст `detail` и ошибки по полям. */
export class ApiError extends Error {
  readonly status: number;
  readonly errors: { field: string; reason: string }[];

  constructor(status: number, message: string, errors: { field: string; reason: string }[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errors = errors;
  }
}

interface RequestOptions extends RequestInit {
  /** Добавлять `X-User-Id` текущего пользователя (обязателен для изменений). */
  withUser?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { withUser, ...init } = options;

  // Заголовки вызывающей стороны сохраняются; Accept — только значение по умолчанию.
  const headers = new Headers(init.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  if (init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (withUser) {
    const userId = getCurrentUserId();
    if (userId !== null && !headers.has("X-User-Id")) {
      headers.set("X-User-Id", String(userId));
    }
  }

  let response: Response;
  try {
    response = await fetch(`/api${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Не удалось связаться с сервером. Проверьте, что backend запущен.");
  }

  if (!response.ok) {
    const parsed = await readError(response);
    throw new ApiError(
      response.status,
      parsed?.detail ?? defaultMessage(response.status),
      parsed?.errors ?? [],
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

/** Понятный текст, когда сервер не прислал `detail`. */
function defaultMessage(status: number): string {
  if (status >= 502 && status <= 504) {
    return "Сервер временно недоступен. Проверьте, что backend запущен, и повторите попытку.";
  }
  if (status === 404) {
    return "Запрошенные данные не найдены.";
  }
  return `Запрос завершился с ошибкой ${status}. Попробуйте ещё раз.`;
}

interface ParsedError {
  detail: string;
  errors?: { field: string; reason: string }[];
}

async function readError(response: Response): Promise<ParsedError | null> {
  try {
    const body = (await response.json()) as { detail?: unknown; errors?: unknown };
    const errors = Array.isArray(body.errors)
      ? body.errors
          .filter(
            (item): item is { field: string; reason: string } =>
              typeof item === "object" &&
              item !== null &&
              "field" in item &&
              "reason" in item &&
              typeof item.field === "string" &&
              typeof item.reason === "string",
          )
          .map((item) => ({ field: item.field, reason: item.reason }))
      : [];

    const detail = body.detail;
    if (typeof detail === "string") {
      return { detail, errors };
    }
    // FastAPI-совместимая валидация: detail — массив объектов с `msg`.
    if (Array.isArray(detail)) {
      const message = detail
        .map((item) => (typeof item === "object" && item && "msg" in item ? String(item.msg) : ""))
        .filter(Boolean)
        .join("; ");
      return message ? { detail: message, errors } : null;
    }
    return null;
  } catch {
    return null;
  }
}

/** Собрать query-строку, выбросив пустые фильтры. */
function buildQuery(params: Record<string, string | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    const trimmed = value?.trim();
    if (trimmed) {
      search.set(key, trimmed);
    }
  }
  const result = search.toString();
  return result ? `?${result}` : "";
}

export const usersApi = {
  list: (init?: RequestInit) => request<User[]>("/users", init),
};

export const incidentsApi = {
  /** Реестр: `?q=` (ID и title), `?status=`, `?priority=`; новые сверху. */
  list: (params: IncidentsQuery = {}, init?: RequestInit) =>
    request<Incident[]>(
      `/incidents${buildQuery({
        q: params.q,
        status: params.status,
        priority: params.priority,
      })}`,
      init,
    ),
  get: (id: string, init?: RequestInit) =>
    request<IncidentDetail>(`/incidents/${encodeURIComponent(id)}`, init),
  create: (body: IncidentCreateBody, init?: RequestInit) =>
    request<Incident>("/incidents", {
      method: "POST",
      body: JSON.stringify(body),
      ...init,
      withUser: true,
    }),
  update: (id: string, body: IncidentUpdateBody, init?: RequestInit) =>
    request<Incident>(`/incidents/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
      ...init,
      withUser: true,
    }),
  changeStatus: (id: string, body: IncidentStatusBody, init?: RequestInit) =>
    request<Incident>(`/incidents/${encodeURIComponent(id)}/status`, {
      method: "PATCH",
      body: JSON.stringify(body),
      ...init,
      withUser: true,
    }),
  addComment: (id: string, body: CommentCreateBody, init?: RequestInit) =>
    request<Comment>(`/incidents/${encodeURIComponent(id)}/comments`, {
      method: "POST",
      body: JSON.stringify(body),
      ...init,
      withUser: true,
    }),
};

export const dashboardApi = {
  get: (init?: RequestInit) => request<Dashboard>("/dashboard", init),
};

/** Единая точка входа клиента: `api.incidents.list(...)`, `api.dashboard.get()`. */
export const api = {
  health: (init?: RequestInit) =>
    request<{ status: string; service: string; version: string }>("/health", init),
  users: usersApi.list,
  incidents: incidentsApi,
  dashboard: dashboardApi,
};
