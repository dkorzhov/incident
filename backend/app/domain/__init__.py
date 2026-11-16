"""Доменная логика: правила жизненного цикла инцидента.

Здесь нет FastAPI и SQL-запросов — только решения «можно/нельзя» и формат
ошибок (``errors``), поэтому правила TASK.md §2 тестируются без HTTP и БД.
"""

from app.domain.dto import (
    CommentCreate,
    IncidentChanges,
    IncidentCreate,
    IncidentUpdate,
    StatusChange,
)
from app.domain.errors import ConflictError, DomainError, NotFoundError, ValidationError
from app.domain.status import (
    ALLOWED_TRANSITIONS,
    TRANSITION_ACTIONS,
    action_for,
    allowed_transitions,
    ensure_editable,
    ensure_transition_allowed,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "TRANSITION_ACTIONS",
    "CommentCreate",
    "ConflictError",
    "DomainError",
    "IncidentChanges",
    "IncidentCreate",
    "IncidentUpdate",
    "NotFoundError",
    "StatusChange",
    "ValidationError",
    "action_for",
    "allowed_transitions",
    "ensure_editable",
    "ensure_transition_allowed",
]