"""Проверки валидации имён в scripts/ensure_test_db.py (имена уходят в DDL)."""

import pytest

from scripts.ensure_test_db import is_safe_name, main


@pytest.mark.parametrize("name", ["incident_test", "Test1", "_internal", "a"])
def test_safe_names_accepted(name: str) -> None:
    assert is_safe_name(name)


@pytest.mark.parametrize(
    "name",
    [
        None,
        "",
        'db"; DROP DATABASE incident; --',
        "db-name",
        "db name",
        "db;",
        "db\n",
        "db'",
    ],
)
def test_unsafe_names_rejected(name: str | None) -> None:
    assert not is_safe_name(name)


def test_main_rejects_unsafe_owner_before_connecting() -> None:
    # Порт заведомо закрыт: при небезопасном имени функция обязана выйти раньше
    # попытки подключения, поэтому тест не требует запущенного PostgreSQL.
    url = 'postgresql+psycopg://bad";--:secret@127.0.0.1:1/incident_test'
    assert main(url) == 2


def test_main_rejects_unsafe_database_before_connecting() -> None:
    url = 'postgresql+psycopg://incident:secret@127.0.0.1:1/bad-db'
    assert main(url) == 2