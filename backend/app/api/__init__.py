from fastapi import APIRouter

from app.api import dashboard, health, incidents, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(users.router)
api_router.include_router(incidents.router)
api_router.include_router(dashboard.router)

__all__ = ["api_router"]