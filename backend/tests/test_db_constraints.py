"""Ограничения целостности в БД — последний рубеж после сервисной валидации.

Сервисы возвращают 400 раньше, но инварианты не должны опираться только
на Python: SQL-скрипт или будущий сервис не обойдут CHECK.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session


def _insert_incident(db_session: Session, **overrides: object) -> None:
    values = {
        "title": "Корректный заголовок",
        "description": "",
        "category": "Mail",
        "priority": "High",
        "status": "New",
        "resolution": None,
    } | overrides
    db_session.execute(
        text(
            """
            INSERT INTO incidents (title, description, category, priority, status, resolution)
            VALUES (:title, :description, :category, :priority, :status, :resolution)
            """
        ),
        values,
    )
    db_session.flush()


@pytest.mark.parametrize("title", ["abcd", "x" * 121])
def test_title_length_is_enforced_by_database(db_session: Session, title: str) -> None:
    with pytest.raises((IntegrityError, DBAPIError)):
        _insert_incident(db_session, title=title)


def test_description_longer_than_limit_is_rejected(db_session: Session) -> None:
    with pytest.raises((IntegrityError, DBAPIError)):
        _insert_incident(db_session, description="d" * 2001)


def test_resolved_without_resolution_is_rejected(db_session: Session) -> None:
    with pytest.raises((IntegrityError, DBAPIError)):
        _insert_incident(db_session, status="Resolved")


def test_resolved_with_blank_resolution_is_rejected(db_session: Session) -> None:
    with pytest.raises((IntegrityError, DBAPIError)):
        _insert_incident(db_session, status="Resolved", resolution="   ")


def test_resolved_with_resolution_is_allowed(db_session: Session) -> None:
    _insert_incident(db_session, status="Resolved", resolution="Перезапущен шлюз")

    count = db_session.execute(
        text("SELECT count(*) FROM incidents WHERE status = 'Resolved'")
    ).scalar()
    assert count == 1


def test_blank_comment_text_is_rejected(db_session: Session) -> None:
    _insert_incident(db_session)
    with pytest.raises((IntegrityError, DBAPIError)):
        db_session.execute(
            text(
                """
                INSERT INTO comments (incident_id, author_id, text)
                SELECT id, (SELECT min(id) FROM users), '   ' FROM incidents LIMIT 1
                """
            )
        )
        db_session.flush()


def test_incident_number_is_sequential(db_session: Session) -> None:
    _insert_incident(db_session, title="Первый номер подряд")
    _insert_incident(db_session, title="Второй номер подряд")

    ids = db_session.execute(
        text("SELECT id FROM incidents ORDER BY id DESC LIMIT 2")
    ).scalars().all()
    first, second = sorted(ids)
    assert first.startswith("INC-")
    assert int(second.removeprefix("INC-")) == int(first.removeprefix("INC-")) + 1