"""Сервисы приложения: операции над моделями и запись истории.

Сервисы принимают SQLAlchemy-сессию и доменные DTO, сами коммитят транзакцию и
поднимают доменные исключения. HTTP-слой (DMI-7) их только вызывает.
"""

from app.services import history, incidents, seed

__all__ = ["history", "incidents", "seed"]