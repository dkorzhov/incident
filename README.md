# IT Incident Tracker (MVP)

Единое рабочее место небольшой ИТ-команды: реестр инцидентов, карточки с комментариями
и автоматической историей, статусы по бизнес-правилам, dashboard.

Концепция — `docs/IT_Incident_Tracker_Концепция_MVP.docx`, макет — `docs/ui-concept.png`,
рабочая спецификация — [TASK.md](TASK.md), правила для агентов — [AGENTS.md](AGENTS.md).

Сейчас в репозитории каркас (DMI-5): работающий Docker Compose, FastAPI с `/api/health`
и `/api/users`, первая миграция `users`, React-оболочка с сайдбаром, Playwright-заглушка.

## Структура

```
backend/    FastAPI, SQLAlchemy 2, Alembic (migrations/), Pytest (tests/)
frontend/   React + TypeScript + Vite, Biome + tsc, Vitest
e2e/        Playwright-сценарии (против поднятого compose)
scripts/    clean-caches.sh — кэши тестов/линта вне worktree (DMI-12)
docs/       концепция, макет UI, спеки и ADR
```

## Запуск

```sh
docker compose up --build     # db :5432 + backend :8000 + frontend :5173
```

- API и Swagger: <http://localhost:8000/api/health>, <http://localhost:8000/docs>
- Интерфейс: <http://localhost:5173>

Миграции применяются автоматически при старте backend (`alembic upgrade head` в entrypoint).
Демо-данные (`SEED_DEMO=true`) появятся отдельным тикетом — сейчас справочник `users`
заполняется первой миграцией.

## API

Все эндпоинты — под `/api`; ответы в `snake_case`, Swagger/OpenAPI — на `/docs`
и `/openapi.json`. Контракт ошибок и решения по нему: `docs/adr/0003-api-contract.md`.

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/api/incidents` | Реестр: `?q=` (номер и название), `?status=`, `?priority=`; сортировка `created_at` desc |
| `POST` | `/api/incidents` | Создать: `title`, `description`, `category`, `priority`, `assignee_id?` |
| `GET` | `/api/incidents/{id}` | Карточка: инцидент + `comments` + `history` + `allowed_transitions` |
| `PATCH` | `/api/incidents/{id}` | `title`, `description`, `category`, `priority`, `assignee_id` |
| `PATCH` | `/api/incidents/{id}/status` | `{ status, resolution? }` — по автомату §2 |
| `POST` | `/api/incidents/{id}/comments` | `{ text }`, автор — текущий пользователь |
| `GET` | `/api/dashboard` | `counts`, `by_priority`, `recent_activity` (10 событий) |
| `GET` | `/api/users` | Справочник сотрудников |

Текущий пользователь передаётся заголовком `X-User-Id` (id из `/api/users`).
Он обязателен для `POST`/`PATCH`/комментариев; чтение доступно без заголовка.

Коды ошибок: `400` — некорректные данные (`{"detail": ..., "errors": [{"field", "reason"}]}`),
`404` — инцидент не найден, `409` — недопустимый переход статуса или изменение закрытого
инцидента. Удаления инцидентов и пагинации в MVP нет.

```sh
curl -s localhost:8000/api/incidents
curl -s -X POST localhost:8000/api/incidents \
  -H 'Content-Type: application/json' -H 'X-User-Id: 1' \
  -d '{"title":"Не работает почта","category":"Mail","priority":"High"}'
