from fastapi import APIRouter

from app.config import get_settings
from app.schemas.health import HealthRead

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthRead)
def read_health() -> HealthRead:
    """Liveness-проба сервиса."""
    settings = get_settings()
    return HealthRead(status="ok", service=settings.app_name, version=settings.app_version)