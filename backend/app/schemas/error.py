"""Схемы ошибок для OpenAPI: ``{"detail": ...}`` по TASK.md §3.

Схемы не участвуют в формировании ответов (их строит ``app/api/errors.py``),
но документируют контракт ошибок в Swagger: у валидации (400) есть ещё и
список полей с причинами.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FieldErrorRead(BaseModel):
    """Одна ошибка поля: что именно не так."""

    field: str = Field(examples=["title"], description="Имя поля запроса")
    reason: str = Field(examples=["минимум 5 символов"], description="Причина на русском")


class ErrorResponse(BaseModel):
    """Ответ с ошибкой (400/404/409)."""

    detail: str = Field(examples=["Инцидент INC-999 не найден"])
    errors: list[FieldErrorRead] | None = Field(
        default=None, description="Список ошибок по полям — только для 400"
    )


__all__ = ["ErrorResponse", "FieldErrorRead"]