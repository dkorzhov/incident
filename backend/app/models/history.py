"""Автоматический журнал изменений инцидента (TASK.md §1–2).

События пишет только сервисный слой (``app/services/history.py``) в той же
транзакции, что и само изменение, — поэтому история не может разойтись с данными.

Схема ``payload`` (все значения — «было/стало»):

* ``created``          — ``{"title": {"from": null, "to": ...}, "category": {...},
  "priority": {...}, "description": {...}, "assignee_id": {...}}``
* ``assigned``         — ``{"assignee_id": {"from": 1|null, "to": 2|null},
  "assignee": {"from": "Имя"|null, "to": "Имя"|null}}``
* ``priority_changed`` — ``{"priority": {"from": ..., "to": ...}}``
* ``status_changed``   — ``{"status": {"from": ..., "to": ...}}``
* ``resolved``         — ``{"status": {...}, "resolution": {"from": null, "to": ...}}``
* ``commented``        — ``{"comment_id": {"from": null, "to": 12},
  "text": {"from": null, "to": "..."}}``
* ``fields_updated``   — по ключу на каждое изменённое поле:
  ``{"title": {"from": ..., "to": ...}, ...}``
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, enum_column
from app.models.user import User

if TYPE_CHECKING:
    from app.models.incident import Incident


class HistoryEventType(StrEnum):
    """Тип события истории."""

    created = "created"
    assigned = "assigned"
    status_changed = "status_changed"
    priority_changed = "priority_changed"
    commented = "commented"
    resolved = "resolved"
    fields_updated = "fields_updated"


#: Значения «было/стало», используемые в payload.
ChangePayload = dict[str, dict[str, Any]]


class HistoryEvent(Base):
    """Событие «кто, когда, что и на что изменил»."""

    __tablename__ = "history_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[str] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    type: Mapped[HistoryEventType] = mapped_column(
        enum_column(HistoryEventType, name="history_event_type"), nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    incident: Mapped[Incident] = relationship("Incident", back_populates="history")
    actor: Mapped[User] = relationship(User)

    __table_args__ = (
        # Лента «последние события» по всему проекту (dashboard) — без сортировки в памяти.
        Index("ix_history_events_created_at_id", "created_at", "id"),
    )