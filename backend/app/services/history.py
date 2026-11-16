"""Запись событий истории — единственная точка создания ``HistoryEvent``.

Вызывается сервисами в той же транзакции, что и изменение инцидента: либо
фиксируются оба факта, либо ни одного. ``payload`` строится здесь, поэтому
формат «было/стало» одинаков для всех событий (см. ``app.models.history``).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.history import ChangePayload, HistoryEvent, HistoryEventType
from app.models.incident import Incident, IncidentStatus
from app.models.user import User


def _change(before: Any, after: Any) -> dict[str, Any]:
    return {"from": before, "to": after}


def record_event(
    db: Session,
    *,
    incident: Incident,
    actor: User,
    event_type: HistoryEventType,
    payload: ChangePayload,
) -> HistoryEvent:
    """Записать событие в историю инцидента (в рамках текущей транзакции)."""
    event = HistoryEvent(
        incident_id=incident.id,
        actor_id=actor.id,
        type=event_type,
        payload=payload,
    )
    db.add(event)
    db.flush()
    return event


def record_created(db: Session, *, incident: Incident, actor: User) -> HistoryEvent:
    """Создание инцидента: все исходные значения как «стало»."""
    payload: ChangePayload = {
        "title": _change(None, incident.title),
        "description": _change(None, incident.description),
        "category": _change(None, incident.category.value),
        "priority": _change(None, incident.priority.value),
        "status": _change(None, incident.status.value),
        "assignee_id": _change(None, incident.assignee_id),
    }
    return record_event(
        db, incident=incident, actor=actor, event_type=HistoryEventType.created, payload=payload
    )


def record_assigned(
    db: Session,
    *,
    incident: Incident,
    actor: User,
    before_id: int | None,
    after_id: int | None,
    before_name: str | None,
    after_name: str | None,
) -> HistoryEvent:
    """Смена ответственного (отдельное событие ``assigned``)."""
    payload: ChangePayload = {
        "assignee_id": _change(before_id, after_id),
        "assignee": _change(before_name, after_name),
    }
    return record_event(
        db, incident=incident, actor=actor, event_type=HistoryEventType.assigned, payload=payload
    )


def record_status_changed(
    db: Session, *, incident: Incident, actor: User, before: IncidentStatus, after: IncidentStatus
) -> HistoryEvent:
    """Смена статуса без разрешения (New → In Progress, Resolved → Closed)."""
    payload: ChangePayload = {"status": _change(before.value, after.value)}
    return record_event(
        db,
        incident=incident,
        actor=actor,
        event_type=HistoryEventType.status_changed,
        payload=payload,
    )


def record_resolved(
    db: Session,
    *,
    incident: Incident,
    actor: User,
    before: IncidentStatus,
    resolution: str,
) -> HistoryEvent:
    """Переход в Resolved: статус + текст решения."""
    payload: ChangePayload = {
        "status": _change(before.value, IncidentStatus.Resolved.value),
        "resolution": _change(None, resolution),
    }
    return record_event(
        db, incident=incident, actor=actor, event_type=HistoryEventType.resolved, payload=payload
    )


def record_priority_changed(
    db: Session, *, incident: Incident, actor: User, before: str, after: str
) -> HistoryEvent:
    """Смена приоритета."""
    payload: ChangePayload = {"priority": _change(before, after)}
    return record_event(
        db,
        incident=incident,
        actor=actor,
        event_type=HistoryEventType.priority_changed,
        payload=payload,
    )


def record_fields_updated(
    db: Session, *, incident: Incident, actor: User, changes: dict[str, tuple[Any, Any]]
) -> HistoryEvent:
    """Изменение прочих полей (title, description, category)."""
    payload: ChangePayload = {
        name: _change(before, after) for name, (before, after) in changes.items()
    }
    return record_event(
        db,
        incident=incident,
        actor=actor,
        event_type=HistoryEventType.fields_updated,
        payload=payload,
    )


def record_commented(
    db: Session, *, incident: Incident, actor: User, comment_id: int, text: str
) -> HistoryEvent:
    """Добавление комментария."""
    payload: ChangePayload = {
        "comment_id": _change(None, comment_id),
        "text": _change(None, text),
    }
    return record_event(
        db, incident=incident, actor=actor, event_type=HistoryEventType.commented, payload=payload
    )