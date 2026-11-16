"""OpenAPI под контракт TASK.md §3.

FastAPI по умолчанию документирует ошибки схемы запроса как ``422``. По TASK.md
§2–3 некорректные данные — это ``400`` со списком полей, поэтому ``422``
убирается из спецификации: иначе frontend и QA будут ждать код, который API
никогда не возвращает (``RequestValidationError`` переопределён в
``app/api/errors.py``). Доменные ответы (400/404/409) остаются в спецификации.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

#: Код, который FastAPI добавляет автоматически, но этот API его не использует.
_UNUSED_VALIDATION_STATUS = "422"


def build_openapi_schema(app: FastAPI) -> dict[str, Any]:
    """Собрать спецификацию и вычистить неиспользуемый код 422."""
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses")
            if isinstance(responses, dict):
                responses.pop(_UNUSED_VALIDATION_STATUS, None)

    schema.get("components", {}).get("schemas", {}).pop("HTTPValidationError", None)
    schema.get("components", {}).get("schemas", {}).pop("ValidationError", None)

    app.openapi_schema = schema
    return schema


__all__ = ["build_openapi_schema"]