"""Преобразование доменных ошибок в HTTP-ответы ``{"detail": ...}``.

Сервисы не зависят от FastAPI; здесь единственное место, где доменное
исключение превращается в код ответа и понятный текст (TASK.md §3).

Дополнительно сюда же приведена ошибка валидации самого FastAPI/Pydantic:
по TASK.md §2 «валидация полей → 400 с указанием полей и причин», поэтому
``RequestValidationError`` отдаётся как 400 (а не дефолтные 422) с тем же
форматом ``errors``, что и у доменной валидации.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.errors import DomainError, ValidationError
from app.schemas.error import ErrorResponse

#: Типовые ответы роутов, меняющих инцидент: 400/404/409 (TASK.md §2–3).
COMMON_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ErrorResponse,
        "description": "Ошибка валидации (поля и причины в `errors`)",
    },
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": "Инцидент не найден",
    },
    status.HTTP_409_CONFLICT: {
        "model": ErrorResponse,
        "description": "Недопустимый переход статуса или изменение закрытого инцидента",
    },
}


def domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Ответ для :class:`~app.domain.errors.DomainError`."""
    assert isinstance(exc, DomainError)  # гарантируется регистрацией обработчиков
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """400 со списком полей и причин: ``{"detail": "...", "errors": [...]}``."""
    assert isinstance(exc, ValidationError)
    content: dict[str, Any] = {"detail": exc.detail, "errors": exc.errors}
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=content)


def request_validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """400 для ошибок схемы запроса — тот же формат, что у доменной валидации."""
    assert isinstance(exc, RequestValidationError)
    errors = [_schema_error(error) for error in exc.errors()]
    domain_error = ValidationError(errors, detail=None)
    content: dict[str, Any] = {"detail": domain_error.detail, "errors": errors}
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=content)


def _schema_error(error: dict[str, Any]) -> dict[str, str]:
    """Привести ошибку Pydantic к виду ``{"field": ..., "reason": ...}``."""
    loc = [part for part in error.get("loc", ()) if part not in ("body", "query", "path")]
    field = ".".join(str(part) for part in loc) or "body"
    return {"field": field, "reason": _reason(error)}


def _reason(error: dict[str, Any]) -> str:
    """Понятный текст причины: для enum-полей перечисляем допустимые значения.

    Pydantic отдаёт ``msg`` на английском, поэтому частые типы ошибок переводим
    по ``type`` (стабильнее, чем сравнивать текст сообщения). Для enum — список
    допустимых значений из ``ctx.expected``.
    """
    error_type = str(error.get("type", ""))
    ctx = error.get("ctx") or {}
    expected = ctx.get("expected")
    if expected:
        return f"допустимые значения: {expected}"

    translated = _REASON_BY_TYPE.get(error_type)
    if translated is not None:
        return translated
    return str(error.get("msg", "некорректное значение"))


#: Переводы типов ошибок Pydantic, которые реально встречаются в API.
_REASON_BY_TYPE: dict[str, str] = {
    "missing": "обязательное поле",
    "string_type": "ожидается строка",
    "int_type": "ожидается целое число",
    "int_parsing": "ожидается целое число",
    "bool_type": "ожидается логическое значение",
    "extra_forbidden": "неизвестное поле — допустимы только поля из спецификации",
    "string_too_short": "слишком короткое значение",
    "string_too_long": "слишком длинное значение",
    "greater_than": "значение вне допустимого диапазона",
    "json_invalid": "тело запроса должно быть корректным JSON",
}


def register_error_handlers(app: FastAPI) -> None:
    """Подключить обработчики ошибок к приложению."""
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)


__all__ = [
    "COMMON_ERRORS",
    "domain_error_handler",
    "register_error_handlers",
    "request_validation_error_handler",
    "validation_error_handler",
]