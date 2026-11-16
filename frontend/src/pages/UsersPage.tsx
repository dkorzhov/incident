import type { UserRole } from "../api/types";
import { PageHeader } from "../components/KpiCard";
import { ErrorMessage, LoadingMessage, StateMessage } from "../components/StateMessage";
import { useUsers } from "../hooks/useUsers";

const ROLE_LABELS: Record<UserRole, string> = {
  engineer: "Инженер",
  manager: "Менеджер",
};

/** Список пользователей из `/api/users` (просмотр, без редактирования). */
export function UsersPage() {
  const { users, isLoading, error, reload } = useUsers();

  return (
    <section className="page">
      <PageHeader
        title="Пользователи"
        description="Справочник сотрудников компании. Текущий пользователь выбирается в шапке и передаётся в API заголовком X-User-Id."
      />

      <div className="panel">
        {error && <ErrorMessage message={error} onRetry={reload} />}

        {!error && isLoading && <LoadingMessage label="Загрузка пользователей…" />}

        {!error && !isLoading && users.length === 0 && (
          <StateMessage
            title="Пользователей нет"
            text="Backend не вернул ни одного пользователя. Проверьте demo-данные (SEED_DEMO)."
          />
        )}

        {!error && users.length > 0 && (
          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">ID</th>
                  <th scope="col">Имя</th>
                  <th scope="col">Роль</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td className="table__id">{user.id}</td>
                    <td className="table__title">{user.name}</td>
                    <td>
                      <span className="role-badge">{ROLE_LABELS[user.role]}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="table__caption">Всего пользователей: {users.length}</p>
          </div>
        )}
      </div>
    </section>
  );
}
