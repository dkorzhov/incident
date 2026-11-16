# AGENTS.md — IT Incident Tracker (MVP)

**Источник истины по требованиям — `TASK.md`** (оригинал концепции — в `docs/`, макет UI — `docs/ui-concept.png`).
Не расширяй скоуп: раздел 8 TASK.md обязателен к соблюдению. SLA в проекте НЕТ.

## Стек (зафиксирован концепцией)

- Backend: **Python 3.12 + FastAPI + SQLAlchemy 2 + PostgreSQL 16**, миграции **Alembic**.
- Frontend: **React + TypeScript + Vite**, обычный CSS (ориентир — макет), без дизайн-фреймворков.
- Тесты: **Pytest** (backend, БД — отдельная тестовая схема/контейнер), **Playwright** (e2e/).
- Линт: **ruff** (backend), **Biome + tsc** (frontend).
- Запуск: **Docker Compose** (db + backend + frontend).

## Команды

| Команда | Что делает |
|---|---|
| `docker compose up --build` | поднять всё приложение (db + api + web) |
| `docker compose exec backend pytest` | backend-тесты |
| `docker compose exec backend alembic upgrade head` | миграции |
| `docker compose exec backend ruff check .` | линт backend |
| `cd frontend && npm ci && npm run check` | линт + typecheck frontend |
| `cd frontend && npm run build` | сборка frontend |
| `cd e2e && npm ci && npx playwright test` | E2E (против поднятого compose) |

Перед завершением задачи: backend-тесты + frontend check/build зелёные локально и в CI.

## Роли агентов (концепция, §7)

| Агент | Роль | Права |
|---|---|---|
| `analyst` | требования, user stories, критерии приёмки | read-only, пишет только в `docs/` |
| `architect` | архитектура, API-контракт, схема БД, ADR | read-only, пишет только в `docs/` |
| `backend` | FastAPI, бизнес-логика, миграции, Pytest | правит `backend/`, не трогает `frontend/` |
| `frontend` | React, интерфейс, интеграция с API | правит `frontend/`, не трогает `backend/` |
| `qa` | тест-кейсы, автотесты, поиск дефектов | правит только тесты (`backend/tests/`, `e2e/`), модель другая |

Конвейер: analyst → architect → backend → frontend → qa. Каждый этап — отдельная сессия/worker
со своим агентом; результаты предыдущего этапа читаются из `docs/` и кода.

## Правила работы

1. **Одна задача Linear = одна ветка = один PR.** Ветка: `feat/DMI-<номер>-<slug>`.
2. Прямые пуши в `main` запрещены (branch protection). PR через `gh pr create`, мержит человек.
3. Коммиты — conventional commits (`feat:`, `fix:`, `test:`, `chore:`, `docs:`).
4. Бизнес-правила проверяются на backend, не только в UI (TASK.md §2). Closed неизменяем, удаления нет.
5. Каждое значимое изменение — автоматическая запись в историю; не забывай payload «было/стало».
6. Не удаляй и не ослабляй существующие тесты ради «зелёного» прогона.
7. Текущий пользователь — заголовок `X-User-Id`, валидируется против списка users.
8. Секреты и `.env` не коммитить.

## Структура

```
backend/    app/ (api, domain, models, services), migrations/, tests/
frontend/   src/ (components, pages, api)
e2e/        Playwright-сценарии
docs/       концепция (docx), макет (ui-concept.png), ADR и спеки агентов
TASK.md     рабочая спецификация
```

## Linear

Команда `DMI`, проект Incident Tracker Lite. В описании PR указывай DMI-NNN.