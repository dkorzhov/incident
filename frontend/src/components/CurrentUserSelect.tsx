import { useEffect, useState } from "react";

import { ApiError, api, type User } from "../api/client";

/**
 * Селектор текущего пользователя (упрощение MVP вместо аутентификации).
 * Выбранный id уйдёт на backend заголовком `X-User-Id` в следующих тикетах.
 */
export function CurrentUserSelect() {
  const [users, setUsers] = useState<User[]>([]);
  const [currentUserId, setCurrentUserId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let ignore = false;

    api
      .users()
      .then((data) => {
        if (ignore) {
          return;
        }
        setUsers(data);
        setCurrentUserId(data[0] ? String(data[0].id) : "");
      })
      .catch((cause: unknown) => {
        if (ignore) {
          return;
        }
        setError(cause instanceof ApiError ? cause.message : "Не удалось загрузить пользователей");
      })
      .finally(() => {
        if (!ignore) {
          setIsLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, []);

  if (error) {
    return (
      <span className="user-select user-select--error" role="alert">
        {error}
      </span>
    );
  }

  return (
    <label className="user-select">
      <span className="user-select__label">Текущий пользователь</span>
      <select
        value={currentUserId}
        disabled={isLoading || users.length === 0}
        onChange={(event) => setCurrentUserId(event.target.value)}
      >
        {isLoading && <option value="">Загрузка…</option>}
        {!isLoading && users.length === 0 && <option value="">Нет пользователей</option>}
        {users.map((user) => (
          <option key={user.id} value={user.id}>
            {user.name}
          </option>
        ))}
      </select>
    </label>
  );
}
