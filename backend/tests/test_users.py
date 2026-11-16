from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


def test_users_returns_list(client: TestClient) -> None:
    response = client.get("/api/users")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_users_returns_created_user(client: TestClient, db_session: Session) -> None:
    engineer = User(name="Тестовый Инженер", role=UserRole.engineer)
    db_session.add(engineer)
    db_session.flush()

    users = client.get("/api/users").json()

    assert {"id": engineer.id, "name": engineer.name, "role": "engineer"} in users