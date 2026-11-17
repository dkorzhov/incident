from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения (читаются из окружения и `.env`)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "IT Incident Tracker API"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+psycopg://incident:incident@localhost:5432/incident"
    # Отдельная БД для тестов; по умолчанию — основная.
    test_database_url: str | None = None
    # Origin'ы через запятую — для запуска фронтенда без прокси.
    cors_origins: str = "http://localhost:5173"
    # Демо-инциденты на старте (TASK.md §6). По умолчанию выключено: обычный
    # запуск и тесты не должны получать данные, которых не просили.
    seed_demo: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def database_url_for_tests(self) -> str:
        return self.test_database_url or self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()