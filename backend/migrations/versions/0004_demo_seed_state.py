"""demo_seed_state: маркер идемпотентности demo-seed (DMI-10)

Таблица хранит одну строку на применённый набор демо-данных. Seed на старте
backend вставляет ключ через ``INSERT ... ON CONFLICT DO NOTHING`` и создаёт
инциденты только если строка действительно вставлена — так повторный старт
(и параллельный старт двух процессов) не задваивает данные.

Почему не признак по title: title демо-инцидента можно изменить через UI,
и seed, ориентирующийся на него, создал бы дубли. Подробности — в
``app/models/demo_seed.py`` и ``app/services/seed.py``.

Revision ID: 0004_demo_seed_state
Revises: 0003_incident_number_padding
Create Date: 2026-11-17 12:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_demo_seed_state"
down_revision: str | None = "0003_incident_number_padding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "demo_seed_state",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("demo_seed_state")