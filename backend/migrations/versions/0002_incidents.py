"""incidents, comments, history_events: домен инцидента (DMI-6)

Номер инцидента ``INC-NNN`` выдаёт последовательность ``incident_number_seq``
через ``server_default`` колонки ``incidents.id``: атомарно и без ``max+1``.
Целостность «было/стало» держится на уровне БД:

* длина строк — не только в сервисе, но и в CHECK (``title`` 5–120,
  ``description`` 0–2000, ``resolution`` 0–2000, ``comments.text`` 1–2000);
* ``resolution`` у ``Resolved`` обязателен — CHECK на связку ``status``/``resolution``.

Revision ID: 0002_incidents
Revises: 0001_users
Create Date: 2026-11-16 16:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_incidents"
down_revision: str | None = "0001_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NUMBER_SEQUENCE = "incident_number_seq"

INCIDENT_CATEGORY = sa.Enum(
    "Network", "Mail", "Portal", "Database", "Workplace", "Other", name="incident_category"
)
INCIDENT_PRIORITY = sa.Enum("Critical", "High", "Medium", "Low", name="incident_priority")
INCIDENT_STATUS = sa.Enum("New", "In Progress", "Resolved", "Closed", name="incident_status")
HISTORY_EVENT_TYPE = sa.Enum(
    "created",
    "assigned",
    "status_changed",
    "priority_changed",
    "commented",
    "resolved",
    "fields_updated",
    name="history_event_type",
)

INCIDENT_ID_DEFAULT = sa.text(
    f"'INC-' || lpad(nextval('{NUMBER_SEQUENCE}')::text, 3, '0')"
)


def upgrade() -> None:
    op.execute(sa.text(f"CREATE SEQUENCE {NUMBER_SEQUENCE} START WITH 1"))

    op.create_table(
        "incidents",
        sa.Column("id", sa.String(length=20), nullable=False, server_default=INCIDENT_ID_DEFAULT),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column(
            "description", sa.String(length=2000), nullable=False, server_default=sa.text("''")
        ),
        sa.Column("category", INCIDENT_CATEGORY, nullable=False),
        sa.Column("priority", INCIDENT_PRIORITY, nullable=False),
        sa.Column(
            "status", INCIDENT_STATUS, nullable=False, server_default=sa.text("'New'")
        ),
        sa.Column("assignee_id", sa.Integer(), nullable=True),
        sa.Column("resolution", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_incidents"),
        sa.ForeignKeyConstraint(
            ["assignee_id"],
            ["users.id"],
            name="fk_incidents_assignee_id_users",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "char_length(btrim(title)) BETWEEN 5 AND 120", name="ck_incidents_title_length"
        ),
        sa.CheckConstraint(
            "char_length(description) <= 2000", name="ck_incidents_description_length"
        ),
        sa.CheckConstraint(
            "resolution IS NULL OR char_length(resolution) BETWEEN 1 AND 2000",
            name="ck_incidents_resolution_length",
        ),
        sa.CheckConstraint(
            "status <> 'Resolved' OR (resolution IS NOT NULL AND btrim(resolution) <> '')",
            name="ck_incidents_resolved_requires_resolution",
        ),
    )
    op.create_index("ix_incidents_created_at", "incidents", ["created_at"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_priority", "incidents", ["priority"])
    op.create_index("ix_incidents_assignee_id", "incidents", ["assignee_id"])

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.String(length=20), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=2000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_comments"),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name="fk_comments_incident_id_incidents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name="fk_comments_author_id_users",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "char_length(btrim(text)) BETWEEN 1 AND 2000", name="ck_comments_text_length"
        ),
    )
    op.create_index("ix_comments_incident_id", "comments", ["incident_id"])
    op.create_index("ix_comments_author_id", "comments", ["author_id"])

    op.create_table(
        "history_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.String(length=20), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("type", HISTORY_EVENT_TYPE, nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_history_events"),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name="fk_history_events_incident_id_incidents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name="fk_history_events_actor_id_users",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_history_events_incident_id", "history_events", ["incident_id"])
    op.create_index("ix_history_events_actor_id", "history_events", ["actor_id"])
    op.create_index(
        "ix_history_events_created_at_id", "history_events", ["created_at", "id"]
    )


def downgrade() -> None:
    op.drop_index("ix_history_events_created_at_id", table_name="history_events")
    op.drop_index("ix_history_events_actor_id", table_name="history_events")
    op.drop_index("ix_history_events_incident_id", table_name="history_events")
    op.drop_table("history_events")

    op.drop_index("ix_comments_author_id", table_name="comments")
    op.drop_index("ix_comments_incident_id", table_name="comments")
    op.drop_table("comments")

    op.drop_index("ix_incidents_assignee_id", table_name="incidents")
    op.drop_index("ix_incidents_priority", table_name="incidents")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_index("ix_incidents_created_at", table_name="incidents")
    op.drop_table("incidents")

    op.execute(sa.text(f"DROP SEQUENCE {NUMBER_SEQUENCE}"))

    bind = op.get_bind()
    for enum_type in (
        HISTORY_EVENT_TYPE,
        INCIDENT_STATUS,
        INCIDENT_PRIORITY,
        INCIDENT_CATEGORY,
    ):
        enum_type.drop(bind, checkfirst=True)