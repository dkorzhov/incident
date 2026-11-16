"""Роуты дашборда (TASK.md §3).

Ответ агрегированный и считается в SQL (``app/services/dashboard.py``), поэтому
показатели дашборда всегда сходятся с реестром: одни и те же таблицы, без
кеша и без фильтрации в Python.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.dashboard import DashboardCountsRead, DashboardRead, RecentActivityRead
from app.services import dashboard as dashboard_service

router = APIRouter(tags=["dashboard"])


@router.get(
    "/dashboard",
    response_model=DashboardRead,
    summary="Показатели дашборда",
)
def read_dashboard(db: DbSession) -> DashboardRead:
    """KPI, разрез по приоритетам и последние 10 событий истории."""
    data = dashboard_service.build_dashboard(db)
    return DashboardRead(
        counts=DashboardCountsRead(
            open=data.counts.open,
            new=data.counts.new,
            in_progress=data.counts.in_progress,
            critical=data.counts.critical,
            resolved_today=data.counts.resolved_today,
        ),
        by_priority=data.by_priority,
        recent_activity=[
            RecentActivityRead.model_validate(event) for event in data.recent_activity
        ],
    )


__all__ = ["router"]