```

## Проверки

```sh
docker compose exec backend pytest          # backend-тесты
docker compose exec backend ruff check .    # линт backend
docker compose exec backend alembic upgrade head
cd frontend && npm ci && npm run check      # Biome + tsc
cd frontend && npm test                     # Vitest
cd frontend && npm run build                # сборка
cd e2e && npm ci && npx playwright test     # E2E против поднятого compose
scripts/clean-caches.sh --check             # в worktree не должно быть кэшей
```

Backend-тесты работают на отдельной БД `incident_test` (`TEST_DATABASE_URL`), которую backend
создаёт и мигрирует при старте. Если БД ещё не готова — выполните `alembic upgrade head`.
Локально без Docker задайте `TEST_DATABASE_URL` явно (см. ниже).

### Кэши в worktree (DMI-12)

`pytest`, `ruff` и Vite пишут кэш рядом с кодом (`backend/.pytest_cache`,
`backend/.ruff_cache`, `frontend/node_modules/.vite`). В контейнере, куда смонтирован
worktree, эти каталоги создаются от **root**, и после мержа `git worktree remove` /
`orca worktree rm` падают с `Permission denied` — уборка требует `sudo`.

Два уровня защиты:

- **Образ backend не пишет кэш в bind-mount**: в `backend/Dockerfile` заданы
  `RUFF_CACHE_DIR=/tmp/ruff-cache`, `PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest-cache"`,
  `HOME=/tmp`. Для Vite есть `VITE_CACHE_DIR` (по умолчанию `node_modules/.vite`).
- **Скрипт-уборка без sudo**: `scripts/clean-caches.sh` удаляет кэши одноразовым
  контейнером с примонтированным корнем репозитория — права root внутри контейнера
  совпадают с правами создавшего файлы процесса.

```sh
scripts/clean-caches.sh                 # удалить кэши
scripts/clean-caches.sh --check         # exit 1, если кэши остались (для CI и перед PR)
scripts/clean-caches.sh --dry-run       # только показать, что будет удалено
```

Если запускаете инструменты вручную в контейнере, передавайте uid/gid и выносите кэш:

```sh
docker build -t incident-backend ./backend
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD/backend:/app" -w /app incident-backend pytest
```

Проверка перед сдачей задачи:

```sh
scripts/clean-caches.sh --check && ls -ld backend/.pytest_cache backend/.ruff_cache
```

## Разработка без Docker

```sh
# backend
cd backend
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://incident:incident@localhost:5432/incident
export TEST_DATABASE_URL=postgresql+psycopg://incident:incident@localhost:5432/incident_test
alembic upgrade head
pytest
uvicorn app.main:app --reload --port 8000

# frontend (прокси /api -> http://localhost:8000)
cd frontend
npm ci
npm run dev
```

## Переменные окружения

| Переменная | Где | Значение по умолчанию |
|---|---|---|
| `DATABASE_URL` | backend | `postgresql+psycopg://incident:incident@localhost:5432/incident` |
| `TEST_DATABASE_URL` | backend (тесты) | не задана — тесты идут в `DATABASE_URL` |
| `CORS_ORIGINS` | backend | `http://localhost:5173` |
| `API_PROXY_TARGET` | frontend (Vite-прокси) | `http://localhost:8000` (в compose — `http://backend:8000`) |
| `SEED_DEMO` | backend | `false` (демо-данные — отдельным тикетом) |

Шаблон — [`.env.example`](.env.example); `.env` в `.gitignore` и не коммитится.

## Миграции

```sh
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade -1
docker compose exec backend alembic revision --autogenerate -m "add incidents"
```

## CI

`.github/workflows/ci.yml` — три job'а: `backend` (ruff + миграции + pytest на сервисном
Postgres), `frontend` (Biome + tsc + Vitest + сборка), `e2e` (поднимает compose, прогоняет
команды из AGENTS.md внутри контейнеров и Playwright).

## Stacked PR

Если ветка `B` стоит на ветке `A` (stacked PR), squash-мерж `A` ломает `B`: GitHub
пересоздаёт коммиты, закрывает stacked PR, и переоткрыть или перецелить его нельзя.
Либо мержим базу без squash (`gh pr merge <A> --merge` / `--rebase`), либо сразу
переписываем `B` на `main`:

```sh
git fetch origin
git rebase --onto origin/main <last-commit-of-A> feat/DMI-B-...
git push --force-with-lease origin feat/DMI-B-...
```

Подробности и обоснование — в `AGENTS.md` («Stacked PR и squash-мерж базы»).
