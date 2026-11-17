import { useCallback, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  api,
  type Dashboard,
  INCIDENT_PRIORITIES,
  INCIDENT_STATUSES,
  type Incident,
  type IncidentPriority,
  type IncidentStatus,
} from "../api/client";
import { AssigneeText, PriorityBadge, StatusBadge } from "../components/Badges";
import { KpiCard, PageHeader } from "../components/KpiCard";
import { ErrorMessage, LoadingMessage, StateMessage } from "../components/StateMessage";
import { useApiData } from "../hooks/useApiData";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { formatDateTime, PRIORITY_LABELS, STATUS_LABELS } from "../utils/labels";

interface Filters {
  q: string;
  status: IncidentStatus | "";
  priority: IncidentPriority | "";
}

const EMPTY_FILTERS: Filters = { q: "", status: "", priority: "" };

function isBlank(value: string): boolean {
  return value.trim().length === 0;
}

/** Реестр инцидентов: KPI, поиск по ID/названию, фильтры статуса и приоритета. */
export function IncidentsPage() {
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const debouncedQuery = useDebouncedValue(filters.q, 250);
  const navigate = useNavigate();

  const loadDashboard = useCallback(() => api.dashboard.get(), []);
  const dashboardState = useApiData<Dashboard>(loadDashboard, "Не удалось загрузить показатели.");

  // Пустые значения не отправляем: backend считает пустую строку отсутствием фильтра,
  // но чистый URL проще читать в логах и тестах.
  const loadIncidents = useCallback(
    () =>
      api.incidents.list({
        q: isBlank(debouncedQuery) ? undefined : debouncedQuery.trim(),
        status: filters.status || undefined,
        priority: filters.priority || undefined,
      }),
    [debouncedQuery, filters.status, filters.priority],
  );
  const incidentsState = useApiData<Incident[]>(
    loadIncidents,
    "Не удалось загрузить реестр инцидентов.",
  );

  const incidents = useMemo(() => incidentsState.data ?? [], [incidentsState.data]);
  const counts = dashboardState.data?.counts;
  const kpiLoading = dashboardState.data === null && dashboardState.error === null;

  const hasActiveFilters = !isBlank(filters.q) || filters.status !== "" || filters.priority !== "";

  const statusOptions = useMemo(
    () => INCIDENT_STATUSES.map((status) => ({ value: status, label: STATUS_LABELS[status] })),
    [],
  );
  const priorityOptions = useMemo(
    () => INCIDENT_PRIORITIES.map((value) => ({ value, label: PRIORITY_LABELS[value] })),
    [],
  );

  const reloadAll = () => {
    dashboardState.reload();
    incidentsState.reload();
  };

  const isEmpty = incidents.length === 0;

  return (
    <section className="page">
      <PageHeader
        title="Реестр инцидентов"
        description="Все инциденты компании: новые сверху. Поиск по номеру или названию, фильтры по статусу и приоритету."
        actions={
          <Link className="button button--primary" to="/incidents/new">
            Новый инцидент
          </Link>
        }
      />

      <div className="kpi-grid">
        <KpiCard label="Всего открытых" value={counts?.open ?? null} isLoading={kpiLoading} />
        <KpiCard label="Новых" value={counts?.new ?? null} tone="info" isLoading={kpiLoading} />
        <KpiCard label="В работе" value={counts?.in_progress ?? null} isLoading={kpiLoading} />
        <KpiCard
          label="Критических"
          value={counts?.critical ?? null}
          tone="critical"
          isLoading={kpiLoading}
          hint="Critical и не закрыт"
        />
        <KpiCard
          label="Решено сегодня"
          value={counts?.resolved_today ?? null}
          tone="success"
          isLoading={kpiLoading}
        />
      </div>

      {dashboardState.error && (
        <p className="alert alert--error alert--compact" role="alert">
          Показатели недоступны: {dashboardState.error}
        </p>
      )}

      <div className="panel">
        <search className="toolbar">
          <label className="field field--grow">
            <span className="field__label">Поиск по ID или названию</span>
            <input
              type="search"
              value={filters.q}
              placeholder="Например, INC-001 или «почта»"
              maxLength={200}
              onChange={(event) => setFilters((current) => ({ ...current, q: event.target.value }))}
            />
          </label>

          <label className="field">
            <span className="field__label">Статус</span>
            <select
              value={filters.status}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  status: event.target.value as Filters["status"],
                }))
              }
            >
              <option value="">Все статусы</option>
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span className="field__label">Приоритет</span>
            <select
              value={filters.priority}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  priority: event.target.value as Filters["priority"],
                }))
              }
            >
              <option value="">Все приоритеты</option>
              {priorityOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          {hasActiveFilters && (
            <button
              type="button"
              className="button button--ghost"
              onClick={() => setFilters(EMPTY_FILTERS)}
            >
              Сбросить
            </button>
          )}
        </search>

        {incidentsState.error && (
          <ErrorMessage message={incidentsState.error} onRetry={reloadAll} />
        )}

        {!incidentsState.error && incidentsState.isLoading && isEmpty && (
          <LoadingMessage label="Загрузка инцидентов…" />
        )}

        {!incidentsState.error && !incidentsState.isLoading && isEmpty && (
          <StateMessage
            title={hasActiveFilters ? "Ничего не найдено" : "Инцидентов пока нет"}
            text={
              hasActiveFilters
                ? "Попробуйте изменить запрос или сбросить фильтры."
                : "Создайте первый инцидент, чтобы команда увидела проблему."
            }
            onRetry={hasActiveFilters ? () => setFilters(EMPTY_FILTERS) : undefined}
            retryLabel="Сбросить фильтры"
          />
        )}

        {!incidentsState.error && !isEmpty && (
          <div className="table-wrapper" aria-busy={incidentsState.isLoading}>
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">ID</th>
                  <th scope="col">Название</th>
                  <th scope="col">Приоритет</th>
                  <th scope="col">Статус</th>
                  <th scope="col">Ответственный</th>
                  <th scope="col">Создан</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map((incident) => (
                  <tr
                    key={incident.id}
                    className="table__row"
                    tabIndex={0}
                    onClick={() => navigate(`/incidents/${incident.id}`)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        navigate(`/incidents/${incident.id}`);
                      }
                    }}
                  >
                    <td className="table__id">{incident.id}</td>
                    <td className="table__title">
                      <Link
                        to={`/incidents/${incident.id}`}
                        onClick={(event) => event.stopPropagation()}
                      >
                        {incident.title}
                      </Link>
                    </td>
                    <td>
                      <PriorityBadge priority={incident.priority} />
                    </td>
                    <td>
                      <StatusBadge status={incident.status} />
                    </td>
                    <td>
                      <AssigneeText assignee={incident.assignee} />
                    </td>
                    <td className="table__muted">{formatDateTime(incident.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="table__caption">
              Найдено: {incidents.length}
              {incidentsState.isLoading && (
                <span className="table__refreshing"> · обновление…</span>
              )}
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
