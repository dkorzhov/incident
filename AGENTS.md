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
| `scripts/clean-caches.sh` | удалить кэши тестов/линта, включая root-owned, без sudo |

Перед завершением задачи: backend-тесты + frontend check/build зелёные локально и в CI.

## Кэши не должны оставаться в worktree (DMI-12)

`pytest`, `ruff` и Vite пишут кэш рядом с кодом: `backend/.pytest_cache`,
`backend/.ruff_cache`, `frontend/node_modules/.vite`. Если инструмент запускали в
контейнере, куда смонтирован worktree (`docker run -v "$PWD/backend:/app" ...`),
на хосте эти каталоги принадлежат **root**. После мержа `git worktree remove` и
`orca worktree rm` не могут удалить worktree — `Permission denied`, уборка
требует `sudo` и потому не автоматизируется.

Правила:

1. **Предпочтительно — локальный venv/`npm ci`** (см. «Разработка без Docker» в
   `README.md`): свои файлы удаляются без sudo.
2. **Если гоняли в Docker** — либо передавайте uid/gid и выносите кэш из
   bind-mount, либо после прогона чистите кэши одной командой:

   ```sh
   # имя тега своё, чтобы не зависеть от имени compose-проекта (каталога worktree)
   docker build -t incident-backend ./backend
   docker run --rm --user "$(id -u):$(id -g)" \
     -e HOME=/tmp -e RUFF_CACHE_DIR=/tmp/ruff-cache \
     -e PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest-cache" \
     -v "$PWD/backend:/app" -w /app incident-backend pytest
   ```

   ```sh
   scripts/clean-caches.sh          # удалить кэши без sudo (работает и для root-owned)
   scripts/clean-caches.sh --check  # exit 1, если в worktree есть кэши
   ```

   Образ backend уже задаёт `RUFF_CACHE_DIR=/tmp/ruff-cache`,
   `PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest-cache"` и `HOME=/tmp`, поэтому
   прогон в контейнере не пишет кэш в смонтированный worktree. Vite принимает
   `VITE_CACHE_DIR=/tmp/vite-cache` (по умолчанию — `node_modules/.vite`).
3. **Перед сдачей задачи** прогоните `scripts/clean-caches.sh --check`: кэшей в
   worktree быть не должно. Это часть Definition of Done, а не «уборка потом»:
   worktree с root-owned каталогами не удаляется после мержа PR.

## Stacked PR и squash-мерж базы

Stacked PR (ветка B стоит на ветке A) ломается, если базу A смержить **squash**:
GitHub пересоздаёт коммиты A, ветка B остаётся с «чужими» коммитами, GitHub
закрывает stacked PR и **переоткрыть или перецелить его нельзя** — PR, закрытый
после мержа базы, не открывается повторно.

Поэтому при стеке выберите один вариант:

1. **Мержить стек без squash базы**: `gh pr merge <A> --merge` (merge commit) или
   `--rebase`, чтобы коммиты A остались в `main` с теми же SHA. Тогда B можно
   перецелить на `main` обычным `gh pr edit <B> --base main`.
2. **После squash-мержа A сразу переписать B на `main`** — до любых правок в PR:

   ```sh
   git fetch origin
   git checkout feat/DMI-B-...
   git rebase --onto origin/main <last-commit-of-A> feat/DMI-B-...
   git push --force-with-lease origin feat/DMI-B-...
   ```

   `--force-with-lease` обязателен: он не даёт затереть чужие изменения ветки.
   После force-push PR B остаётся открытым и уже стоит на актуальном `main`;
   если GitHub успел его закрыть — открой новый PR из той же ветки.

В описании stacked PR укажите базу и порядок мержа («stacked on #N, merge after #N»).

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
9. Кэши тестов/линта не оставляем в worktree: локальный venv или `--user` + `scripts/clean-caches.sh`
   (раздел «Кэши не должны оставаться в worktree»). Worktree с root-owned кэшами не удаляется.
10. Stacked PR: мержим базу без squash либо сразу `rebase --onto` + `push --force-with-lease`
    (раздел «Stacked PR и squash-мерж базы»).

## Структура

```
backend/    app/ (api, domain, models, services), migrations/, tests/
frontend/   src/ (components, pages, api)
e2e/        Playwright-сценарии
scripts/    гигиена worktree: clean-caches.sh (DMI-12)
docs/       концепция (docx), макет (ui-concept.png), ADR и спеки агентов
TASK.md     рабочая спецификация
```

## Linear

Команда `DMI`, проект Incident Tracker Lite. В описании PR указывай DMI-NNN.