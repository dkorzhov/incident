from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.api.errors import register_error_handlers
from app.api.openapi import build_openapi_schema
from app.config import Settings, get_settings
from app.services import seed


def _run_demo_seed(settings: Settings) -> None:
    """Демо-данные на старте (TASK.md §6); выключено без ``SEED_DEMO=true``."""
    if not settings.seed_demo:
        return

    created = seed.seed_demo_on_startup()
    # print, как в entrypoint: uvicorn не настраивает root-logger, поэтому
    # `logger.info` из `app.*` в `docker compose logs` не виден, а строка
    # «создал/не создал демо-данные» нужна оператору при первом запуске.
    if created:
        print(f"SEED_DEMO: создано демо-инцидентов — {created}", flush=True)
    else:
        print("SEED_DEMO: демо-данные уже применены или недоступны", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Стартовые задачи приложения.

    Единственная задача — демо-данные при ``SEED_DEMO=true``. Seed
    идемпотентен (маркер в ``demo_seed_state``) и не выполняется под pytest,
    поэтому ``TestClient`` в тестах не пишет в тестовую БД.
    """
    _run_demo_seed(get_settings())
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")
    register_error_handlers(app)

    # Схема документирует только те коды, которые API реально возвращает (400, не 422).
    app.openapi = lambda: build_openapi_schema(app)  # type: ignore[method-assign]
    return app


app = create_app()