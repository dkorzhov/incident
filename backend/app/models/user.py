from enum import StrEnum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, enum_column


class UserRole(StrEnum):
    engineer = "engineer"
    manager = "manager"


class User(Base):
    """Предзагруженный сотрудник ИТ-команды (текущий пользователь MVP)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole, name="user_role"), nullable=False)
