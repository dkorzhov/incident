"""Схемы инцидентов, комментариев и истории (TASK.md §3).

Роуты не перепроверяют бизнес-правила: значения (длины, перечисления,
обязательность, автомат статусов) валидирует домен
(``app/domain/validation.py``, ``app/domain/status.py``). Схемы решают только
транспортную задачу:

* отличают «поле не передано» (``UNSET``) от «передано явно» — в том числе
  ``null`` как очистку ``assignee_id``/``description`` в PATCH;
* описывают контракт ответов в snake_case для Swagger и frontend.

Константы длин берутся из моделей, чтобы документация не расходилась с БД.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.dto import (
    UNSET,
    CommentCreate,
    IncidentCreate,
    IncidentUpdate,
    StatusChange,
)
from app.models.comment import COMMENT_TEXT_MAX_LENGTH
from app.models.history import HistoryEventType
from app.models.incident import (
    DESCRIPTION_MAX_LENGTH,
    RESOLUTION_MAX_LENGTH,
    TITLE_MAX_LENGTH,
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
)
from app.schemas.user import UserBriefRead

# --- запросы ---------------------------------------------------------------


class IncidentCreateRequest(BaseModel):
    """Тело ``POST /api/incidents``."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "title": "Не работает почта",
                "description": "Письма не приходят с 9:00",
                "category": "Mail",
                "priority": "High",
                "assignee_id": 1,
            }
        },
    )

    title: str = Field(description=f"Название, 5–{TITLE_MAX_LENGTH} символов")
    description: str | None = Field(
        default="", description=f"Детали, до {DESCRIPTION_MAX_LENGTH} символов"
    )
    category: IncidentCategory = Field(description="Категория инцидента")
    priority: IncidentPriority = Field(description="Приоритет инцидента")
    assignee_id: int | None = Field(
        default=None, description="Ответственный из `/api/users`; null — без ответственного"
    )

    def to_dto(self) -> IncidentCreate:
        """Входные данные сервиса: значения проверит домен."""
        return IncidentCreate(
            title=self.title,
            description=self.description,
            category=self.category,
            priority=self.priority,
            assignee_id=self.assignee_id,
        )


class IncidentUpdateRequest(BaseModel):
    """Тело ``PATCH /api/incidents/{id}``.

    Поля, отсутствующие в теле, не меняются. Явный ``null`` означает очистку:
    ``assignee_id: null`` снимает ответственного, ``description: null`` очищает
    описание. ``title``/``category``/``priority`` обязательны по смыслу и
    ``null`` для них — 400.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"priority": "Critical", "assignee_id": 2}},
    )

    title: str | None = Field(
        default=None, description=f"Название, 5–{TITLE_MAX_LENGTH} символов"
    )
    description: str | None = Field(
        default=None, description=f"Детали, до {DESCRIPTION_MAX_LENGTH} символов"
    )
    category: IncidentCategory | None = Field(default=None, description="Категория инцидента")
    priority: IncidentPriority | None = Field(default=None, description="Приоритет инцидента")
    assignee_id: int | None = Field(
        default=None, description="Ответственный; null — снять ответственного"
    )

    def to_dto(self) -> IncidentUpdate:
        """Собрать DTO: непереданные поля остаются ``UNSET`` (не меняются)."""

        def provided(name: str) -> Any:
            return getattr(self, name) if name in self.model_fields_set else UNSET

        return IncidentUpdate(
            title=provided("title"),
            description=provided("description"),
            category=provided("category"),
            priority=provided("priority"),
            assignee_id=provided("assignee_id"),
        )


class IncidentStatusRequest(BaseModel):
    """Тело ``PATCH /api/incidents/{id}/status`` — шаг автомата §2."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"status": "Resolved", "resolution": "Перезапущен шлюз"}},
    )

    status: IncidentStatus = Field(description="Целевой статус")
    resolution: str | None = Field(
        default=None,
        description=(
            f"Описание решения, 1–{RESOLUTION_MAX_LENGTH} символов; "
            "обязательно при переходе в Resolved"
        ),
    )

    def to_dto(self) -> StatusChange:
        """``resolution`` без значения остаётся ``UNSET`` — домен его не применит."""
        resolution = (
            self.resolution if "resolution" in self.model_fields_set else UNSET
        )
        return StatusChange(status=self.status, resolution=resolution)


class CommentCreateRequest(BaseModel):
    """Тело ``POST /api/incidents/{id}/comments``."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"text": "Уточните, пожалуйста, время события"}},
    )

    text: str = Field(description=f"Текст комментария, 1–{COMMENT_TEXT_MAX_LENGTH} символов")

    def to_dto(self) -> CommentCreate:
        return CommentCreate(text=self.text)


# --- ответы ----------------------------------------------------------------


class CommentRead(BaseModel):
    """Комментарий в карточке инцидента."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: str
    author_id: int
    author: UserBriefRead = Field(description="Автор комментария (для отображения имени)")
    text: str
    created_at: datetime


class HistoryEventRead(BaseModel):
    """Событие истории: кто, когда и что изменил (``payload`` — «было/стало»)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: str
    actor_id: int
    actor: UserBriefRead = Field(description="Кто выполнил действие")
    type: HistoryEventType
    payload: dict[str, Any] = Field(description="Изменения вида `{field: {from, to}}`")
    created_at: datetime


class IncidentRead(BaseModel):
    """Инцидент в реестре и в ответах на изменения."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(examples=["INC-001"], description="Номер INC-NNN, выдаёт сервер")
    title: str
    description: str
    category: IncidentCategory
    priority: IncidentPriority
    status: IncidentStatus
    assignee_id: int | None
    assignee: UserBriefRead | None = Field(
        default=None, description="Ответственный (name — для таблицы реестра)"
    )
    resolution: str | None = Field(default=None, description="Обязателен для Resolved")
    created_at: datetime
    updated_at: datetime


class IncidentDetailRead(IncidentRead):
    """Карточка: инцидент + комментарии + история + доступные переходы."""

    allowed_transitions: list[IncidentStatus] = Field(
        default_factory=list,
        description="Статусы, в которые можно перевести инцидент сейчас (TASK.md §2)",
    )
    comments: list[CommentRead] = Field(default_factory=list)
    history: list[HistoryEventRead] = Field(default_factory=list)


__all__ = [
    "CommentCreateRequest",
    "CommentRead",
    "HistoryEventRead",
    "IncidentCreateRequest",
    "IncidentDetailRead",
    "IncidentRead",
    "IncidentStatusRequest",
    "IncidentUpdateRequest",
]