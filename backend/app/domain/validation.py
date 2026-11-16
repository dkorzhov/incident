"""Проверка полей инцидента/комментария — общая для сервисов и будущих роутов.

Все функции возвращают нормализованное значение или поднимают
:class:`~app.domain.errors.ValidationError` (→ HTTP 400). Проверки не ходят
в БД: уникальность/существование сущностей — забота сервисов.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Final, TypeVar

from app.domain.errors import ValidationError

T = TypeVar("T")


@dataclass(frozen=True)
class Unset:
    """Сентинел «поле не передано» — отличается от ``None`` (явная очистка)."""

    def __repr__(self) -> str:  # pragma: no cover - только для отладки
        return "UNSET"


UNSET: Final = Unset()


class FieldErrors:
    """Копит ошибки по нескольким полям, чтобы вернуть все причины сразу."""

    def __init__(self) -> None:
        self._errors: list[dict[str, str]] = []

    def add(self, field: str, reason: str) -> None:
        self._errors.append({"field": field, "reason": reason})

    def extend(self, errors: list[dict[str, Any]]) -> None:
        self._errors.extend({"field": e["field"], "reason": e["reason"]} for e in errors)

    def collect(self, validate: Callable[..., T], *args: Any, **kwargs: Any) -> T | None:
        """Выполнить проверку, запомнив ошибку; вернуть ``None`` вместо исключения."""
        try:
            return validate(*args, **kwargs)
        except ValidationError as exc:
            self.extend(exc.errors)
            return None

    def raise_if_any(self, detail: str | None = None) -> None:
        if self._errors:
            raise ValidationError(self._errors, detail=detail)


def clean_text(
    value: Any,
    *,
    field: str,
    min_length: int = 0,
    max_length: int,
    required: bool = True,
) -> str:
    """Проверить строковое поле и вернуть его без ведущих/хвостовых пробелов."""
    if value is None:
        if required:
            raise ValidationError.for_field(field, "обязательное поле")
        return ""
    if not isinstance(value, str):
        raise ValidationError.for_field(field, "ожидается строка")
    cleaned = value.strip()
    length = len(cleaned)
    if required and length == 0:
        raise ValidationError.for_field(field, "обязательное поле")
    if min_length and 0 < length < min_length:
        raise ValidationError.for_field(field, f"минимум {min_length} символов")
    if length > max_length:
        raise ValidationError.for_field(field, f"не более {max_length} символов")
    return cleaned


def parse_enum[E: Enum](value: Any, enum_cls: type[E], *, field: str) -> E:
    """Принять значение перечисления (член enum или его строковое значение)."""
    if isinstance(value, enum_cls):
        return value
    if not isinstance(value, str):
        raise ValidationError.for_field(field, f"ожидается одно из: {_enum_values(enum_cls)}")
    try:
        return enum_cls(value.strip())
    except ValueError:
        raise ValidationError.for_field(
            field, f"допустимые значения: {_enum_values(enum_cls)}"
        ) from None


def clean_identifier(value: Any, *, field: str) -> int | None:
    """Необязательный идентификатор пользователя: ``None`` или положительный int."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError.for_field(field, "ожидается целое число или null")
    if value <= 0:
        raise ValidationError.for_field(field, "ожидается положительное число")
    return value


def _enum_values(enum_cls: type[Enum]) -> str:
    return ", ".join(str(member.value) for member in enum_cls)