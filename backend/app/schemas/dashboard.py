"""Схемы дашборда (TASK.md §3).

Семантика счётчиков зафиксирована в ``app/services/dashboard.py`` и описана
в полях ниже, чтобы frontend и тесты читали одно и то же определение.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.history import HistoryEventType
from app.models.incident import IncidentPriority
from app.schemas.user import UserBriefRead


class DashboardCountsRead(BaseModel):
    """KPI-карточки дашборда."""

    open: int = Field(description="Все открытые: статус не Closed (включая Resolved)")
    new: int = Field(description="Статус New")
    in_progress: int = Field(description="Статус In Progress")
    critical: int = Field(description="Приоритет Critical и статус не Closed")
    resolved_today: int = Field(
        description=(
            "Инциденты, переведённые в Resolved сегодня (UTC) — по событию истории, "
            "а не по updated_at"
        )
    )


class IncidentRefRead(BaseModel):
    """Ссылка на инцидент для ленты активности."""

    model_config = {"from_attributes": True}

    id: str = Field(examples=["INC-001"])
    title: str


class RecentActivityRead(BaseModel):
    """Последнее событие истории в ленте дашборда."""

    model_config = {"from_attributes": True}

    id: int
    incident_id: str
    incident: IncidentRefRead = Field(description="Инцидент, к которому относится событие")
    actor: UserBriefRead = Field(description="Кто выполнил действие")
    type: HistoryEventType
    payload: dict[str, Any] = Field(description="Изменения вида `{field: {from, to}}`")
    created_at: datetime


class DashboardRead(BaseModel):
    """Ответ ``GET /api/dashboard``."""

    counts: DashboardCountsRead
    by_priority: dict[IncidentPriority, int] = Field(
        description=(
            "Количество инцидентов по приоритетам (включая закрытые, ключи без данных — 0)"
        ),
        examples=[{"Critical": 3, "High": 7, "Medium": 8, "Low": 5}],
    )
    recent_activity: list[RecentActivityRead] = Field(
        description="Последние 10 событий истории, свежие сверху"
    )


__all__ = [
    "DashboardCountsRead",
    "DashboardRead",
    "IncidentRefRead",
    "RecentActivityRead",
]