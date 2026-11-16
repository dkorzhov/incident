"""Инцидент — центральная сущность домена (TASK.md §1).

Идентификатор ``INC-NNN`` генерирует сервер: ``server_default`` колонки ``id``
вызывает функцию ``next_incident_id()``, которая берёт следующее значение
последовательности ``incident_number_seq`` и форматирует его. Последовательность
выдаёт номера атомарно, без ``max+1`` и без гонок при параллельном создании;
при откате транзакции номер «сгорает» (в нумерации возможен пропуск) — для
человекочитаемого номера это допустимо.
Решение зафиксировано в ``docs/adr/0002-backend-domain.md``.

Форматирование вынесено в функцию миграцией ``0003_incident_number_padding``:
``lpad(n::text, 3, '0')`` не только дополнял короткие номера, но и обрезал
длинные (``1133`` → ``113``), из-за чего 1000-й инцидент падал с нарушением
первичного ключа. Детали — в ``docs/adr/0003-api-contract.md``.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Final

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, enum_column
from app.models.comment import Comment
from app.models.history import HistoryEvent
from app.models.user import User

#: Последовательность, из которой PostgreSQL берёт номер инцидента.
INCIDENT_NUMBER_SEQUENCE: Final = "incident_number_seq"

#: Функция, форматирующая номер ``INC-NNN`` (не обрезает номера >= 1000).
INCIDENT_NUMBER_FORMAT_FUNCTION: Final = "format_incident_number"

#: DEFAULT для ``incidents.id``: ``INC-001``, ``INC-002``, ... ``INC-1000``.
INCIDENT_ID_SERVER_DEFAULT: Final = text("next_incident_id()")

TITLE_MAX_LENGTH: Final = 120
DESCRIPTION_MAX_LENGTH: Final = 2000
RESOLUTION_MAX_LENGTH: Final = 2000


class IncidentCategory(StrEnum):
    """Категория инцидента."""

    Network = "Network"
    Mail = "Mail"
    Portal = "Portal"
    Database = "Database"
    Workplace = "Workplace"
    Other = "Other"


class IncidentPriority(StrEnum):
    """Приоритет инцидента."""

    Critical = "Critical"
    High = "High"
    Medium = "Medium"
    Low = "Low"


class IncidentStatus(StrEnum):
    """Статус инцидента; переходы — только по автомату TASK.md §2."""

    New = "New"
    InProgress = "In Progress"
    Resolved = "Resolved"
    Closed = "Closed"


class Incident(Base):
    """Инцидент ИТ-службы."""

    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        server_default=INCIDENT_ID_SERVER_DEFAULT,
        doc="Человекочитаемый номер INC-NNN, выдаётся последовательностью PostgreSQL.",
    )
    title: Mapped[str] = mapped_column(String(TITLE_MAX_LENGTH), nullable=False)
    description: Mapped[str] = mapped_column(
        String(DESCRIPTION_MAX_LENGTH), nullable=False, default="", server_default=text("''")
    )
    category: Mapped[IncidentCategory] = mapped_column(
        enum_column(IncidentCategory, name="incident_category"), nullable=False
    )
    priority: Mapped[IncidentPriority] = mapped_column(
        enum_column(IncidentPriority, name="incident_priority"), nullable=False, index=True
    )
    status: Mapped[IncidentStatus] = mapped_column(
        enum_column(IncidentStatus, name="incident_status"),
        nullable=False,
        default=IncidentStatus.New,
        server_default=text("'New'"),
        index=True,
    )
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    resolution: Mapped[str | None] = mapped_column(String(RESOLUTION_MAX_LENGTH), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Многие-к-одному грузится явно (select/joinedload у вызывающего кода):
    # joined-eager здесь ломал бы `SELECT ... FOR UPDATE` (outer join).
    assignee: Mapped[User | None] = relationship(User)
    comments: Mapped[list[Comment]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by=lambda: [Comment.created_at, Comment.id],
    )
    history: Mapped[list[HistoryEvent]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by=lambda: [HistoryEvent.created_at, HistoryEvent.id],
    )

    __table_args__ = (
        # Проверки дублируют ограничения миграции 0002_incidents: сервис отдаёт
        # 400 раньше, БД остаётся последним рубежом целостности.
        CheckConstraint(
            "char_length(btrim(title)) BETWEEN 5 AND 120", name="ck_incidents_title_length"
        ),
        CheckConstraint(
            "char_length(description) <= 2000", name="ck_incidents_description_length"
        ),
        CheckConstraint(
            "resolution IS NULL OR char_length(resolution) BETWEEN 1 AND 2000",
            name="ck_incidents_resolution_length",
        ),
        CheckConstraint(
            "status <> 'Resolved' OR (resolution IS NOT NULL AND btrim(resolution) <> '')",
            name="ck_incidents_resolved_requires_resolution",
        ),
    )