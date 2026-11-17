import { useEffect, useMemo } from "react";

import { setCurrentUserId } from "../api/currentUser";
import { useCurrentUserId } from "../hooks/useCurrentUserId";
import { useUsers } from "../hooks/useUsers";

/**
 * Селектор текущего пользователя (упрощение MVP вместо аутентификации).
 * Выбранный id живёт в общем store и уходит на backend заголовком `X-User-Id`.
 */
export function CurrentUserSelect() {
  const { users, isLoading, error, reload } = useUsers();
  const currentUserId = useCurrentUserId();

  // Первый пользователь из справочника становится текущим, если выбор пуст
  // или сохранённый id больше не существует.
  useEffect(() => {
    if (users.length === 0) {
      return;
    }
    const stillExists = users.some((user) => user.id === currentUserId);
    if (!stillExists) {
      const fallback = users[0];
      if (fallback) {
        setCurrentUserId(fallback.id);
      }
    }
  }, [users, currentUserId]);

  const selectedUser = useMemo(
    () => users.find((user) => user.id === currentUserId) ?? null,
    [users, currentUserId],
  );

  if (error) {
    return (
      <div className="user-select user-select--error" role="alert">
        <span>{error}</span>
        <button type="button" className="button button--ghost" onClick={reload}>
          Повторить
        </button>
      </div>
    );
  }

  return (
    <label className="user-select">
      <span className="user-select__label">Текущий пользователь</span>
      <span className="user-select__avatar" aria-hidden="true">
        {selectedUser ? initials(selectedUser.name) : "?"}
      </span>
      <select
        value={currentUserId ?? ""}
        disabled={isLoading || users.length === 0}
        aria-label="Текущий пользователь"
        onChange={(event) => {
          const next = Number.parseInt(event.target.value, 10);
          setCurrentUserId(Number.isFinite(next) ? next : null);
        }}
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

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}
