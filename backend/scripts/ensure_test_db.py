"""Создаёт тестовую БД, если её ещё нет (идемпотентно).

Нужно, чтобы `docker compose exec backend pytest` работал на уже существующем
томе PostgreSQL, где init-скрипты не выполнялись (AGENTS.md §5: отдельная БД для тестов).

Использование: python scripts/ensure_test_db.py postgresql+psycopg://user:pass@host:5432/incident_test
"""

import re
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

SAFE_NAME = re.compile(r"^[A-Za-z0-9_]+$")


def is_safe_name(value: str | None) -> bool:
    """Имя уходит в DDL подстановкой, поэтому допускаем только буквы/цифры/подчёркивания."""
    return bool(value) and SAFE_NAME.fullmatch(value) is not None


def main(url_string: str) -> int:
    url = make_url(url_string)
    database = url.database
    if not is_safe_name(database):
        print(f"Некорректное имя тестовой БД: {database!r}", file=sys.stderr)
        return 2

    owner = url.username or "incident"
    if not is_safe_name(owner):
        print(f"Некорректное имя владельца тестовой БД: {owner!r}", file=sys.stderr)
        return 2

    admin_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": database}
        ).scalar()
        if exists:
            print(f"Тестовая БД {database} уже существует")
        else:
            connection.execute(text(f'CREATE DATABASE "{database}" OWNER "{owner}"'))
            print(f"Тестовая БД {database} создана")
    admin_engine.dispose()
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: ensure_test_db.py <database-url>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))