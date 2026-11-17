"""Маркер применения demo-seed (DMI-10, TASK.md §6).

Seed выполняется на старте backend, поэтому повторный старт не должен
задваивать данные. Маркером выбрана **отдельная таблица**, а не признак
«в БД есть инцидент с таким-то title»:

* содержимое инцидентов принадлежит пользователю — title можно отредактировать
  через UI (``PATCH /api/incidents/{id}``), и seed по title-признаку создал бы
  дубли на следующем старте;
* строка маркера пишется только сидом и не меняется действиями пользователя,
  поэтому идемпотентность не зависит от того, что стало с демо-инцидентами;
* ``applied_at`` даёт оператору ответ на вопрос «когда демо-данные появились».

Ключ (``key``) версионирован: новый набор демо-данных можно залить поверх
старого, не переписывая историю миграциями.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DemoSeedState(Base):
    """Одна строка на применённый набор демо-данных."""

    __tablename__ = "demo_seed_state"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )