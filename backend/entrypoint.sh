#!/bin/sh
set -e

# Повторяем команду, пока Postgres не станет доступен (depends_on healthy,
# но при рестартах контейнера соединение может быть ещё не готово).
retry() {
  max_attempts=30
  attempt=1
  until "$@"; do
    if [ "$attempt" -ge "$max_attempts" ]; then
      echo "Команда не удалась после $max_attempts попыток: $*" >&2
      return 1
    fi
    echo "Ожидание базы данных (попытка $attempt/$max_attempts)..."
    attempt=$((attempt + 1))
    sleep 2
  done
}

# Основная БД: без миграций приложение стартовать не должно.
if ! retry alembic upgrade head; then
  echo "Не удалось применить миграции основной БД" >&2
  exit 1
fi

# Отдельная БД для тестов (AGENTS.md §5): создаём при необходимости и мигрируем,
# чтобы `docker compose exec backend pytest` работал сразу после старта.
# Сбой здесь не должен мешать приложению подняться — тесты можно запустить позже.
if [ -n "${TEST_DATABASE_URL:-}" ]; then
  if retry python scripts/ensure_test_db.py "$TEST_DATABASE_URL" \
    && retry env DATABASE_URL="$TEST_DATABASE_URL" alembic upgrade head; then
    echo "Тестовая БД готова"
  else
    echo "ВНИМАНИЕ: тестовая БД не подготовлена, приложение стартует без неё" >&2
  fi
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000