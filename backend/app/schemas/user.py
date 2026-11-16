from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    role: UserRole


class UserBriefRead(BaseModel):
    """Короткая карточка пользователя для вложенных объектов.

    Используется в ответах, где важен автор/исполнитель (``assignee``,
    ``actor``, ``author``): frontend показывает имя, не запрашивая справочник.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


__all__ = ["UserBriefRead", "UserRead"]