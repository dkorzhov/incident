# Incident Tracker Lite

Мини-система учёта ИТ-инцидентов с SLA: создание, назначение ответственного,
конечный автомат статусов, дедлайны по severity, REST API + SPA.

Полное ТЗ — [TASK.md](TASK.md). Правила для агентов — [AGENTS.md](AGENTS.md).

## Запуск

```sh
npm ci
npm run dev        # backend :3000 + frontend :5173
```

## Проверки

```sh
npm run check      # Biome + typecheck
npm test           # unit + HTTP тесты
npm run test:e2e   # Playwright smoke
```