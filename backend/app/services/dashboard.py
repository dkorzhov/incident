"""Агрегаты для дашборда (TASK.md §3): KPI, разрез по приоритетам, активность.

Правила подсчёта (важны для сходимости с БД):

* ``open``   — не ``Closed``: всё, что ещё в работе службы поддержки;
* ``new`` / ``in_progress`` — инциденты в соответствующем статусе;
* ``critical`` — ``Critical`` **и** не ``Closed``, потому что KPI-строка
  на дашборде описывает открытые инциденты (итог KPI — «Всего открытых»);
* ``resolved_today`` — по дате события перехода в ``Resolved`` в истории
  (``status_changed``/``resolved`` с ``to = Resolved``), а не по ``updated_at``:
  правка закрытого или иного поля не должна «омолаживать» решение;
* ``by_priority`` — все инциденты, включая закрытые: это разрез реестра,
  сумма ключей равна общему числу инцидентов.

Границы «сегодня» считаются в UTC — в этом часовом поясе хранится время в БД.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.history import HistoryEvent, HistoryEventType
from app.models.incident import Incident, IncidentPriority, IncidentStatus

#: Сколько последних событий отдаёт дашборд.
RECENT_ACTIVITY_LIMIT = 10

#: Типы событий, которыми фиксируется переход в ``Resolved``.
_RESOLUTION_EVENTS = (HistoryEventType.status_changed, HistoryEventType.resolved)


@dataclass(frozen=True, slots=True)
class DashboardCounts:
    """KPI-показатели дашборда."""

    open: int
    new: int
    in_progress: int
    critical: int
    resolved_today: int


@dataclass(frozen=True, slots=True)
class DashboardData:
    """Всё, что отдаёт ``GET /api/dashboard``."""

    counts: DashboardCounts
    by_priority: dict[IncidentPriority, int]
    recent_activity: Sequence[HistoryEvent]


def build_dashboard(db: Session, *, now: datetime | None = None) -> DashboardData:
    """Собрать показатели дашборда одним проходом по БД (без Python-фильтрации)."""
    day_start, day_end = _utc_day_bounds(now or datetime.now(UTC))

    return DashboardData(
        counts=DashboardCounts(
            open=_count_incidents(db, Incident.status != IncidentStatus.Closed),
            new=_count_incidents(db, Incident.status == IncidentStatus.New),
            in_progress=_count_incidents(db, Incident.status == IncidentStatus.InProgress),
            critical=_count_incidents(
                db,
                Incident.priority == IncidentPriority.Critical,
                Incident.status != IncidentStatus.Closed,
            ),
            resolved_today=_count_resolved_between(db, day_start, day_end),
        ),
        by_priority=_count_by_priority(db),
        recent_activity=_recent_activity(db),
    )


def _count_incidents(db: Session, *conditions: object) -> int:
    """Количество инцидентов, удовлетворяющих условиям (0, если строк нет)."""
    stmt = select(func.count()).select_from(Incident).where(*conditions)
    return db.scalar(stmt) or 0


def _count_by_priority(db: Session) -> dict[IncidentPriority, int]:
    """Разрез реестра по приоритетам; приоритеты без инцидентов — с нулём."""
    rows = db.execute(
        select(Incident.priority, func.count()).group_by(Incident.priority)
    ).all()
    counted = dict(rows)
    return {priority: counted.get(priority, 0) for priority in IncidentPriority}


def _count_resolved_between(db: Session, start: datetime, end: datetime) -> int:
    """Сколько инцидентов переведено в ``Resolved`` в интервале ``[start, end)``.

    Считаются именно переходы из истории: ``DISTINCT incident_id`` защищает от
    двойного счёта, если у инцидента окажется несколько событий со ``to=Resolved``.
    """
    stmt = (
        select(func.count(distinct(HistoryEvent.incident_id)))
        .select_from(HistoryEvent)
        .where(
            HistoryEvent.type.in_(_RESOLUTION_EVENTS),
            HistoryEvent.payload["status"]["to"].astext == IncidentStatus.Resolved.value,
            HistoryEvent.created_at >= start,
            HistoryEvent.created_at < end,
        )
    )
    return db.scalar(stmt) or 0


def _recent_activity(db: Session) -> Sequence[HistoryEvent]:
    """Последние ``RECENT_ACTIVITY_LIMIT`` событий истории (свежие сверху)."""
    stmt = (
        select(HistoryEvent)
        .options(joinedload(HistoryEvent.actor), joinedload(HistoryEvent.incident))
        .order_by(HistoryEvent.created_at.desc(), HistoryEvent.id.desc())
        .limit(RECENT_ACTIVITY_LIMIT)
    )
    return db.scalars(stmt).unique().all()


def _utc_day_bounds(moment: datetime) -> tuple[datetime, datetime]:
    """Начало и конец суток UTC для момента ``moment`` (полуинтервал)."""
    start = datetime.combine(moment.astimezone(UTC).date(), time.min, tzinfo=UTC)
    return start, start + timedelta(days=1)


__all__ = [
    "RECENT_ACTIVITY_LIMIT",
    "DashboardCounts",
    "DashboardData",
    "build_dashboard",
]