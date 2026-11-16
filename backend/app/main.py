from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.api.errors import register_error_handlers
from app.api.openapi import build_openapi_schema
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Точка расширения для стартовых задач (demo-seed появится отдельным тикетом).
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