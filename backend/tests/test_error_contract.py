"""Контракт ошибок HTTP-слоя (TASK.md §2–3, DMI-7).

Ошибки — всегда JSON ``{"detail": ...}``; для валидации — ещё и ``errors`` со
списком полей. Коды: 400 — данные, 404 — нет объекта, 409 — состояние.
Здесь же проверяется, что Swagger не обещает 422, которого API не возвращает.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_error_detail_is_string(client: TestClient) -> None:
    body = client.get("/api/incidents/INC-000000").json()

    assert isinstance(body["detail"], str)
    assert body["detail"]


def test_domain_validation_error_contains_fields(client: TestClient) -> None:
    response = client.post(
        "/api/incidents",
        json={"title": "abc", "category": "Mail", "priority": "High"},
        headers={"X-User-Id": "1"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["errors"] == [{"field": "title", "reason": "минимум 5 символов"}]


def test_schema_validation_error_is_400_not_422(client: TestClient) -> None:
    """Pydantic-ошибки отдаются как 400 с тем же форматом, что и доменные."""
    response = client.post(
        "/api/incidents",
        json={"category": "Mail", "priority": "High"},
        headers={"X-User-Id": "1"},
    )

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["detail"]
    assert body["errors"] == [{"field": "title", "reason": "обязательное поле"}]


def test_schema_error_reports_enum_values(client: TestClient) -> None:
    response = client.post(
        "/api/incidents",
        json={"title": "Норм заголовок", "category": "Nope", "priority": "High"},
        headers={"X-User-Id": "1"},
    )

    assert response.status_code == 400
    error = response.json()["errors"][0]
    assert error["field"] == "category"
    assert "Network" in error["reason"]


@pytest.mark.parametrize(
    ("payload", "field", "reason"),
    [
        (
            {"title": 123, "category": "Mail", "priority": "High"},
            "title",
            "ожидается строка",
        ),
        (
            {"title": "Норм заголовок", "category": "Mail", "priority": "High", "bogus": 1},
            "bogus",
            "неизвестное поле",
        ),
        (
            {
                "title": "Норм заголовок",
                "category": "Mail",
                "priority": "High",
                "assignee_id": "два",
            },
            "assignee_id",
            "ожидается целое число",
        ),
        (
            {"title": "Норм заголовок", "category": "Mail", "priority": "High", "assignee_id": -1},
            "assignee_id",
            "положительное число",
        ),
    ],
)
def test_schema_errors_have_readable_russian_reasons(
    client: TestClient, payload: dict, field: str, reason: str
) -> None:
    """Frontend показывает `reason` пользователю: текст должен быть понятным."""
    response = client.post(
        "/api/incidents", json=payload, headers={"X-User-Id": "1"}
    )

    assert response.status_code == 400, response.text
    errors = response.json()["errors"]
    match = next(error for error in errors if error["field"] == field)
    assert reason in match["reason"], match["reason"]


def test_unknown_path_is_404(client: TestClient) -> None:
    assert client.get("/api/nope").status_code == 404


def test_users_endpoint_contract_is_unchanged(client: TestClient) -> None:
    """GET /api/users не сломан: id/name/role."""
    users = client.get("/api/users").json()

    assert users, "пользователи предзагружены миграцией 0001_users"
    assert set(users[0]) == {"id", "name", "role"}


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/api/incidents", "get"),
        ("/api/incidents", "post"),
        ("/api/incidents/{incident_id}", "get"),
        ("/api/incidents/{incident_id}", "patch"),
        ("/api/incidents/{incident_id}/status", "patch"),
        ("/api/incidents/{incident_id}/comments", "post"),
        ("/api/dashboard", "get"),
        ("/api/users", "get"),
    ],
)
def test_openapi_documents_every_endpoint(path: str, method: str) -> None:
    schema = app.openapi()

    assert path in schema["paths"], f"{path} отсутствует в OpenAPI"
    assert method in schema["paths"][path], f"{method.upper()} {path} не описан"


def test_openapi_does_not_advertise_unused_422() -> None:
    """Все ошибки валидации — 400; 422 в контракте сбивал бы frontend."""
    schema = app.openapi()

    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            assert "422" not in operation["responses"], f"{method.upper()} {path}"


def test_openapi_documents_error_contract() -> None:
    schema = app.openapi()
    operation = schema["paths"]["/api/incidents/{incident_id}"]["patch"]

    assert operation["responses"]["409"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }
    assert "ErrorResponse" in schema["components"]["schemas"]


def test_openapi_describes_dashboard_shape() -> None:
    schema = app.openapi()
    dashboard = schema["components"]["schemas"]["DashboardRead"]

    assert set(dashboard["properties"]) == {"counts", "by_priority", "recent_activity"}