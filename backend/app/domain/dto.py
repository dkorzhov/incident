"""Входные данные доменных сервисов (не зависят от FastAPI и Pydantic).

Роуты DMI-7 приводят тело запроса к этим объектам; сервисы валидируют значения
сами, поэтому бизнес-правила нельзя обойти, минуя HTTP-слой.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.validation import UNSET, Unset


@dataclass(frozen=True, slots=True)
class IncidentCreate:
    """Создание инцидента: обязательны title, category, priority."""

    title: Any
    category: Any
    priority: Any
    description: Any = ""
    assignee_id: Any = None


@dataclass(frozen=True, slots=True)
class IncidentUpdate:
    """PATCH инцидента: непереданные поля остаются как есть (``UNSET``)."""

    title: Any | Unset = UNSET
    description: Any | Unset = UNSET
    category: Any | Unset = UNSET
    priority: Any | Unset = UNSET
    assignee_id: Any | Unset = UNSET


@dataclass(frozen=True, slots=True)
class StatusChange:
    """Переход по автомату; ``resolution`` нужен только для Resolved."""

    status: Any
    resolution: Any | Unset = UNSET


@dataclass(frozen=True, slots=True)
class CommentCreate:
    """Новый комментарий к инциденту."""

    text: Any


@dataclass(frozen=True, slots=True)
class IncidentChanges:
    """Результат применения PATCH: чем инцидент отличался до и после.

    ``before``/``after`` — снимки значений по полям, которые изменились;
    используются для payload истории.
    """

    fields: dict[str, tuple[Any, Any]] = field(default_factory=dict)

    def record(self, name: str, before: Any, after: Any) -> None:
        if before != after:
            self.fields[name] = (before, after)

    def __bool__(self) -> bool:
        return bool(self.fields)

    @property
    def priority_changed(self) -> bool:
        return "priority" in self.fields

    @property
    def assignee_changed(self) -> bool:
        return "assignee_id" in self.fields

    def without(self, *names: str) -> dict[str, tuple[Any, Any]]:
        return {name: value for name, value in self.fields.items() if name not in names}


__all__ = [
    "UNSET",
    "CommentCreate",
    "IncidentChanges",
    "IncidentCreate",
    "IncidentUpdate",
    "StatusChange",
    "Unset",
]