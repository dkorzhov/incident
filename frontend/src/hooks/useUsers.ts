import { useCallback, useMemo } from "react";

import { ApiError, api, type User } from "../api/client";
import { useApiData } from "./useApiData";

interface UsersResult {
  users: User[];
  isLoading: boolean;
  error: string | null;
  reload: () => void;
}

const EMPTY_USERS: User[] = [];

/** Справочник пользователей из `/api/users` (общий для селектора и страницы). */
export function useUsers(): UsersResult {
  const loader = useCallback(() => api.users(), []);
  const { data, isLoading, error, reload } = useApiData(
    loader,
    "Не удалось загрузить список пользователей.",
  );

  // Стабильная ссылка: без неё эффект выбора пользователя перезапускался бы каждый рендер.
  const users = useMemo(() => data ?? EMPTY_USERS, [data]);

  return { users, isLoading, error, reload };
}

/** Текст ошибки с учётом уже разобранного ApiError. */
export function describeApiError(cause: unknown, fallback: string): string {
  return cause instanceof ApiError ? cause.message : fallback;
}
