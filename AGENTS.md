# AGENTS.md — Incident Tracker Lite

Мини-система учёта ИТ-инцидентов с SLA. **Источник истины по требованиям — `TASK.md`.**
Не расширяй скоуп: разделы 5 (что НЕ входит) и 6 (стретчи) обязательны к соблюдению.

## Стек (зафиксирован)

- Монорепо на npm workspaces: `backend/`, `frontend/`. TypeScript strict везде.
- Backend: **Fastify 5 + better-sqlite3** (SQLite-файл, в тестах — in-memory). Без аутентификации.
- Frontend: **React + Vite**, обычный CSS без дизайн-фреймворков. Только реальный API, без моков.
- Тесты: **Vitest** (unit + HTTP через `fastify.inject`), **Playwright** (один smoke-сценарий).
- Линт/формат: **Biome** (единый инструмент, конфиг в корне).

## Команды (запускать из корня)

| Команда | Что делает |
|---|---|
| `npm ci` | установка зависимостей |
| `npm run check` | Biome + typecheck (`tsc -b`) |
| `npm test` | все unit/HTTP тесты (Vitest) |
| `npm run build` | сборка backend + frontend |
| `npm run dev` | backend (:3000) + frontend (:5173) одновременно |
| `npm run test:e2e` | Playwright smoke (поднимает серверы сам) |

## Правила работы

1. **Одна задача Linear = одна ветка = один PR.** Ветка: `feat/DMI-<номер>-<slug>`.
2. Прямые пуши в `main` запрещены. PR создаётся через `gh pr create`, мержит человек.
3. Коммиты — conventional commits (`feat:`, `fix:`, `test:`, `chore:`).
4. Перед завершением задачи ОБЯЗАТЕЛЬНО прогнать локально: `npm run check && npm test && npm run build`. Зелёный CI — условие готовности.
5. Валидация, автомат статусов и SLA — по `TASK.md` §1–2. Недопустимый переход статуса → 409. `is_overdue` вычисляется на лету, не хранится.
6. Каждый эндпоинт покрыт тестами (минимумы — в `TASK.md` §2). Не удаляй и не ослабляй существующие тесты ради «зелёного» прогона.
7. Ошибки API — 400 с описанием полей; фронтенд показывает их понятным текстом, сетевые ошибки не глотает.
8. Секреты и `.env` не коммитить. Прод-ключей в окружении нет и не должно быть.

## Структура

```
backend/    src/ (routes, domain, storage), test/
frontend/   src/ (components, api), e2e/
TASK.md     полное ТЗ
```

## Линейные ссылки

- Команда Linear: `DMI`. Проект: Incident Tracker Lite.
- В описании PR указывай идентификатор тикета (DMI-NNN) — интеграция GitHub↔Linear свяжет их автоматически.