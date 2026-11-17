"""Demo-seed (TASK.md §6, DMI-10): состав набора и идемпотентность.

Тесты вызывают ``seed_demo_data`` напрямую с транзакционной сессией из
``conftest``: ``Session.commit()`` внутри сида закрывает savepoint, а откат
внешней транзакции в фикстуре всё равно убирает демо-данные из тестовой БД.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.demo_seed import DemoSeedState
from app.models.history import HistoryEvent, HistoryEventType
from app.models.incident import Incident, IncidentPriority, IncidentStatus
from app.services import seed
from app.services.dashboard import build_dashboard


def _count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Incident)) or 0


def test_seed_creates_incidents_in_every_status(db_session: Session) -> None:
    created = seed.seed_demo_data(db_session)

    assert created == len(seed.DEMO_INCIDENTS)
    statuses = set(db_session.scalars(select(Incident.status)).all())
    assert statuses == set(IncidentStatus), "набор должен покрывать все статусы автомата"


def test_seed_has_critical_incident(db_session: Session) -> None:
    seed.seed_demo_data(db_session)

    critical = db_session.scalars(
        select(Incident).where(Incident.priority == IncidentPriority.Critical)
    ).all()
    assert critical, "для KPI «Критических» нужен хотя бы один Critical"


def test_seed_resolved_today_is_counted_by_dashboard(db_session: Session) -> None:
    """Resolved сегодня = resolution + событие истории с переходом в Resolved."""
    seed.seed_demo_data(db_session)

    resolved = db_session.scalars(
        select(Incident).where(Incident.status == IncidentStatus.Resolved)
    ).all()
    assert resolved, "нужен хотя бы один Resolved"
    for incident in resolved:
        assert incident.resolution, "у Resolved обязателен resolution"

        day_start = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)
        transition = db_session.scalars(
            select(HistoryEvent).where(
                HistoryEvent.incident_id == incident.id,
                HistoryEvent.type.in_(
                    (HistoryEventType.resolved, HistoryEventType.status_changed)
                ),
                HistoryEvent.payload["status"]["to"].astext == IncidentStatus.Resolved.value,
                HistoryEvent.created_at >= day_start,
                HistoryEvent.created_at < day_start + timedelta(days=1),
            )
        ).all()
        assert transition, f"у {incident.id} нет события перехода в Resolved за сегодня"

    counts = build_dashboard(db_session).counts
    # Точное равенство, а не «>=»: недосчёт дашборда должен падать. Ожидаемое
    # число берём из состава набора, независимо от реализации дашборда:
    # Closed-инцидент тоже прошёл через Resolved сегодня и считается.
    expected = sum(
        1
        for spec in seed.DEMO_INCIDENTS
        if spec.status in {IncidentStatus.Resolved, IncidentStatus.Closed}
    )
    assert counts.resolved_today == expected


def test_seed_closed_incident_keeps_history_order(db_session: Session) -> None:
    """Жизненный цикл демо-инцидента проходит по автомату §2 шаг за шагом."""
    seed.seed_demo_data(db_session)

    closed = db_session.scalars(
        select(Incident).where(Incident.status == IncidentStatus.Closed)
    ).first()
    assert closed is not None
    assert closed.resolution

    transitions = [
        event.payload["status"]["to"]
        for event in db_session.scalars(
            select(HistoryEvent)
            .where(
                HistoryEvent.incident_id == closed.id,
                HistoryEvent.type.in_(
                    (HistoryEventType.status_changed, HistoryEventType.resolved)
                ),
            )
            .order_by(HistoryEvent.created_at, HistoryEvent.id)
        ).all()
    ]
    assert transitions == ["In Progress", "Resolved", "Closed"]


def test_seed_is_idempotent(db_session: Session) -> None:
    """Повторный старт не задваивает данные: маркер уже занят."""
    seed.seed_demo_data(db_session)
    before = _count(db_session)

    created_again = seed.seed_demo_data(db_session)

    assert created_again == 0
    assert _count(db_session) == before


def test_seed_marker_is_written_once(db_session: Session) -> None:
    seed.seed_demo_data(db_session)
    seed.seed_demo_data(db_session)

    markers = db_session.scalars(
        select(DemoSeedState).where(DemoSeedState.key == seed.DEMO_SEED_KEY)
    ).all()
    assert len(markers) == 1


def test_seed_is_skipped_under_pytest() -> None:
    """``lifespan`` поднимается TestClient'ом — seed не должен писать в тестовую БД."""
    assert seed.running_under_pytest() is True
    assert seed.seed_demo_on_startup() == 0


def test_demo_set_respects_field_limits() -> None:
    """Демо-данные проходят те же ограничения, что и инциденты из UI."""
    from app.models.incident import DESCRIPTION_MAX_LENGTH, RESOLUTION_MAX_LENGTH, TITLE_MAX_LENGTH

    for spec in seed.DEMO_INCIDENTS:
        assert seed.DEMO_TITLE_PREFIX in spec.title
        assert 5 <= len(spec.title) <= TITLE_MAX_LENGTH
        assert len(spec.description) <= DESCRIPTION_MAX_LENGTH
        if spec.status in {IncidentStatus.Resolved, IncidentStatus.Closed}:
            assert spec.resolution, f"{spec.title!r}: Resolved/Closed требует resolution"
            assert len(spec.resolution) <= RESOLUTION_MAX_LENGTH