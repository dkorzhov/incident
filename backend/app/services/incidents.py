"""Операции над инцидентами: создание, PATCH, переходы статусов, комментарии.

Сервисы принимают ``Session`` и обычные DTO, не зная про FastAPI. Ошибки —
доменные исключения (``app.domain.errors``): их переводит в HTTP API-слой.
Каждая успешная операция оставляет событие в истории и коммитит транзакцию.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Integer, Select, cast, func, select
from sqlalchemy.orm import Session, joinedload

from app.domain.dto import (
    CommentCreate,
    IncidentChanges,
    IncidentCreate,
    IncidentUpdate,
    StatusChange,
)
from app.domain.errors import ConflictError, NotFoundError, ValidationError
from app.domain.status import ensure_editable, ensure_transition_allowed
from app.domain.validation import (
    FieldErrors,
    Unset,
    clean_identifier,
    clean_text,
    parse_enum,
)
from app.models.comment import COMMENT_TEXT_MAX_LENGTH, Comment
from app.models.history import HistoryEvent
from app.models.incident import (
    DESCRIPTION_MAX_LENGTH,
    RESOLUTION_MAX_LENGTH,
    TITLE_MAX_LENGTH,
    Incident,
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
)
from app.models.user import User
from app.services import history


def _incident_query() -> Select[tuple[Incident]]:
    """Запрос инцидента с предзагруженным ответственным (для имён в истории)."""
    return select(Incident).options(joinedload(Incident.assignee))


def _number_order() -> Any:
    """Числовая часть номера для сортировки.

    Лексикографический порядок строк ломается после ``INC-999``
    (``INC-1000`` < ``INC-999``), поэтому tie-break идёт по числу.
    """
    return cast(func.substr(Incident.id, len("INC-") + 1), Integer)


def get_incident(db: Session, incident_id: str) -> Incident:
    """Инцидент по номеру ``INC-NNN``; 404, если его нет."""
    incident = db.scalars(_incident_query().where(Incident.id == incident_id)).first()
    if incident is None:
        raise NotFoundError(f"Инцидент {incident_id} не найден")
    return incident


def get_incident_for_update(db: Session, incident_id: str) -> Incident:
    """Инцидент под блокировкой строки — для операций, меняющих состояние.

    ``FOR UPDATE`` сериализует параллельные PATCH/переходы одного инцидента,
    чтобы автомат статусов нельзя было обойти гонкой двух запросов.
    """
    incident = db.scalars(
        select(Incident).where(Incident.id == incident_id).with_for_update()
    ).first()
    if incident is None:
        raise NotFoundError(f"Инцидент {incident_id} не найден")
    return incident


def _get_user(db: Session, user_id: int, *, field: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise ValidationError.for_field(field, f"пользователь {user_id} не найден")
    return user


def list_incidents(
    db: Session,
    *,
    query: str | None = None,
    status: IncidentStatus | None = None,
    priority: IncidentPriority | None = None,
) -> Sequence[Incident]:
    """Реестр: новые сверху, с поиском по номеру/названию и фильтрами."""
    stmt = _incident_query().order_by(
        Incident.created_at.desc(), _number_order().desc()
    )
    if status is not None:
        stmt = stmt.where(Incident.status == status)
    if priority is not None:
        stmt = stmt.where(Incident.priority == priority)
    if query and query.strip():
        needle = f"%{query.strip().lower()}%"
        stmt = stmt.where(Incident.id.ilike(needle) | Incident.title.ilike(needle))
    return db.scalars(stmt).unique().all()


def create_incident(db: Session, data: IncidentCreate, *, actor: User) -> Incident:
    """Создать инцидент: статус New, номер INC-NNN от последовательности, история."""
    errors = FieldErrors()
    title = errors.collect(
        clean_text, data.title, field="title", min_length=5, max_length=TITLE_MAX_LENGTH
    )
    description = errors.collect(
        clean_text,
        data.description,
        field="description",
        max_length=DESCRIPTION_MAX_LENGTH,
        required=False,
    )
    category = errors.collect(parse_enum, data.category, IncidentCategory, field="category")
    priority = errors.collect(parse_enum, data.priority, IncidentPriority, field="priority")
    assignee_id = errors.collect(clean_identifier, data.assignee_id, field="assignee_id")
    errors.raise_if_any()

    assignee = _get_user(db, assignee_id, field="assignee_id") if assignee_id else None
    assert title is not None and category is not None and priority is not None

    incident = Incident(
        title=title,
        description=description or "",
        category=category,
        priority=priority,
        status=IncidentStatus.New,
        assignee_id=assignee_id,
        assignee=assignee,
    )
    db.add(incident)
    db.flush()

    history.record_created(db, incident=incident, actor=actor)
    if assignee is not None:
        history.record_assigned(
            db,
            incident=incident,
            actor=actor,
            before_id=None,
            after_id=assignee.id,
            before_name=None,
            after_name=assignee.name,
        )
    db.commit()
    db.refresh(incident)
    return incident


def update_incident(
    db: Session, incident_id: str, data: IncidentUpdate, *, actor: User
) -> Incident:
    """PATCH: title/description/category/priority/assignee_id.

    Для закрытого инцидента — 409. Приоритет и ответственный попадают в историю
    отдельными событиями ``priority_changed``/``assigned``, прочие поля —
    одним событием ``fields_updated``.
    """
    incident = get_incident_for_update(db, incident_id)
    ensure_editable(incident)

    errors = FieldErrors()
    new_values: dict[str, Any] = {}

    if not isinstance(data.title, Unset):
        new_values["title"] = errors.collect(
            clean_text, data.title, field="title", min_length=5, max_length=TITLE_MAX_LENGTH
        )
    if not isinstance(data.description, Unset):
        new_values["description"] = errors.collect(
            clean_text,
            data.description,
            field="description",
            max_length=DESCRIPTION_MAX_LENGTH,
            required=False,
        )
    if not isinstance(data.category, Unset):
        new_values["category"] = errors.collect(
            parse_enum, data.category, IncidentCategory, field="category"
        )
    if not isinstance(data.priority, Unset):
        new_values["priority"] = errors.collect(
            parse_enum, data.priority, IncidentPriority, field="priority"
        )
    if not isinstance(data.assignee_id, Unset):
        new_values["assignee_id"] = errors.collect(
            clean_identifier, data.assignee_id, field="assignee_id"
        )
    errors.raise_if_any()

    new_assignee_id: int | None = new_values.get("assignee_id")
    new_assignee = (
        _get_user(db, new_assignee_id, field="assignee_id") if new_assignee_id else None
    )

    previous_assignee = incident.assignee
    previous_assignee_id = incident.assignee_id

    changes = IncidentChanges()
    for field_name, value in new_values.items():
        changes.record(field_name, getattr(incident, field_name), value)
        setattr(incident, field_name, value)

    if not changes:
        db.commit()
        db.refresh(incident)
        return incident

    if changes.priority_changed:
        before, after = changes.fields["priority"]
        history.record_priority_changed(
            db, incident=incident, actor=actor, before=before.value, after=after.value
        )
    if changes.assignee_changed:
        history.record_assigned(
            db,
            incident=incident,
            actor=actor,
            before_id=previous_assignee_id,
            after_id=new_assignee_id,
            before_name=previous_assignee.name if previous_assignee else None,
            after_name=new_assignee.name if new_assignee else None,
        )
    rest = changes.without("priority", "assignee_id")
    if rest:
        history.record_fields_updated(
            db,
            incident=incident,
            actor=actor,
            changes={
                name: (_serialize(before), _serialize(after))
                for name, (before, after) in rest.items()
            },
        )

    db.commit()
    db.refresh(incident)
    return incident


def _serialize(value: Any) -> Any:
    """Значение для JSONB-payload: enum → строка."""
    if isinstance(value, IncidentCategory | IncidentPriority | IncidentStatus):
        return value.value
    return value


def change_status(db: Session, incident_id: str, data: StatusChange, *, actor: User) -> Incident:
    """Переход по автомату §2 с записью истории.

    409 — перехода нет (в т.ч. любой переход из Closed);
    400 — переход в Resolved без непустого resolution.
    """
    incident = get_incident_for_update(db, incident_id)
    target = parse_enum(data.status, IncidentStatus, field="status")

    ensure_editable(incident, action="менять статус")
    if target == incident.status:
        raise ConflictError(f"Инцидент {incident.id} уже в статусе {incident.status.value}")
    ensure_transition_allowed(incident.status, target)

    resolution = _resolution_for(target, data.resolution)
    if target is IncidentStatus.Resolved and not resolution:
        raise ValidationError.for_field("resolution", "обязательно при переводе в Resolved")

    before = incident.status
    incident.status = target
    if target is IncidentStatus.Resolved:
        incident.resolution = resolution
        history.record_resolved(
            db, incident=incident, actor=actor, before=before, resolution=resolution or ""
        )
    else:
        history.record_status_changed(
            db, incident=incident, actor=actor, before=before, after=target
        )

    db.commit()
    db.refresh(incident)
    return incident


def _resolution_for(target: IncidentStatus, value: Any) -> str | None:
    """Проверить resolution; учитывается только при переходе в Resolved."""
    if isinstance(value, Unset) or value is None:
        return None
    if target is not IncidentStatus.Resolved:
        # При прочих переходах поле не применяется и не должно ломать запрос.
        return None
    return clean_text(value, field="resolution", max_length=RESOLUTION_MAX_LENGTH)


def get_incident_comments(db: Session, incident_id: str) -> Sequence[Comment]:
    """Комментарии инцидента в хронологическом порядке (404, если инцидента нет)."""
    incident = get_incident(db, incident_id)
    return db.scalars(
        select(Comment)
        .options(joinedload(Comment.author))
        .where(Comment.incident_id == incident.id)
        .order_by(Comment.created_at, Comment.id)
    ).unique().all()


def get_incident_history(db: Session, incident_id: str) -> Sequence[HistoryEvent]:
    """История инцидента в хронологическом порядке."""
    incident = get_incident(db, incident_id)
    return db.scalars(
        select(HistoryEvent)
        .options(joinedload(HistoryEvent.actor))
        .where(HistoryEvent.incident_id == incident.id)
        .order_by(HistoryEvent.created_at, HistoryEvent.id)
    ).unique().all()


def add_comment(db: Session, incident_id: str, data: CommentCreate, *, actor: User) -> Comment:
    """Добавить комментарий; для Closed — 409 (TASK.md §2)."""
    incident = get_incident_for_update(db, incident_id)
    ensure_editable(incident, action="добавлять комментарии")

    text = clean_text(data.text, field="text", min_length=1, max_length=COMMENT_TEXT_MAX_LENGTH)
    comment = Comment(incident_id=incident.id, author_id=actor.id, text=text)
    db.add(comment)
    db.flush()

    history.record_commented(
        db, incident=incident, actor=actor, comment_id=comment.id, text=comment.text
    )
    db.commit()
    db.refresh(comment)
    return comment


__all__ = [
    "add_comment",
    "change_status",
    "create_incident",
    "get_incident",
    "get_incident_comments",
    "get_incident_for_update",
    "get_incident_history",
    "list_incidents",
    "update_incident",
]