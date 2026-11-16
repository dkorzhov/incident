# IT Incident Tracker (MVP)

Единое рабочее место небольшой ИТ-команды: реестр инцидентов, карточки с комментариями
и автоматической историей, статусы по бизнес-правилам, dashboard.

Концепция — `docs/IT_Incident_Tracker_Концепция_MVP.docx`, макет — `docs/ui-concept.png`,
рабочая спецификация — [TASK.md](TASK.md), правила для агентов — [AGENTS.md](AGENTS.md).

## Запуск

```sh
docker compose up --build     # db + backend (:8000) + frontend (:5173)
```

Demo-данные: `SEED_DEMO=true docker compose up --build`.

## Проверки

```sh
docker compose exec backend pytest          # backend-тесты
docker compose exec backend ruff check .    # линт backend
cd frontend && npm run check && npm run build
cd e2e && npx playwright test               # E2E против поднятого compose
```

## Миграции

```sh
docker compose exec backend alembic upgrade head
```