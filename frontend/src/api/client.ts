export type UserRole = "engineer" | "manager";

export interface User {
  id: number;
  name: string;
  role: UserRole;
}

/** Ошибка API: статус и понятный текст из `{ detail }`. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // Заголовки вызывающей стороны сохраняются; Accept — только значение по умолчанию.
  const headers = new Headers(init?.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`/api${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Не удалось связаться с сервером. Проверьте, что backend запущен.");
  }

  if (!response.ok) {
    const detail = await readDetail(response);
    throw new ApiError(response.status, detail ?? defaultMessage(response.status));
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

async function readDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    const detail = body.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (typeof item === "object" && item && "msg" in item ? String(item.msg) : ""))
        .filter(Boolean)
        .join("; ");
    }
    return null;
  } catch {
    return null;
  }
}

export const api = {
  health: (init?: RequestInit) =>
    request<{ status: string; service: string; version: string }>("/health", init),
  users: (init?: RequestInit) => request<User[]>("/users", init),
};
