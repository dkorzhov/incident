import { ApiError } from "../api/client";

/**
 * Понятный текст ошибки API. `ApiError.detail` приходит с backend по-русски
 * (TASK.md §3), поэтому показываем его как есть; иначе — запасной текст.
 */
export function describeError(cause: unknown, fallback: string): string {
  if (cause instanceof ApiError) {
    return cause.message.trim() || fallback;
  }
  return fallback;
}

/**
 * Ошибки полей из ответа 400 (`errors: [{field, reason}]`) в виде карты
 * `поле → причина`. Используется формами, чтобы подсветить конкретный ввод.
 */
export function fieldErrors(cause: unknown): Record<string, string> {
  const result: Record<string, string> = {};
  if (!(cause instanceof ApiError)) {
    return result;
  }
  for (const error of cause.errors) {
    if (error.field && error.reason) {
      result[error.field] = error.reason;
    }
  }
  return result;
}
