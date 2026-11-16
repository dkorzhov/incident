"""Общие FastAPI-зависимости.

Текущий пользователь MVP приходит заголовком ``X-User-Id`` и валидируется
против справочника ``users``: упрощение вместо аутентификации (концепция, §6).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.db import get_db
from app.domain.errors import ValidationError
from app.models.user import User

USER_ID_HEADER = "X-User-Id"


def get_current_user(
    x_user_id: Annotated[str | None, Header(alias=USER_ID_HEADER)] = None,
    db: Session = Depends(get_db),
) -> User:
    """Текущий пользователь из заголовка ``X-User-Id``.

    400 — заголовок отсутствует, не является целым числом или указывает на
    неизвестного пользователя. Зависимость переиспользуется всеми роутами,
    которым нужен автор изменения (инциденты, комментарии — DMI-7).
    """
    if x_user_id is None or not x_user_id.strip():
        raise ValidationError.for_field(
            USER_ID_HEADER, "обязательный заголовок: укажите id текущего пользователя"
        )
    raw = x_user_id.strip()
    try:
        user_id = int(raw)
    except ValueError:
        raise ValidationError.for_field(
            USER_ID_HEADER, f"ожидается целое число, получено {raw!r}"
        ) from None
    if user_id <= 0:
        raise ValidationError.for_field(USER_ID_HEADER, "ожидается положительное число")

    user = db.get(User, user_id)
    if user is None:
        raise ValidationError.for_field(USER_ID_HEADER, f"пользователь {user_id} не найден")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]

__all__ = ["USER_ID_HEADER", "CurrentUser", "DbSession", "get_current_user"]