"""users: предзагруженный список сотрудников (справочные данные MVP)

Revision ID: 0001_users
Revises:
Create Date: 2026-11-16 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_users"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USER_ROLE = sa.Enum("engineer", "manager", name="user_role")

SEED_USERS = [
    ("Иван Петров", "engineer"),
    ("Иванов Иван", "engineer"),
    ("Сидорова Анна", "manager"),
    ("Кузнецов Олег", "engineer"),
    ("Смирнова Мария", "manager"),
]


def upgrade() -> None:
    users = op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("role", USER_ROLE, nullable=False),
        sa.UniqueConstraint("name", name="uq_users_name"),
    )
    op.bulk_insert(
        users,
        [{"name": name, "role": role} for name, role in SEED_USERS],
    )


def downgrade() -> None:
    op.drop_table("users")
    USER_ROLE.drop(op.get_bind(), checkfirst=True)