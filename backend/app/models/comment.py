"""Комментарий к инциденту (TASK.md §1)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Final

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.user import User

if TYPE_CHECKING:
    from app.models.incident import Incident

COMMENT_TEXT_MIN_LENGTH: Final = 1
COMMENT_TEXT_MAX_LENGTH: Final = 2000


class Comment(Base):
    """Комментарий сотрудника в карточке инцидента."""

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[str] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(String(COMMENT_TEXT_MAX_LENGTH), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    incident: Mapped[Incident] = relationship("Incident", back_populates="comments")
    author: Mapped[User] = relationship(User)

    __table_args__ = (
        # Страховка БД: пробельная строка не пройдёт (сервис отдаёт 400 раньше).
        CheckConstraint(
            "char_length(btrim(text)) BETWEEN 1 AND 2000", name="ck_comments_text_length"
        ),
    )