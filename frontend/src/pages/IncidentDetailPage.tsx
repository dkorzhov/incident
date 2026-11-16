import { useCallback, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError, api, type IncidentDetail, type IncidentStatus } from "../api/client";
import { AssigneeText, CategoryBadge, PriorityBadge, StatusBadge } from "../components/Badges";
import { CommentForm, CommentList } from "../components/Comments";
import { HistoryList } from "../components/HistoryList";
import { PageHeader } from "../components/KpiCard";
import { ErrorMessage, LoadingMessage } from "../components/StateMessage";
import { StatusActions } from "../components/StatusActions";
import { type TabItem, Tabs } from "../components/Tabs";
import { useApiData } from "../hooks/useApiData";
import { useUsers } from "../hooks/useUsers";
import { describeError } from "../utils/apiError";
import { formatDateTime } from "../utils/labels";

type TabId = "info" | "history" | "comments";

const TAB_LABELS: readonly { id: TabId; label: string }[] = [
  { id: "info", label: "Информация" },
  { id: "history", label: "История" },
  { id: "comments", label: "Комментарии" },
];

const ACTION_FALLBACK = "Не удалось сохранить изменение. Повторите попытку.";

/** Текст сервера как отдельное предложение — без слипания с нашей припиской. */
function withPeriod(text: string): string {
  return /[.!?…]$/.test(text.trim()) ? text.trim() : `${text.trim()}.`;
}

/**
 * Карточка инцидента: информация, история и комментарии.
 *
 * Ключ по номеру: при переходе на другую карточку компонент монтируется
 * заново, поэтому вкладки, текст решения и ошибки не «переезжают» в чужой
 * инцидент.
 */
export function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  return <IncidentDetailView key={id ?? ""} incidentId={id ?? ""} />;
}

/**
 * Действия по статусу рисуются только по `allowed_transitions` из ответа API,
 * поэтому UI не может предложить недопустимый переход (TASK.md §2). Сервер
 * остаётся источником истины: гонку статусов (409) показываем текстом и
 * перезагружаем карточку — состояние на экране снова совпадает с БД.
 */
