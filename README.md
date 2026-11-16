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
```

Backend-тесты работают на отдельной БД `incident_test` (`TEST_DATABASE_URL`), которую backend
создаёт и мигрирует при старте. Если БД ещё не готова — выполните `alembic upgrade head`.
Локально без Docker задайте `TEST_DATABASE_URL` явно (см. ниже).

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
| `VITE_API_PROXY_TARGET` | frontend | `http://localhost:8000` (в compose — `http://backend:8000`) |

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