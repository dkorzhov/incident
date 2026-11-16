"""Тесты домена инцидента: автомат статусов, неизменяемость Closed, история, валидация.

Тесты работают с сервисами напрямую (без публичных эндпоинтов инцидентов):
роуты — объём DMI-7. БД — тестовая, изменения откатываются фикстурой
``db_session`` (вложенные savepoints), поэтому сиды не нужно чистить вручную.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.dto import (
    UNSET,
    CommentCreate,
    IncidentCreate,
    IncidentUpdate,
    StatusChange,
)
from app.domain.errors import ConflictError, NotFoundError, ValidationError
from app.models.comment import Comment
from app.models.history import HistoryEvent, HistoryEventType
from app.models.incident import Incident, IncidentCategory, IncidentPriority, IncidentStatus
from app.models.user import User, UserRole
from app.services import incidents as incidents_service


@pytest.fixture
def actor(db_session: Session) -> User:
    """Текущий пользователь — автор изменений."""
    user = User(name=f"Актор-{id(db_session)}", role=UserRole.engineer)
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def assignee(db_session: Session) -> User:
    user = User(name=f"Исполнитель-{id(db_session)}", role=UserRole.engineer)
    db_session.add(user)
    db_session.flush()
    return user


def make_incident(
    db_session: Session,
    actor: User,
    *,
    title: str = "Не работает почта",
    priority: str = "High",
    assignee_id: int | None = None,
) -> Incident:
    return incidents_service.create_incident(
        db_session,
        IncidentCreate(
            title=title,
            description="Письма не приходят",
            category="Mail",
            priority=priority,
            assignee_id=assignee_id,
        ),
        actor=actor,
    )


def statuses(incident: Incident) -> list[HistoryEventType]:
    return [event.type for event in incident.history]


def event_of_type(incident: Incident, event_type: HistoryEventType) -> HistoryEvent:
    events = [event for event in incident.history if event.type is event_type]
    assert len(events) == 1, f"ожидалось одно событие {event_type}, получено {len(events)}"
    return events[0]


# --- создание и нумерация -------------------------------------------------


def test_create_incident_generates_sequential_number(db_session: Session, actor: User) -> None:
    first = make_incident(db_session, actor, title="Первая проблема сети")
    second = make_incident(db_session, actor, title="Вторая проблема сети")

    assert first.id.startswith("INC-")
    assert first.id != second.id
    assert int(first.id.removeprefix("INC-")) + 1 == int(second.id.removeprefix("INC-"))
    assert first.status is IncidentStatus.New
    assert first.resolution is None


def test_create_incident_records_created_history(db_session: Session, actor: User) -> None:
    incident = make_incident(db_session, actor)

    created = event_of_type(incident, HistoryEventType.created)
    assert created.actor_id == actor.id
    assert created.payload["title"] == {"from": None, "to": incident.title}
    assert created.payload["category"] == {"from": None, "to": "Mail"}
    assert created.payload["priority"] == {"from": None, "to": "High"}
    assert created.payload["status"] == {"from": None, "to": "New"}


def test_create_incident_with_assignee_records_assigned_history(
    db_session: Session, actor: User, assignee: User
) -> None:
    incident = make_incident(db_session, actor, assignee_id=assignee.id)

    assert incident.assignee_id == assignee.id
    assigned = event_of_type(incident, HistoryEventType.assigned)
    assert assigned.payload["assignee_id"] == {"from": None, "to": assignee.id}
    assert assigned.payload["assignee"] == {"from": None, "to": assignee.name}


# --- автомат статусов (TASK.md §2) ---------------------------------------


def test_status_happy_path_new_to_closed(db_session: Session, actor: User) -> None:
    """Успешный путь: New → In Progress → Resolved → Closed."""
    incident = make_incident(db_session, actor)

    incident = incidents_service.change_status(
        db_session, incident.id, StatusChange(status="In Progress"), actor=actor
    )
    assert incident.status is IncidentStatus.InProgress

    incident = incidents_service.change_status(
        db_session,
        incident.id,
        StatusChange(status="Resolved", resolution="Перезапущен почтовый шлюз"),
        actor=actor,
    )
    assert incident.status is IncidentStatus.Resolved
    assert incident.resolution == "Перезапущен почтовый шлюз"

    incident = incidents_service.change_status(
        db_session, incident.id, StatusChange(status="Closed"), actor=actor
    )
    assert incident.status is IncidentStatus.Closed

    assert statuses(incident) == [
        HistoryEventType.created,
        HistoryEventType.status_changed,
        HistoryEventType.resolved,
        HistoryEventType.status_changed,
    ]


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("New", "Closed"),
        ("New", "Resolved"),
        ("In Progress", "Closed"),
        ("In Progress", "New"),
        ("Resolved", "In Progress"),
        ("Resolved", "New"),
    ],
)
def test_invalid_transitions_raise_conflict(
    db_session: Session, actor: User, current: str, target: str
) -> None:
    """Иные переходы, включая закрытие из New/In Progress, — 409."""
    incident = make_incident(db_session, actor)
    incident = _drive_to(db_session, incident, actor, current)

    with pytest.raises(ConflictError):
        incidents_service.change_status(
            db_session, incident.id, StatusChange(status=target), actor=actor
        )

    db_session.rollback()
    assert incidents_service.get_incident(db_session, incident.id).status.value == current


def test_resolved_without_resolution_is_rejected(db_session: Session, actor: User) -> None:
    """Переход в Resolved без resolution — ошибка валидации (400)."""
    incident = make_incident(db_session, actor)
    incident = incidents_service.change_status(
        db_session, incident.id, StatusChange(status="In Progress"), actor=actor
    )

    with pytest.raises(ValidationError) as exc_info:
        incidents_service.change_status(
            db_session, incident.id, StatusChange(status="Resolved"), actor=actor
        )

    assert [error["field"] for error in exc_info.value.errors] == ["resolution"]
    db_session.rollback()
    stored = incidents_service.get_incident(db_session, incident.id)
    assert stored.status is IncidentStatus.InProgress


@pytest.mark.parametrize("resolution", ["", "   ", "\n\t "])
def test_resolved_with_blank_resolution_is_rejected(
    db_session: Session, actor: User, resolution: str
) -> None:
    incident = make_incident(db_session, actor)
    incident = incidents_service.change_status(
        db_session, incident.id, StatusChange(status="In Progress"), actor=actor
    )

    with pytest.raises(ValidationError):
        incidents_service.change_status(
            db_session,
            incident.id,
            StatusChange(status="Resolved", resolution=resolution),
            actor=actor,
        )


def test_same_status_change_is_conflict(db_session: Session, actor: User) -> None:
    incident = make_incident(db_session, actor)

    with pytest.raises(ConflictError):
        incidents_service.change_status(
            db_session, incident.id, StatusChange(status="New"), actor=actor
        )


def test_unknown_incident_status_raises_not_found(db_session: Session, actor: User) -> None:
    with pytest.raises(NotFoundError):
        incidents_service.change_status(
            db_session, "INC-999999", StatusChange(status="In Progress"), actor=actor
        )


def _drive_to(db_session: Session, incident: Incident, actor: User, status: str) -> Incident:
    """Привести инцидент к статусу по легальному маршруту."""
    path = {
        "New": [],
        "In Progress": ["In Progress"],
        "Resolved": ["In Progress", "Resolved"],
        "Closed": ["In Progress", "Resolved", "Closed"],
    }[status]
    for target in path:
        incident = incidents_service.change_status(
            db_session,
            incident.id,
            StatusChange(status=target, resolution="Решение" if target == "Resolved" else UNSET),
            actor=actor,
        )
    return incident


# --- неизменяемость Closed ------------------------------------------------


def test_closed_incident_rejects_patch(db_session: Session, actor: User) -> None:
    incident = make_incident(db_session, actor)
    _drive_to(db_session, incident, actor, "Closed")

    with pytest.raises(ConflictError):
        incidents_service.update_incident(
            db_session, incident.id, IncidentUpdate(title="Новое название"), actor=actor
        )


def test_closed_incident_rejects_status_change(db_session: Session, actor: User) -> None:
    incident = make_incident(db_session, actor)
    _drive_to(db_session, incident, actor, "Closed")

    for target in ("New", "In Progress", "Resolved", "Closed"):
        with pytest.raises(ConflictError):
            incidents_service.change_status(
                db_session, incident.id, StatusChange(status=target), actor=actor
            )


def test_closed_incident_rejects_comments(db_session: Session, actor: User) -> None:
    incident = make_incident(db_session, actor)
    _drive_to(db_session, incident, actor, "Closed")

    with pytest.raises(ConflictError):
        incidents_service.add_comment(
            db_session, incident.id, CommentCreate(text="Ещё вопрос"), actor=actor
        )

    assert db_session.scalar(select(func.count()).select_from(Comment)) == 0
    # и в истории нет события о комментарии
    assert HistoryEventType.commented not in statuses(
        incidents_service.get_incident(db_session, incident.id)
    )


# --- PATCH и история изменений -------------------------------------------


def test_update_title_and_description_records_fields_updated(
    db_session: Session, actor: User
) -> None:
    incident = make_incident(db_session, actor)

    incident = incidents_service.update_incident(
        db_session,
        incident.id,
        IncidentUpdate(title="Не работает корпоративная почта", description="Новое описание"),
        actor=actor,
    )

    assert incident.title == "Не работает корпоративная почта"
    updated = event_of_type(incident, HistoryEventType.fields_updated)
    assert updated.payload["title"] == {
        "from": "Не работает почта",
        "to": "Не работает корпоративная почта",
    }
    assert updated.payload["description"] == {"from": "Письма не приходят", "to": "Новое описание"}


def test_update_priority_records_priority_changed(db_session: Session, actor: User) -> None:
    incident = make_incident(db_session, actor, priority="Low")

    incidents_service.update_incident(
        db_session, incident.id, IncidentUpdate(priority="Critical"), actor=actor
    )

    incident = incidents_service.get_incident(db_session, incident.id)
    assert incident.priority is IncidentPriority.Critical
    event = event_of_type(incident, HistoryEventType.priority_changed)
    assert event.payload == {"priority": {"from": "Low", "to": "Critical"}}


def test_update_assignee_records_assigned_with_names(
    db_session: Session, actor: User, assignee: User
) -> None:
    incident = make_incident(db_session, actor)

    incidents_service.update_incident(
        db_session, incident.id, IncidentUpdate(assignee_id=assignee.id), actor=actor
    )

    incident = incidents_service.get_incident(db_session, incident.id)
    event = event_of_type(incident, HistoryEventType.assigned)
    assert event.payload["assignee_id"] == {"from": None, "to": assignee.id}
    assert event.payload["assignee"]["to"] == assignee.name

    # снятие ответственного — тоже событие, «стало» = null
    incidents_service.update_incident(
        db_session, incident.id, IncidentUpdate(assignee_id=None), actor=actor
    )
    incident = incidents_service.get_incident(db_session, incident.id)
    unassign = [e for e in incident.history if e.type is HistoryEventType.assigned][-1]
    assert unassign.payload["assignee_id"] == {"from": assignee.id, "to": None}


def test_update_assignee_only_writes_no_fields_updated(
    db_session: Session, actor: User, assignee: User
) -> None:
    """`assigned` и `priority_changed` не дублируются в `fields_updated`."""
    incident = make_incident(db_session, actor)

    incidents_service.update_incident(
        db_session,
        incident.id,
        IncidentUpdate(assignee_id=assignee.id, priority="Critical"),
        actor=actor,
    )

    incident = incidents_service.get_incident(db_session, incident.id)
    assert statuses(incident) == [
        HistoryEventType.created,
        HistoryEventType.priority_changed,
        HistoryEventType.assigned,
    ]


def test_update_without_changes_writes_no_history(db_session: Session, actor: User) -> None:
    incident = make_incident(db_session, actor)
    before = db_session.scalar(select(func.count()).select_from(HistoryEvent))

    incidents_service.update_incident(
        db_session,
        incident.id,
        IncidentUpdate(title=incident.title, description=incident.description),
        actor=actor,
    )

    assert db_session.scalar(select(func.count()).select_from(HistoryEvent)) == before


def test_unchanged_optional_field_keeps_value(db_session: Session, actor: User) -> None:
    incident = make_incident(db_session, actor)

    incidents_service.update_incident(
        db_session, incident.id, IncidentUpdate(priority="Medium"), actor=actor
    )

    incident = incidents_service.get_incident(db_session, incident.id)
    assert incident.title == "Не работает почта"
    assert incident.description == "Письма не приходят"
    assert incident.category is IncidentCategory.Mail


def test_update_unknown_incident_raises_not_found(db_session: Session, actor: User) -> None:
    with pytest.raises(NotFoundError):
        incidents_service.update_incident(
            db_session, "INC-987654", IncidentUpdate(title="Какой-то заголовок"), actor=actor
        )


# --- комментарии ----------------------------------------------------------


def test_add_comment_records_history(db_session: Session, actor: User) -> None:
    incident = make_incident(db_session, actor)

    comment = incidents_service.add_comment(
        db_session, incident.id, CommentCreate(text="  Уточните, пожалуйста, время  "), actor=actor
    )

    assert comment.text == "Уточните, пожалуйста, время"
    assert comment.author_id == actor.id
    incident = incidents_service.get_incident(db_session, incident.id)
    event = event_of_type(incident, HistoryEventType.commented)
    assert event.payload["comment_id"] == {"from": None, "to": comment.id}
    assert event.payload["text"]["to"] == "Уточните, пожалуйста, время"


@pytest.mark.parametrize("text", ["", "   ", "\n"])
def test_add_comment_rejects_blank_text(db_session: Session, actor: User, text: str) -> None:
    incident = make_incident(db_session, actor)

    with pytest.raises(ValidationError) as exc_info:
        incidents_service.add_comment(
            db_session, incident.id, CommentCreate(text=text), actor=actor
        )

    assert exc_info.value.errors[0]["field"] == "text"


def test_add_comment_too_long_is_rejected(db_session: Session, actor: User) -> None:
    incident = make_incident(db_session, actor)

    with pytest.raises(ValidationError) as exc_info:
        incidents_service.add_comment(
            db_session, incident.id, CommentCreate(text="x" * 2001), actor=actor
        )

    assert exc_info.value.errors[0]["field"] == "text"


# --- валидация полей ------------------------------------------------------


@pytest.mark.parametrize(
    ("title", "reason_field"),
    [
        ("", "title"),
        ("    ", "title"),
        ("1234", "title"),  # меньше 5 символов
        ("x" * 121, "title"),
    ],
)
def test_create_incident_rejects_invalid_title(
    db_session: Session, actor: User, title: str, reason_field: str
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        incidents_service.create_incident(
            db_session,
            IncidentCreate(title=title, category="Mail", priority="High"),
            actor=actor,
        )

    assert exc_info.value.errors[0]["field"] == reason_field


def test_create_incident_accepts_boundary_title_lengths(
    db_session: Session, actor: User
) -> None:
    exact_min = make_incident(db_session, actor, title="x" * 5)
    exact_max = make_incident(db_session, actor, title="y" * 120)

    assert len(exact_min.title) == 5
    assert len(exact_max.title) == 120


def test_create_incident_rejects_unknown_category(db_session: Session, actor: User) -> None:
    with pytest.raises(ValidationError) as exc_info:
        incidents_service.create_incident(
            db_session,
            IncidentCreate(title="Проблема с VPN", category="Hardware", priority="High"),
            actor=actor,
        )

    assert exc_info.value.errors[0]["field"] == "category"


def test_create_incident_rejects_unknown_priority(db_session: Session, actor: User) -> None:
    with pytest.raises(ValidationError) as exc_info:
        incidents_service.create_incident(
            db_session,
            IncidentCreate(title="Проблема с VPN", category="Network", priority="Urgent"),
            actor=actor,
        )

    assert exc_info.value.errors[0]["field"] == "priority"


def test_create_incident_reports_all_invalid_fields_at_once(
    db_session: Session, actor: User
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        incidents_service.create_incident(
            db_session,
            IncidentCreate(title="abc", category="Nope", priority="Nope"),
            actor=actor,
        )

    assert {error["field"] for error in exc_info.value.errors} == {
        "title",
        "category",
        "priority",
    }


def test_create_incident_rejects_too_long_description(
    db_session: Session, actor: User
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        incidents_service.create_incident(
            db_session,
            IncidentCreate(
                title="Проблема с VPN",
                description="d" * 2001,
                category="Network",
                priority="Medium",
            ),
            actor=actor,
        )

    assert exc_info.value.errors[0]["field"] == "description"


def test_create_incident_rejects_unknown_assignee(db_session: Session, actor: User) -> None:
    with pytest.raises(ValidationError) as exc_info:
        incidents_service.create_incident(
            db_session,
            IncidentCreate(
                title="Проблема с VPN", category="Network", priority="Medium", assignee_id=987654
            ),
            actor=actor,
        )

    assert exc_info.value.errors[0]["field"] == "assignee_id"


def test_update_rejects_empty_payload_field(db_session: Session, actor: User) -> None:
    incident = make_incident(db_session, actor)

    with pytest.raises(ValidationError):
        incidents_service.update_incident(
            db_session, incident.id, IncidentUpdate(title="   "), actor=actor
        )


# --- реестр ---------------------------------------------------------------


def test_list_incidents_sorts_newest_first(db_session: Session, actor: User) -> None:
    first = make_incident(db_session, actor, title="Первый инцидент реестра")
    second = make_incident(db_session, actor, title="Второй инцидент реестра")

    listed = incidents_service.list_incidents(db_session)

    ids = [incident.id for incident in listed]
    assert ids.index(second.id) < ids.index(first.id)


def test_list_incidents_filters_by_status_and_priority(
    db_session: Session, actor: User
) -> None:
    new_critical = make_incident(
        db_session, actor, title="Критичный новый инцидент", priority="Critical"
    )
    make_incident(db_session, actor, title="Некритичный новый инцидент", priority="Low")

    critical = incidents_service.list_incidents(
        db_session, status=IncidentStatus.New, priority=IncidentPriority.Critical
    )

    assert [incident.id for incident in critical] == [new_critical.id]


def test_list_incidents_searches_by_id_and_title(db_session: Session, actor: User) -> None:
    target = make_incident(db_session, actor, title="Не открывается портал")
    make_incident(db_session, actor, title="Не работает почта")

    by_title = incidents_service.list_incidents(db_session, query="портал")
    by_id = incidents_service.list_incidents(db_session, query=target.id.lower())

    assert [incident.id for incident in by_title] == [target.id]
    assert [incident.id for incident in by_id] == [target.id]


# --- история как журнал ---------------------------------------------------


def test_history_is_chronological_and_actor_is_recorded(
    db_session: Session, actor: User, assignee: User
) -> None:
    incident = make_incident(db_session, actor)
    incidents_service.update_incident(
        db_session, incident.id, IncidentUpdate(assignee_id=assignee.id), actor=assignee
    )
    incidents_service.change_status(
        db_session, incident.id, StatusChange(status="In Progress"), actor=assignee
    )

    events = incidents_service.get_incident_history(db_session, incident.id)

    assert [event.type.value for event in events] == ["created", "assigned", "status_changed"]
    assert [event.actor_id for event in events] == [actor.id, assignee.id, assignee.id]
    assert [event.created_at for event in events] == sorted(e.created_at for e in events)


def test_history_starting_status_payload(db_session: Session, actor: User) -> None:
    incident = make_incident(db_session, actor)
    incidents_service.change_status(
        db_session, incident.id, StatusChange(status="In Progress"), actor=actor
    )

    incident = incidents_service.get_incident(db_session, incident.id)
    event = event_of_type(incident, HistoryEventType.status_changed)
    assert event.payload == {"status": {"from": "New", "to": "In Progress"}}


def test_resolved_event_carries_resolution(db_session: Session, actor: User) -> None:
    incident = make_incident(db_session, actor)
    incident = incidents_service.change_status(
        db_session, incident.id, StatusChange(status="In Progress"), actor=actor
    )
    incidents_service.change_status(
        db_session,
        incident.id,
        StatusChange(status="Resolved", resolution="Перезапущен шлюз"),
        actor=actor,
    )

    incident = incidents_service.get_incident(db_session, incident.id)
    event = event_of_type(incident, HistoryEventType.resolved)
    assert event.payload == {
        "status": {"from": "In Progress", "to": "Resolved"},
        "resolution": {"from": None, "to": "Перезапущен шлюз"},
    }


def test_history_of_unknown_incident_raises_not_found(
    db_session: Session, actor: User
) -> None:
    with pytest.raises(NotFoundError):
        incidents_service.get_incident_history(db_session, "INC-111222")


# --- таблица переходов как контракт для UI (DMI-7) -----------------------


def test_transition_table_matches_task_spec() -> None:
    from app.domain.status import ALLOWED_TRANSITIONS, action_for

    assert ALLOWED_TRANSITIONS[IncidentStatus.New] == {IncidentStatus.InProgress}
    assert ALLOWED_TRANSITIONS[IncidentStatus.InProgress] == {IncidentStatus.Resolved}
    assert ALLOWED_TRANSITIONS[IncidentStatus.Resolved] == {IncidentStatus.Closed}
    assert ALLOWED_TRANSITIONS[IncidentStatus.Closed] == set()

    assert action_for(IncidentStatus.New, IncidentStatus.InProgress) == "Взять в работу"
    assert action_for(IncidentStatus.InProgress, IncidentStatus.Resolved) == "Отметить решённым"
    assert action_for(IncidentStatus.Resolved, IncidentStatus.Closed) == "Закрыть"
    assert action_for(IncidentStatus.New, IncidentStatus.Closed) is None


def test_conflict_message_names_current_and_target_status(
    db_session: Session, actor: User
) -> None:
    incident = make_incident(db_session, actor)

    with pytest.raises(ConflictError) as exc_info:
        incidents_service.change_status(
            db_session, incident.id, StatusChange(status="Closed"), actor=actor
        )

    message = str(exc_info.value)
    assert "New" in message
    assert "Closed" in message
    assert "In Progress" in message  # подсказка о допустимом переходе