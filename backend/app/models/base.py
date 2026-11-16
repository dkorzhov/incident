from enum import Enum as PyEnum

from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс всех ORM-моделей."""


def enum_column(enum_cls: type[PyEnum], *, name: str) -> SAEnum:
    """Колонка PostgreSQL-перечисления по *значениям* членов Python-enum.

    В БД и в API живут значения (``"In Progress"``, ``"Network"``), имена
    членов enum остаются деталью реализации.
    """
    return SAEnum(enum_cls, name=name, values_callable=lambda cls: [m.value for m in cls])
