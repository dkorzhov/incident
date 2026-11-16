"""incidents.id: паддинг номера без обрезания (>= INC-1000)

Дефект миграции ``0002_incidents``: ``lpad(nextval(...)::text, 3, '0')`` не только
дополняет короткие номера нулями, но и **обрезает** длинные до трёх символов.
На 1000-м инциденте ``INC-1000`` превращалось в ``INC-100``, на 1133-м — в
``INC-113``, что давало ``unique violation`` по первичному ключу и полностью
блокировало создание инцидентов (`{operational error}` при вставке).

Решение — форматирование вынесено в функции:

* ``format_incident_number(bigint)`` — IMMUTABLE-функция, одна ответственность;
* ``next_incident_id()`` — VOLATILE-функция, берёт следующий номер и форматирует.

``lpad`` вызывается с длиной ``greatest(3, length(номер))``, поэтому короткие
номера дополняются нулями (``INC-007``), а длинные не обрезаются (``INC-1000``).
Вызов ``nextval`` остаётся ровно один на вставку: значение последовательности
не расходуется дважды.

Revision ID: 0003_incident_number_padding
Revises: 0002_incidents
Create Date: 2026-11-16 21:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_incident_number_padding"
down_revision: str | None = "0002_incidents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NUMBER_SEQUENCE = "incident_number_seq"
FORMAT_FUNCTION = "format_incident_number"
NEXT_ID_FUNCTION = "next_incident_id"

#: Старый DEFAULT из 0002_incidents — нужен для downgrade.
PREVIOUS_DEFAULT = sa.text(f"'INC-' || lpad(nextval('{NUMBER_SEQUENCE}')::text, 3, '0')")


def upgrade() -> None:
    # Форматирование: только паддинг, без обрезания длинных номеров.
    op.execute(
        sa.text(
            f"""
            CREATE FUNCTION {FORMAT_FUNCTION}(number bigint) RETURNS text
            LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
            AS $$
                SELECT 'INC-' || lpad(
                    number::text,
                    greatest(3, length(number::text)),
                    '0'
                )
            $$
            """
        )
    )
    # DEFAULT колонки: одно обращение к последовательности на вставку.
    op.execute(
        sa.text(
            f"""
            CREATE FUNCTION {NEXT_ID_FUNCTION}() RETURNS text
            LANGUAGE sql VOLATILE
            AS $$
                SELECT {FORMAT_FUNCTION}(nextval('{NUMBER_SEQUENCE}'))
            $$
            """
        )
    )
    op.execute(
        sa.text(
            f"ALTER TABLE incidents ALTER COLUMN id SET DEFAULT {NEXT_ID_FUNCTION}()"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE incidents ALTER COLUMN id SET DEFAULT " + str(PREVIOUS_DEFAULT)))
    op.execute(sa.text(f"DROP FUNCTION {NEXT_ID_FUNCTION}()"))
    op.execute(sa.text(f"DROP FUNCTION {FORMAT_FUNCTION}(bigint)"))