"""Нумерация ``INC-NNN`` не ломается на номерах от 1000 (регрессия DMI-7).

Найденный дефект: ``lpad(nextval(...)::text, 3, '0')`` обрезал номера длиннее
трёх цифр, поэтому ``INC-1000`` превращался в ``INC-100`` и вставка падала с
``duplicate key value violates unique constraint "pk_incidents"``. Тесты
API создают много инцидентов и перешагнули 1000-й номер — без этого теста
дефект возвращался бы молча.

Тест проверяет функцию форматирования напрямую (``format_incident_number``) и
сквозной сценарий: последовательность переведена за 999, инцидент создаётся
через API и получает четырёхзначный номер.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.incident import INCIDENT_NUMBER_SEQUENCE


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (1, "INC-001"),
        (7, "INC-007"),
        (42, "INC-042"),
        (999, "INC-999"),
        (1000, "INC-1000"),
        (1133, "INC-1133"),
        (1234567, "INC-1234567"),
    ],
)
def test_format_incident_number_pads_without_truncating(
    db_session: Session, number: int, expected: str
) -> None:
    formatted = db_session.execute(
        text("SELECT format_incident_number(:number)"), {"number": number}
    ).scalar()

    assert formatted == expected
    assert len(formatted) > 3


def test_create_incident_after_sequence_passes_thousand(
    db_session: Session, client: TestClient, actor_headers: dict[str, str]
) -> None:
    """Сквозной сценарий: номер 1001+ создаётся без конфликта ключа."""
    db_session.execute(
        text("SELECT setval(:seq, 1000, true)"), {"seq": INCIDENT_NUMBER_SEQUENCE}
    )

    response = client.post(
        "/api/incidents",
        json={"title": "Инцидент после тысячи", "category": "Other", "priority": "Low"},
        headers=actor_headers,
    )

    assert response.status_code == 201, response.text
    incident_id = response.json()["id"]
    assert incident_id.startswith("INC-")
    assert int(incident_id.removeprefix("INC-")) >= 1001


def test_two_incidents_after_thousand_have_distinct_numbers(
    db_session: Session, client: TestClient, actor_headers: dict[str, str]
) -> None:
    """Соседние номера за 1000 не схлопываются в один PK."""
    db_session.execute(
        text("SELECT setval(:seq, 1200, true)"), {"seq": INCIDENT_NUMBER_SEQUENCE}
    )

    def create(title: str) -> str:
        response = client.post(
            "/api/incidents",
            json={"title": title, "category": "Other", "priority": "Low"},
            headers=actor_headers,
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    first = create("Первый инцидент после тысячи")
    second = create("Второй инцидент после тысячи")

    assert first != second
    assert int(second.removeprefix("INC-")) == int(first.removeprefix("INC-")) + 1