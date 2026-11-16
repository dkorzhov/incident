import { useEffect, useState } from "react";

import { ApiError, api, type User } from "../api/client";

export function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let ignore = false;

    api
      .users()
      .then((data) => {
        if (!ignore) {
          setUsers(data);
        }
      })
      .catch((cause: unknown) => {
        if (!ignore) {
          setError(
            cause instanceof ApiError ? cause.message : "Не удалось загрузить пользователей",
          );
        }
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

  return (
    <section className="placeholder">
      <h2>Пользователи</h2>
      {isLoading && <p>Загрузка…</p>}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!isLoading && !error && (
        <ul className="user-list">
          {users.map((user) => (
            <li key={user.id}>
              <strong>{user.name}</strong> <span className="role-badge">{user.role}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
