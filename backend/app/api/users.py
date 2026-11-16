from collections.abc import Sequence

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(tags=["users"])


@router.get("/users", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)) -> Sequence[User]:
    """Список сотрудников ИТ-команды."""
    return db.scalars(select(User).order_by(User.id)).all()