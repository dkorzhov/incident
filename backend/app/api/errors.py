"""Преобразование доменных ошибок в HTTP-ответы ``{"detail": ...}``.

Сервисы не зависят от FastAPI; здесь единственное место, где доменное
исключение превращается в код ответа и понятный текст (TASK.md §3).
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.errors import DomainError, ValidationError


def domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Ответ для :class:`~app.domain.errors.DomainError`."""
    assert isinstance(exc, DomainError)  # гарантируется регистрацией обработчиков
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """400 со списком полей и причин: ``{"detail": "...", "errors": [...]}``."""
    assert isinstance(exc, ValidationError)
    content: dict[str, Any] = {"detail": exc.detail, "errors": exc.errors}
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=content)


def register_error_handlers(app: FastAPI) -> None:
    """Подключить обработчики доменных ошибок к приложению."""
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)


__all__ = ["domain_error_handler", "register_error_handlers", "validation_error_handler"]