function IncidentDetailView({ incidentId }: { incidentId: string }) {
  const [tab, setTab] = useState<TabId>("info");
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingStatus, setPendingStatus] = useState<IncidentStatus | null>(null);
  const [isCommentSubmitting, setIsCommentSubmitting] = useState(false);
  const [isAssigneeSaving, setIsAssigneeSaving] = useState(false);

  const loadIncident = useCallback(() => api.incidents.get(incidentId), [incidentId]);
  const {
    data: incident,
    error,
    isLoading,
    reload,
  } = useApiData<IncidentDetail>(loadIncident, "Не удалось загрузить инцидент.");

  const usersState = useUsers();

  /**
   * Выполнить изменение, затем перечитать карточку. `false` — ошибка показана
   * пользователю; для 404/409 данные на экране заведомо устарели, поэтому
   * перечитываем их в любом случае.
   */
  const runAndRefresh = useCallback(
    async (action: () => Promise<unknown>): Promise<boolean> => {
      setActionError(null);
      try {
        await action();
        // Дожидаемся свежих данных: кнопки не должны остаться от старого статуса.
        await reload();
        return true;
      } catch (cause) {
        const status = cause instanceof ApiError ? cause.status : null;
        const base = describeError(cause, ACTION_FALLBACK);
        // 409 — гонка статусов: сервер отклонил переход по актуальному
        // состоянию, значит данные на экране устарели.
        setActionError(
          status === 409
            ? `${withPeriod(base)} Данные карточки перезагружены — проверьте актуальный статус.`
            : base,
        );
        if (status === 409 || status === 404) {
          await reload();
        }
        return false;
      }
    },
    [reload],
  );

  const handleStatusChange = useCallback(
    async (target: IncidentStatus, resolution?: string): Promise<boolean> => {
      setPendingStatus(target);
      try {
        return await runAndRefresh(() =>
          api.incidents.changeStatus(incidentId, {
            status: target,
            ...(resolution !== undefined ? { resolution } : {}),
          }),
        );
      } finally {
        setPendingStatus(null);
      }
    },
    [incidentId, runAndRefresh],
  );

  const handleCommentSubmit = useCallback(
    async (text: string): Promise<boolean> => {
      setIsCommentSubmitting(true);
      try {
        return await runAndRefresh(() => api.incidents.addComment(incidentId, { text }));
      } finally {
        setIsCommentSubmitting(false);
      }
    },
    [incidentId, runAndRefresh],
  );

  const handleAssigneeChange = useCallback(
    async (nextAssigneeId: number | null) => {
      setIsAssigneeSaving(true);
      try {
        await runAndRefresh(() =>
          api.incidents.update(incidentId, { assignee_id: nextAssigneeId }),
        );
      } finally {
        setIsAssigneeSaving(false);
      }
    },
    [incidentId, runAndRefresh],
  );

  if (!incidentId) {
    return (
      <section className="page">
        <PageHeader title="Инцидент" />
        <div className="panel">
          <ErrorMessage message="В адресе страницы нет номера инцидента." />
          <p className="panel__footer-link">
            <Link to="/incidents">Вернуться в реестр</Link>
          </p>
        </div>
      </section>
    );
  }

  // При переходе на другую карточку старые данные не показываем: иначе на
  // экране на миг оказался бы чужой инцидент с уже другими действиями.
  if (incident === null || incident.id !== incidentId) {
    return (
      <section className="page">
        <PageHeader
          title={`Инцидент ${incidentId}`}
          actions={
            <Link className="button button--secondary" to="/incidents">
              К реестру
            </Link>
          }
        />
        <div className="panel">
          {error ? (
            <ErrorMessage message={error} onRetry={reload} />
          ) : (
            <LoadingMessage label="Загрузка карточки…" />
          )}
        </div>
      </section>
    );
  }

  const isClosed = incident.status === "Closed";
  const tabs: TabItem[] = TAB_LABELS.map((item) =>
    item.id === "comments" && incident.comments.length > 0
      ? { ...item, badge: incident.comments.length }
      : item,
  );

  return (
    <section className="page">
      <PageHeader
        title={`${incident.id} · ${incident.title}`}
        description={`Создан ${formatDateTime(incident.created_at)} · обновлён ${formatDateTime(
          incident.updated_at,
        )}`}
        actions={
          <Link className="button button--secondary" to="/incidents">
            К реестру
          </Link>
        }
      />

      <div className="panel incident-card" aria-busy={isLoading}>
        {isLoading && (
          <p className="incident-card__refreshing" role="status">
            Обновляем карточку…
          </p>
        )}

        {error && <ErrorMessage message={error} onRetry={reload} />}

        <div className="incident-card__badges">
          <StatusBadge status={incident.status} />
          <PriorityBadge priority={incident.priority} />
          <CategoryBadge category={incident.category} />
          <span className="incident-card__assignee">
            Ответственный: <AssigneeText assignee={incident.assignee} />
          </span>
        </div>

        {actionError && (
          <div className="alert alert--error" role="alert">
            <div>
              <strong>Изменение не применено</strong>
              <p className="alert__text">{actionError}</p>
            </div>
            <button
              type="button"
              className="button button--secondary"
              onClick={() => setActionError(null)}
            >
              Скрыть
            </button>
          </div>
        )}

        <StatusActions
          // Ключ сбрасывает локальную форму решения, когда меняется инцидент
          // или его статус: иначе текст решения «переезжал» бы в другую карточку.
          key={`${incident.id}-${incident.status}`}
          transitions={incident.allowed_transitions}
          onChangeStatus={handleStatusChange}
          pendingTarget={pendingStatus}
          isRefreshing={isLoading}
        />

        <div className="assignee-form">
          <label className="field__label" htmlFor="assignee-select">
            Ответственный
          </label>
          <select
            id="assignee-select"
            value={incident.assignee_id ?? ""}
            disabled={isClosed || isAssigneeSaving || isLoading || usersState.isLoading}
            onChange={(event) => {
              const raw = event.target.value;
              void handleAssigneeChange(raw === "" ? null : Number(raw));
            }}
          >
            <option value="">
              {usersState.isLoading
                ? "Загрузка…"
                : usersState.users.length === 0
                  ? "Нет пользователей"
                  : "Не назначен"}
            </option>
            {usersState.users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.name}
              </option>
            ))}
            {/* Ответственного может не быть в справочнике — имя не теряем. */}
            {incident.assignee &&
              !usersState.users.some((user) => user.id === incident.assignee_id) && (
                <option value={incident.assignee_id ?? ""}>{incident.assignee.name}</option>
              )}
          </select>
          {isClosed ? (
            <span className="field__hint">Закрытый инцидент неизменяем.</span>
          ) : (
            <span className="field__hint">Смена сохраняется сразу и попадает в историю.</span>
          )}
          {usersState.error && (
            <span className="field__error">Справочник недоступен: {usersState.error}</span>
          )}
        </div>

        <Tabs
          items={tabs}
          activeId={tab}
          onChange={(next) => setTab(next as TabId)}
          label="Разделы карточки"
        >
          {tab === "info" && <InfoTab incident={incident} />}
          {tab === "history" && <HistoryList events={incident.history} />}
          {tab === "comments" && (
            <div className="comments">
              <CommentList comments={incident.comments} />
              <CommentForm
                onSubmit={handleCommentSubmit}
                isSubmitting={isCommentSubmitting}
                disabledReason={
                  isClosed
                    ? "Инцидент закрыт: новые комментарии сервер не принимает (409)."
                    : undefined
                }
              />
            </div>
          )}
        </Tabs>
      </div>
    </section>
  );
}

/** Вкладка «Информация»: описание, решение и служебные поля. */
function InfoTab({ incident }: { incident: IncidentDetail }) {
  return (
    <div className="info">
      <dl className="info__grid">
        <div className="info__row">
          <dt>Номер</dt>
          <dd className="info__id">{incident.id}</dd>
        </div>
        <div className="info__row">
          <dt>Название</dt>
          <dd>{incident.title}</dd>
        </div>
        <div className="info__row">
          <dt>Категория</dt>
          <dd>
            <CategoryBadge category={incident.category} />
          </dd>
        </div>
        <div className="info__row">
          <dt>Ответственный</dt>
          <dd>
            <AssigneeText assignee={incident.assignee} />
          </dd>
        </div>
        <div className="info__row">
          <dt>Создан</dt>
          <dd>{formatDateTime(incident.created_at)}</dd>
        </div>
        <div className="info__row">
          <dt>Обновлён</dt>
          <dd>{formatDateTime(incident.updated_at)}</dd>
        </div>
      </dl>

      <div className="info__section">
        <h4 className="info__heading">Описание</h4>
        {incident.description.trim() ? (
          <p className="info__text">{incident.description}</p>
        ) : (
          <p className="info__text info__text--empty">Описание не заполнено.</p>
        )}
      </div>

      {incident.resolution && (
        <div className="info__section">
          <h4 className="info__heading">Решение</h4>
          <p className="info__text">{incident.resolution}</p>
        </div>
      )}
    </div>
  );
}
