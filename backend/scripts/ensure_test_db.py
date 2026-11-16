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


def main(url_string: str) -> int:
    url = make_url(url_string)
    database = url.database
    if not database or not SAFE_NAME.match(database):
        print(f"Некорректное имя тестовой БД: {database!r}", file=sys.stderr)
        return 2

    admin_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": database}
        ).scalar()
        if exists:
            print(f"Тестовая БД {database} уже существует")
        else:
            owner = url.username or "incident"
            connection.execute(text(f'CREATE DATABASE "{database}" OWNER "{owner}"'))
            print(f"Тестовая БД {database} создана")
    admin_engine.dispose()
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: ensure_test_db.py <database-url>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))