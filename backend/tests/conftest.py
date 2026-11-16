from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.api.deps import USER_ID_HEADER
from app.config import get_settings
from app.db import get_db
from app.main import app


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    """Движок для тестов: отдельная БД через `TEST_DATABASE_URL`, иначе основная.

    Тестовая БД должна быть мигрирована (`alembic upgrade head`).
    """
    url = get_settings().database_url_for_tests
    test_engine = create_engine(url, pool_pre_ping=True)
    yield test_engine
    test_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _require_migrations(engine: Engine) -> None:
    """Явная подсказка, если схема не создана: сначала миграции, потом тесты."""
    with engine.connect() as connection:
        migrated = connection.execute(text("SELECT to_regclass('public.users')")).scalar()
    if migrated is None:
        pytest.exit("База не мигрирована: выполните `alembic upgrade head`", returncode=1)


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    """Сессия внутри транзакции — после теста всё откатывается."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Клиент API, который ходит в тестовую сессию БД."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --- фикстуры HTTP API инцидентов (DMI-7) ---------------------------------

#: Пользователи предзагружены миграцией ``0001_users`` — id стабильны.
ACTOR_ID = 1
ASSIGNEE_ID = 2
MANAGER_ID = 3


@pytest.fixture
def actor_headers() -> dict[str, str]:
    """Заголовок текущего пользователя: инженер Иван Петров (id=1)."""
    return {USER_ID_HEADER: str(ACTOR_ID)}


@pytest.fixture
def make_incident(client: TestClient, actor_headers: dict[str, str]):
    """Фабрика инцидентов через публичный API — так же, как это делает frontend.

    Создаётся инцидент в статусе ``New``; ``status`` прогоняет его по легальному
    маршруту автомата §2, чтобы тест не собирал переходы вручную.
    """

    def _make(
        *,
        title: str = "Не работает почта",
        description: str = "Письма не приходят с утра",
        category: str = "Mail",
        priority: str = "High",
        assignee_id: int | None = None,
        status: str = "New",
    ) -> dict:
        response = client.post(
            "/api/incidents",
            json={
                "title": title,
                "description": description,
                "category": category,
                "priority": priority,
                "assignee_id": assignee_id,
            },
            headers=actor_headers,
        )
        assert response.status_code == 201, response.text
        incident = response.json()

        path = {
            "New": [],
            "In Progress": [{"status": "In Progress"}],
            "Resolved": [
                {"status": "In Progress"},
                {"status": "Resolved", "resolution": "Перезапущен почтовый шлюз"},
            ],
            "Closed": [
                {"status": "In Progress"},
                {"status": "Resolved", "resolution": "Перезапущен почтовый шлюз"},
                {"status": "Closed"},
            ],
        }[status]
        for payload in path:
            updated = client.patch(
                f"/api/incidents/{incident['id']}/status",
                json=payload,
                headers=actor_headers,
            )
            assert updated.status_code == 200, updated.text
            incident = updated.json()

        return incident

    return _make