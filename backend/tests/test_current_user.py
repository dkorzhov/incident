"""Тесты зависимости `X-User-Id` и отображения доменных ошибок в HTTP.

Публичных эндпоинтов инцидентов пока нет (DMI-7), поэтому проверяем:
* ``get_current_user`` — разбор/валидация заголовка против таблицы ``users``;
* временный роут на ``register_error_handlers`` — что доменная ошибка становится
  400/409 с ``{"detail": ...}``, а валидация — ещё и со списком ``errors``.
"""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import USER_ID_HEADER, get_current_user
from app.api.errors import register_error_handlers
from app.db import get_db
from app.domain.errors import ConflictError, NotFoundError, ValidationError
from app.models.user import User, UserRole


@pytest.fixture
def probe_app(db_session: Session) -> FastAPI:
    """Мини-приложение с временными роутами: наружу ничего не публикуется."""
    app = FastAPI()
    register_error_handlers(app)
    app.dependency_overrides[get_db] = lambda: db_session

    @app.get("/probe/whoami")
    def whoami(user: User = Depends(get_current_user)) -> dict:
        return {"id": user.id, "name": user.name}

    @app.get("/probe/validation")
    def validation_error() -> dict:
        raise ValidationError.for_field("title", "минимум 5 символов")

    @app.get("/probe/conflict")
    def conflict_error() -> dict:
        raise ConflictError("Недопустимый переход статуса")

    @app.get("/probe/not-found")
    def not_found_error() -> dict:
        raise NotFoundError("Инцидент INC-999 не найден")

    return app


@pytest.fixture
def probe_client(probe_app: FastAPI) -> TestClient:
    return TestClient(probe_app)


def test_missing_user_header_returns_400(probe_client: TestClient) -> None:
    response = probe_client.get("/probe/whoami")

    assert response.status_code == 400
    body = response.json()
    assert USER_ID_HEADER in body["detail"]
    assert body["errors"][0]["field"] == USER_ID_HEADER


def test_blank_user_header_returns_400(probe_client: TestClient) -> None:
    response = probe_client.get("/probe/whoami", headers={USER_ID_HEADER: "   "})

    assert response.status_code == 400


@pytest.mark.parametrize("value", ["abc", "1.5", "0", "-3", ""])
def test_non_integer_or_non_positive_header_returns_400(
    probe_client: TestClient, value: str
) -> None:
    response = probe_client.get("/probe/whoami", headers={USER_ID_HEADER: value})

    assert response.status_code == 400
    assert response.json()["detail"]


def test_unknown_user_header_returns_400(probe_client: TestClient) -> None:
    response = probe_client.get("/probe/whoami", headers={USER_ID_HEADER: "999999"})

    assert response.status_code == 400
    assert "не найден" in response.json()["detail"]


def test_known_user_header_returns_user(probe_client: TestClient, db_session: Session) -> None:
    user = User(name="Пользователь Заголовка", role=UserRole.manager)
    db_session.add(user)
    db_session.flush()

    response = probe_client.get("/probe/whoami", headers={USER_ID_HEADER: str(user.id)})

    assert response.status_code == 200
    assert response.json() == {"id": user.id, "name": user.name}


def test_header_is_trimmed(probe_client: TestClient, db_session: Session) -> None:
    user = User(name="Пользователь С Пробелами", role=UserRole.engineer)
    db_session.add(user)
    db_session.flush()

    response = probe_client.get("/probe/whoami", headers={USER_ID_HEADER: f"  {user.id}  "})

    assert response.status_code == 200
    assert response.json()["id"] == user.id


def test_domain_validation_error_maps_to_400_with_fields(probe_client: TestClient) -> None:
    response = probe_client.get("/probe/validation")

    assert response.status_code == 400
    body = response.json()
    assert "title" in body["detail"]
    assert body["errors"] == [{"field": "title", "reason": "минимум 5 символов"}]


def test_domain_conflict_maps_to_409(probe_client: TestClient) -> None:
    response = probe_client.get("/probe/conflict")

    assert response.status_code == 409
    assert "Недопустимый переход" in response.json()["detail"]


def test_domain_not_found_maps_to_404(probe_client: TestClient) -> None:
    response = probe_client.get("/probe/not-found")

    assert response.status_code == 404
    assert "INC-999" in response.json()["detail"]