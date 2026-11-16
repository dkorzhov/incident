/**
 * Текущий пользователь MVP (вместо аутентификации, TASK.md §1).
 *
 * Один модульный store: селектор в шапке пишет сюда выбранный id, api-клиент
 * читает его и отправляет заголовком `X-User-Id`. Значение переживает
 * перезагрузку страницы через localStorage; если хранилище недоступно
 * (приватный режим, запрет cookies) — работаем только в памяти.
 */

const STORAGE_KEY = "it-incident-tracker.current-user-id";

type Listener = (userId: number | null) => void;

function readStoredUserId(): number | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = Number.parseInt(raw, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  } catch {
    return null;
  }
}

function persistUserId(userId: number | null): void {
  try {
    if (userId === null) {
      window.localStorage.removeItem(STORAGE_KEY);
    } else {
      window.localStorage.setItem(STORAGE_KEY, String(userId));
    }
  } catch {
    // Хранилище недоступно — выбранный пользователь живёт до перезагрузки.
  }
}

let currentUserId: number | null = readStoredUserId();
const listeners = new Set<Listener>();

/** id текущего пользователя или `null`, если он ещё не выбран. */
export function getCurrentUserId(): number | null {
  return currentUserId;
}

/** Выбрать текущего пользователя; `null` — сбросить выбор. */
export function setCurrentUserId(userId: number | null): void {
  if (userId !== null && (!Number.isInteger(userId) || userId <= 0)) {
    return;
  }
  if (currentUserId === userId) {
    return;
  }
  currentUserId = userId;
  persistUserId(userId);
  for (const listener of listeners) {
    listener(userId);
  }
}

/** Подписка на смену пользователя (для `useSyncExternalStore`). */
export function subscribeCurrentUser(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
