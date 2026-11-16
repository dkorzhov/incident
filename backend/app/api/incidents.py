"""Роуты инцидентов (TASK.md §3).

Роуты — тонкий транспорт: приводят тело запроса к доменным DTO, вызывают
сервис и отдают Pydantic-схему. Бизнес-правила (длины, перечисления, автомат
статусов, неизменяемость Closed) проверяет домен, поэтому одни и те же
правила действуют и в API, и в юнит-тестах сервисов. Коды ошибок заданы
в ``app/api/errors.py``: 400 — валидация, 404 — инцидент не найден, 409 —
недопустимый переход или изменение закрытого инцидента.
"""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.api.errors import COMMON_ERRORS
from app.domain.status import allowed_transitions
from app.domain.validation import FieldErrors, parse_enum
from app.models.incident import Incident, IncidentPriority, IncidentStatus
from app.schemas.error import ErrorResponse
from app.schemas.incident import (
    CommentCreateRequest,
    CommentRead,
    HistoryEventRead,
    IncidentCreateRequest,
    IncidentDetailRead,
    IncidentRead,
    IncidentStatusRequest,
    IncidentUpdateRequest,
)
from app.services import incidents as incidents_service

router = APIRouter(prefix="/incidents", tags=["incidents"])

#: Порядок статусов в ответах — как в автомате, а не как получилось из множества.
_STATUS_ORDER = list(IncidentStatus)


@router.get(
    "",
    response_model=list[IncidentRead],
    summary="Реестр инцидентов",
    responses={400: {"model": ErrorResponse, "description": "Некорректный фильтр"}},
)
def list_incidents(
    db: DbSession,
    q: str | None = Query(
        default=None,
        max_length=200,
        description="Поиск по номеру (INC-NNN) и названию, без учёта регистра",
    ),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Фильтр по статусу: New, In Progress, Resolved, Closed",
    ),
    priority: str | None = Query(
        default=None, description="Фильтр по приоритету: Critical, High, Medium, Low"
    ),
) -> Sequence[Incident]:
    """Список инцидентов: новые сверху, поиск и фильтры по TASK.md §3."""
    errors = FieldErrors()
    status_value = errors.collect(
        parse_enum, status_filter, IncidentStatus, field="status"
    ) if _provided(status_filter) else None
    priority_value = errors.collect(
        parse_enum, priority, IncidentPriority, field="priority"
    ) if _provided(priority) else None
    errors.raise_if_any("Некорректные параметры фильтра")

    return incidents_service.list_incidents(
        db, query=q, status=status_value, priority=priority_value
    )


@router.post(
    "",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать инцидент",
    responses={
        400: {"model": ErrorResponse, "description": "Ошибка валидации"},
    },
)
def create_incident(
    payload: IncidentCreateRequest, db: DbSession, user: CurrentUser
) -> Incident:
    """Создать инцидент: номер INC-NNN, статус New, событие `created` в истории."""
    return incidents_service.create_incident(db, payload.to_dto(), actor=user)


@router.get(
    "/{incident_id}",
    response_model=IncidentDetailRead,
    summary="Карточка инцидента",
    responses={404: {"model": ErrorResponse, "description": "Инцидент не найден"}},
)
def get_incident(incident_id: str, db: DbSession) -> IncidentDetailRead:
    """Карточка: инцидент + комментарии + история + допустимые переходы."""
    incident = incidents_service.get_incident(db, incident_id)
    comments = incidents_service.get_incident_comments(db, incident.id)
    history = incidents_service.get_incident_history(db, incident.id)

    return IncidentDetailRead(
        **IncidentRead.model_validate(incident).model_dump(),
        allowed_transitions=sorted(
            allowed_transitions(incident.status), key=_STATUS_ORDER.index
        ),
        comments=[CommentRead.model_validate(comment) for comment in comments],
        history=[HistoryEventRead.model_validate(event) for event in history],
    )


@router.patch(
    "/{incident_id}",
    response_model=IncidentRead,
    summary="Обновить поля инцидента",
    responses=COMMON_ERRORS,
)
def update_incident(
    incident_id: str, payload: IncidentUpdateRequest, db: DbSession, user: CurrentUser
) -> Incident:
    """PATCH title/description/category/priority/assignee_id.

    Закрытый инцидент неизменяем (409). Каждое фактическое изменение пишется
    в историю отдельным событием (`priority_changed`, `assigned`, `fields_updated`).
    """
    return incidents_service.update_incident(
        db, incident_id, payload.to_dto(), actor=user
    )


@router.patch(
    "/{incident_id}/status",
    response_model=IncidentRead,
    summary="Сменить статус по автомату",
    responses=COMMON_ERRORS,
)
def change_status(
    incident_id: str, payload: IncidentStatusRequest, db: DbSession, user: CurrentUser
) -> Incident:
    """Переход по автомату §2: New → In Progress → Resolved → Closed.

    400 — переход в Resolved без resolution; 409 — переход, которого нет в
    автомате, или изменение закрытого инцидента.
    """
    return incidents_service.change_status(
        db, incident_id, payload.to_dto(), actor=user
    )


@router.post(
    "/{incident_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить комментарий",
    responses={
        400: {"model": ErrorResponse, "description": "Ошибка валидации"},
        404: {"model": ErrorResponse, "description": "Инцидент не найден"},
        409: {"model": ErrorResponse, "description": "Инцидент закрыт"},
    },
)
def add_comment(
    incident_id: str, payload: CommentCreateRequest, db: DbSession, user: CurrentUser
) -> CommentRead:
    """Комментарий от текущего пользователя (`X-User-Id`); для Closed — 409."""
    comment = incidents_service.add_comment(
        db, incident_id, payload.to_dto(), actor=user
    )
    return CommentRead.model_validate(comment)


def _provided(value: str | None) -> bool:
    """Пустая строка в query-параметре равнозначна отсутствию фильтра."""
    return value is not None and bool(value.strip())


__all__ = ["router"]