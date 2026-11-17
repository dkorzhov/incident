import { useCallback, useMemo } from "react";
import { Link } from "react-router-dom";

import { api, type Dashboard, type Incident, type RecentActivity } from "../api/client";
import { buildDynamics, DynamicsChart } from "../components/DynamicsChart";
import { KpiCard, PageHeader } from "../components/KpiCard";
import { PriorityChart } from "../components/PriorityChart";
import { ErrorMessage, LoadingMessage, StateMessage } from "../components/StateMessage";
import { useApiData } from "../hooks/useApiData";
import { describeHistoryEvent, HISTORY_TYPE_LABELS } from "../utils/history";
import { formatShortDateTime } from "../utils/labels";

/** Дашборд: KPI, разрез по приоритетам, динамика за 7 дней, лента активности. */
export function DashboardPage() {
  const loadDashboard = useCallback(() => api.dashboard.get(), []);
  const loadIncidents = useCallback(() => api.incidents.list(), []);

  const dashboardState = useApiData<Dashboard>(loadDashboard, "Не удалось загрузить показатели.");
  const incidentsState = useApiData<Incident[]>(loadIncidents, "Не удалось загрузить реестр.");

  const dashboard = dashboardState.data;
  const counts = dashboard?.counts;
  const isLoading = dashboardState.isLoading && dashboard === null;

  const dynamics = useMemo(
    () => (incidentsState.data ? buildDynamics(incidentsState.data) : []),
    [incidentsState.data],
  );

  const reloadAll = () => {
    dashboardState.reload();
    incidentsState.reload();
  };

  return (
    <section className="page">
      <PageHeader
        title="Дашборд"
        description="Сводка по открытым инцидентам и нагрузке команды. Данные считает backend по базе."
        actions={
          <button
            type="button"
            className="button button--secondary"
            onClick={reloadAll}
            disabled={dashboardState.isLoading || incidentsState.isLoading}
          >
            {dashboardState.isLoading || incidentsState.isLoading ? "Обновление…" : "Обновить"}
          </button>
        }
      />

      {dashboardState.error && dashboard === null && (
        <ErrorMessage message={dashboardState.error} onRetry={dashboardState.reload} />
      )}

      <div className="kpi-grid">
        <KpiCard label="Всего открытых" value={counts?.open ?? null} isLoading={!dashboard} />
        <KpiCard label="Новых" value={counts?.new ?? null} tone="info" isLoading={!dashboard} />
        <KpiCard label="В работе" value={counts?.in_progress ?? null} isLoading={!dashboard} />
        <KpiCard
          label="Критических"
          value={counts?.critical ?? null}
          tone="critical"
          isLoading={!dashboard}
          hint="Critical и не закрыт"
        />
        <KpiCard
          label="Решено сегодня"
          value={counts?.resolved_today ?? null}
          tone="success"
          isLoading={!dashboard}
          hint="Переведены в Resolved за сутки UTC"
        />
      </div>

      {dashboardState.error && dashboard !== null && (
        <p className="alert alert--error alert--compact" role="alert">
          Часть данных недоступна: {dashboardState.error}
        </p>
      )}

      <div className="dashboard-grid">
        <article className="panel panel--chart">
          <header className="panel__header">
            <h3 className="panel__title">По приоритетам</h3>
            <p className="panel__subtitle">Все инциденты, включая закрытые</p>
          </header>
          {dashboard ? (
            <PriorityChart byPriority={dashboard.by_priority} />
          ) : dashboardState.error ? (
            <StateMessage title="Диаграмма недоступна" text={dashboardState.error} />
          ) : (
            <LoadingMessage label="Загрузка диаграммы…" />
          )}
        </article>

        <article className="panel panel--chart">
          <header className="panel__header">
            <h3 className="panel__title">Динамика инцидентов</h3>
            <p className="panel__subtitle">Последние 7 дней по реестру</p>
          </header>
          {incidentsState.error ? (
            <StateMessage
              title="График недоступен"
              text={incidentsState.error}
              onRetry={incidentsState.reload}
            />
          ) : incidentsState.data === null ? (
            <LoadingMessage label="Загрузка графика…" />
          ) : (
            <DynamicsChart points={dynamics} />
          )}
        </article>

        <article className="panel panel--activity">
          <header className="panel__header">
            <h3 className="panel__title">Недавняя активность</h3>
            <p className="panel__subtitle">Последние события истории</p>
          </header>
          {dashboard === null ? (
            isLoading ? (
              <LoadingMessage label="Загрузка активности…" />
            ) : (
              <StateMessage
                title="Активность недоступна"
                text={dashboardState.error ?? "Нет данных."}
              />
            )
          ) : dashboard.recent_activity.length === 0 ? (
            <StateMessage
              title="Активности пока нет"
              text="Создайте инцидент — события появятся здесь автоматически."
            />
          ) : (
            <ul className="activity-list">
              {dashboard.recent_activity.map((event) => (
                <ActivityItem key={event.id} event={event} />
              ))}
            </ul>
          )}
        </article>
      </div>
    </section>
  );
}

function ActivityItem({ event }: { event: RecentActivity }) {
  return (
    <li className="activity-item">
      <span className={`activity-item__dot activity-item__dot--${event.type}`} aria-hidden="true" />
      <div className="activity-item__body">
        <p className="activity-item__title">
          <Link to={`/incidents/${event.incident_id}`} className="activity-item__link">
            {event.incident_id}
          </Link>{" "}
          <span className="activity-item__incident">{event.incident.title}</span>
        </p>
        <p className="activity-item__meta">
          {event.actor.name} · {HISTORY_TYPE_LABELS[event.type]} ·{" "}
          {formatShortDateTime(event.created_at)}
        </p>
        <p className="activity-item__text">{describeHistoryEvent(event.type, event.payload)}</p>
      </div>
    </li>
  );
}
