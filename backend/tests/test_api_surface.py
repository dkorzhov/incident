"""Инварианты поверхности API из TASK.md §8.

Удаление инцидентов не предусмотрено — DELETE-эндпоинта не должно появиться
ни в этом тикете, ни позже. Тест дешёвый и защищает инвариант от регрессии.
"""

from __future__ import annotations

from fastapi.routing import APIRoute

from app.main import app


def test_api_exposes_no_delete_endpoints() -> None:
    delete_routes = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if "DELETE" in (route.methods or set()):
            delete_routes.append(route.path)

    assert delete_routes == [], f"DELETE запрещён в MVP (TASK.md §8): {delete_routes}"


def test_domain_services_do_not_expose_delete() -> None:
    """Домен не умеет удалять инциденты — даже внутренним вызовом."""
    from app.services import incidents

    public = [name for name in dir(incidents) if not name.startswith("_")]
    assert [name for name in public if "delete" in name.lower()] == []