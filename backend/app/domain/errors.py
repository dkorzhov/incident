"""Доменные ошибки и их отображение в HTTP (TASK.md §2–3).

Сервисы ничего не знают про FastAPI: они поднимают эти исключения, а
``app/api/errors.py`` превращает их в JSON ``{"detail": ...}`` с нужным кодом.
Так бизнес-правила остаются проверяемыми юнит-тестами без HTTP-клиента.
"""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Базовая доменная ошибка; ``status_code`` — HTTP-код для API-слоя."""

    status_code: int = 400
    detail: str = "Нарушено бизнес-правило"

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class ValidationError(DomainError):
    """Некорректные входные данные (400): список полей и причин."""

    status_code = 400

    def __init__(self, errors: list[dict[str, Any]], detail: str | None = None) -> None:
        self.errors = errors
        super().__init__(detail or _format_errors(errors))

    @classmethod
    def for_field(cls, field: str, reason: str) -> ValidationError:
        return cls([{"field": field, "reason": reason}])


def _format_errors(errors: list[dict[str, Any]]) -> str:
    parts = []
    for error in errors:
        field = error.get("field", "?")
        reason = error.get("reason", "некорректное значение")
        parts.append(f"{field}: {reason}")
    return "Некорректные данные — " + "; ".join(parts)


class NotFoundError(DomainError):
    """Запрошенной сущности нет (404)."""

    status_code = 404
    detail = "Объект не найден"


class ConflictError(DomainError):
    """Действие нарушает бизнес-правило состояния (409)."""

    status_code = 409
    detail = "Действие недопустимо в текущем состоянии"