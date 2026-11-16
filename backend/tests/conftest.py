from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

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