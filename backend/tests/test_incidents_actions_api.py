"""HTTP-тесты изменяющих операций над инцидентом (TASK.md §2–3, DMI-7).

Каждое бизнес-правило проверяется на сервере: недопустимые переходы → 409,
resolve без resolution → 400, Closed неизменяем → 409 на PATCH/status/comments.
Плюс проверка, что значимые изменения автоматически попадают в историю.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import ACTOR_ID, ASSIGNEE_ID, MANAGER_ID


def _card(client: TestClient, incident_id: str) -> dict:
    response = client.get(f"/api/incidents/{incident_id}")
    assert response.status_code == 200, response.text
    return response.json()


def _history_types(card: dict) -> list[str]:
    return [event["type"] for event in card["history"]]


# --- PATCH /api/incidents/{id} -------------------------------------------


def test_patch_updates_fields_and_records_history(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    incident = make_incident(title="Не работает почта", priority="Low")

    response = client.patch(
        f"/api/incidents/{incident['id']}",
        json={
            "title": "Не работает корпоративная почта",
            "description": "Письма не приходят с 9:00",
            "category": "Portal",
            "priority": "Critical",
        },
        headers=actor_headers,
    )

    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["title"] == "Не работает корпоративная почта"
    assert updated["category"] == "Portal"
    assert updated["priority"] == "Critical"

    card = _card(client, incident["id"])
    assert _history_types(card) == ["created", "priority_changed", "fields_updated"]
    fields_updated = card["history"][-1]
    assert fields_updated["payload"]["title"] == {
        "from": "Не работает почта",
        "to": "Не работает корпоративная почта",
    }
    assert fields_updated["payload"]["category"] == {"from": "Mail", "to": "Portal"}
    priority_event = card["history"][-2]
    assert priority_event["payload"] == {"priority": {"from": "Low", "to": "Critical"}}


def test_patch_partial_update_keeps_other_fields(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    incident = make_incident(
        title="Проблема с VPN", category="Network", priority="Medium", assignee_id=ASSIGNEE_ID
    )

    response = client.patch(
        f"/api/incidents/{incident['id']}",
        json={"priority": "High"},
        headers=actor_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Проблема с VPN"
    assert body["category"] == "Network"
    assert body["assignee_id"] == ASSIGNEE_ID
    assert body["priority"] == "High"


def test_patch_assigns_and_unassigns_with_history(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    incident = make_incident()

    assigned = client.patch(
        f"/api/incidents/{incident['id']}",
        json={"assignee_id": ASSIGNEE_ID},
        headers=actor_headers,
    )
    assert assigned.status_code == 200
    assert assigned.json()["assignee"] == {"id": ASSIGNEE_ID, "name": "Иванов Иван"}

    unassigned = client.patch(
        f"/api/incidents/{incident['id']}",
        json={"assignee_id": None},
        headers=actor_headers,
    )
    assert unassigned.status_code == 200
    assert unassigned.json()["assignee_id"] is None

    card = _card(client, incident["id"])
    assigned_events = [e for e in card["history"] if e["type"] == "assigned"]
    assert len(assigned_events) == 2
    assert assigned_events[0]["payload"]["assignee_id"] == {"from": None, "to": ASSIGNEE_ID}
    assert assigned_events[1]["payload"]["assignee_id"] == {"from": ASSIGNEE_ID, "to": None}


def test_patch_without_actual_changes_writes_no_history(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    incident = make_incident(title="Инцидент без изменений")

    response = client.patch(
        f"/api/incidents/{incident['id']}",
        json={"title": "Инцидент без изменений"},
        headers=actor_headers,
    )

    assert response.status_code == 200
    assert _history_types(_card(client, incident["id"])) == ["created"]


def test_patch_empty_body_returns_incident_unchanged(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    incident = make_incident(title="Инцидент пустого PATCH")

    response = client.patch(
        f"/api/incidents/{incident['id']}", json={}, headers=actor_headers
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Инцидент пустого PATCH"


@pytest.mark.parametrize(
    ("payload", "expected_field"),
    [
        ({"title": "abc"}, "title"),
        ({"title": ""}, "title"),
        ({"category": "Hardware"}, "category"),
        ({"priority": "Urgent"}, "priority"),
        ({"assignee_id": 987654}, "assignee_id"),
        ({"assignee_id": 0}, "assignee_id"),
        ({"description": "d" * 2001}, "description"),
    ],
)
def test_patch_validates_fields(
    client: TestClient,
    make_incident,
    actor_headers: dict[str, str],
    payload: dict,
    expected_field: str,
) -> None:
    incident = make_incident()

    response = client.patch(
        f"/api/incidents/{incident['id']}", json=payload, headers=actor_headers
    )

    assert response.status_code == 400, response.text
    assert expected_field in {error["field"] for error in response.json()["errors"]}


def test_patch_unknown_incident_returns_404(
    client: TestClient, actor_headers: dict[str, str]
) -> None:
    response = client.patch(
        "/api/incidents/INC-999999", json={"title": "Другой заголовок"}, headers=actor_headers
    )

    assert response.status_code == 404
    assert "INC-999999" in response.json()["detail"]


def test_patch_requires_user_header(client: TestClient, make_incident) -> None:
    incident = make_incident()

    response = client.patch(
        f"/api/incidents/{incident['id']}", json={"priority": "Low"}
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "X-User-Id"


def test_patch_closed_incident_returns_409(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    """После Closed инцидент неизменяем (TASK.md §2)."""
    incident = make_incident(status="Closed")

    response = client.patch(
        f"/api/incidents/{incident['id']}",
        json={"title": "Попытка изменить закрытый"},
        headers=actor_headers,
    )

    assert response.status_code == 409
    assert "закрыт" in response.json()["detail"]
    assert _card(client, incident["id"])["title"] == incident["title"]


def test_patch_closed_with_assignee_returns_409(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    incident = make_incident(status="Closed")

    response = client.patch(
        f"/api/incidents/{incident['id']}",
        json={"assignee_id": MANAGER_ID},
        headers=actor_headers,
    )

    assert response.status_code == 409


# --- PATCH /api/incidents/{id}/status ------------------------------------


def test_status_happy_path_new_to_closed(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    """Полный цикл: New → In Progress → Resolved → Closed."""
    incident = make_incident()

    in_progress = client.patch(
        f"/api/incidents/{incident['id']}/status",
        json={"status": "In Progress"},
        headers=actor_headers,
    )
    assert in_progress.status_code == 200, in_progress.text
    assert in_progress.json()["status"] == "In Progress"

    resolved = client.patch(
        f"/api/incidents/{incident['id']}/status",
        json={"status": "Resolved", "resolution": "Перезапущен почтовый шлюз"},
        headers=actor_headers,
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "Resolved"
    assert resolved.json()["resolution"] == "Перезапущен почтовый шлюз"

    closed = client.patch(
        f"/api/incidents/{incident['id']}/status",
        json={"status": "Closed"},
        headers=actor_headers,
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "Closed"

    card = _card(client, incident["id"])
    assert _history_types(card) == [
        "created",
        "status_changed",
        "resolved",
        "status_changed",
    ]
    assert card["allowed_transitions"] == []


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("New", "Closed"),
        ("New", "Resolved"),
        ("In Progress", "Closed"),
        ("In Progress", "New"),
        ("Resolved", "In Progress"),
        ("Resolved", "New"),
    ],
)
def test_status_invalid_transition_returns_409(
    client: TestClient,
    make_incident,
    actor_headers: dict[str, str],
    current: str,
    target: str,
) -> None:
    """Закрыть из New/In Progress нельзя, прочие переходы — тоже 409 (TASK.md §2)."""
    incident = make_incident(status=current)

    response = client.patch(
        f"/api/incidents/{incident['id']}/status",
        json={"status": target, "resolution": "Решение на всякий случай"},
        headers=actor_headers,
    )

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert current in detail
    assert target in detail
    assert _card(client, incident["id"])["status"] == current


def test_status_same_status_returns_409(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    incident = make_incident()

    response = client.patch(
        f"/api/incidents/{incident['id']}/status",
        json={"status": "New"},
        headers=actor_headers,
    )

    assert response.status_code == 409


@pytest.mark.parametrize("resolution", [None, "", "   "])
def test_resolve_without_resolution_returns_400(
    client: TestClient,
    make_incident,
    actor_headers: dict[str, str],
    resolution: str | None,
) -> None:
    """Resolved без непустого resolution — 400 с указанием поля."""
    incident = make_incident(status="In Progress")
    body = {"status": "Resolved"}
    if resolution is not None:
        body["resolution"] = resolution

    response = client.patch(
        f"/api/incidents/{incident['id']}/status", json=body, headers=actor_headers
    )

    assert response.status_code == 400, response.text
    assert response.json()["errors"][0]["field"] == "resolution"
    assert _card(client, incident["id"])["status"] == "In Progress"


def test_resolve_rejects_too_long_resolution(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    incident = make_incident(status="In Progress")

    response = client.patch(
        f"/api/incidents/{incident['id']}/status",
        json={"status": "Resolved", "resolution": "r" * 2001},
        headers=actor_headers,
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "resolution"


def test_status_rejects_unknown_status_value(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    incident = make_incident()

    response = client.patch(
        f"/api/incidents/{incident['id']}/status",
        json={"status": "Done"},
        headers=actor_headers,
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "status"


def test_status_closed_incident_returns_409(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    incident = make_incident(status="Closed")

    for target in ("New", "In Progress", "Resolved", "Closed"):
        response = client.patch(
            f"/api/incidents/{incident['id']}/status",
            json={"status": target},
            headers=actor_headers,
        )
        assert response.status_code == 409, (target, response.text)


def test_status_unknown_incident_returns_404(
    client: TestClient, actor_headers: dict[str, str]
) -> None:
    response = client.patch(
        "/api/incidents/INC-777777/status",
        json={"status": "In Progress"},
        headers=actor_headers,
    )

    assert response.status_code == 404


def test_status_requires_user_header(client: TestClient, make_incident) -> None:
    incident = make_incident()

    response = client.patch(
        f"/api/incidents/{incident['id']}/status", json={"status": "In Progress"}
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "X-User-Id"


# --- POST /api/incidents/{id}/comments -----------------------------------


def test_add_comment_returns_201_and_author(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    incident = make_incident()

    response = client.post(
        f"/api/incidents/{incident['id']}/comments",
        json={"text": "  Уточните, пожалуйста, время события  "},
        headers=actor_headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["text"] == "Уточните, пожалуйста, время события"
    assert body["author_id"] == ACTOR_ID
    assert body["author"] == {"id": ACTOR_ID, "name": "Иван Петров"}
    assert body["incident_id"] == incident["id"]


def test_add_comment_uses_current_user_as_author(
    client: TestClient, make_incident
) -> None:
    """Автор — тот, кто указан в X-User-Id, а не константа."""
    incident = make_incident()

    response = client.post(
        f"/api/incidents/{incident['id']}/comments",
        json={"text": "Комментарий менеджера"},
        headers={"X-User-Id": str(MANAGER_ID)},
    )

    assert response.status_code == 201
    assert response.json()["author_id"] == MANAGER_ID


def test_add_comment_records_history(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    incident = make_incident()
    comment = client.post(
        f"/api/incidents/{incident['id']}/comments",
        json={"text": "Проверяю журналы"},
        headers=actor_headers,
    ).json()

    card = _card(client, incident["id"])

    commented = card["history"][-1]
    assert commented["type"] == "commented"
    assert commented["payload"]["comment_id"] == {"from": None, "to": comment["id"]}
    assert commented["payload"]["text"]["to"] == "Проверяю журналы"


@pytest.mark.parametrize("text", ["", "   ", "x" * 2001])
def test_add_comment_validates_text(
    client: TestClient, make_incident, actor_headers: dict[str, str], text: str
) -> None:
    incident = make_incident()

    response = client.post(
        f"/api/incidents/{incident['id']}/comments", json={"text": text}, headers=actor_headers
    )

    assert response.status_code == 400, response.text
    assert response.json()["errors"][0]["field"] == "text"


def test_add_comment_requires_user_header(client: TestClient, make_incident) -> None:
    incident = make_incident()

    response = client.post(
        f"/api/incidents/{incident['id']}/comments", json={"text": "Без автора"}
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "X-User-Id"


def test_add_comment_to_closed_incident_returns_409(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    incident = make_incident(status="Closed")

    response = client.post(
        f"/api/incidents/{incident['id']}/comments",
        json={"text": "Ещё вопрос"},
        headers=actor_headers,
    )

    assert response.status_code == 409
    assert "закрыт" in response.json()["detail"]
    assert _card(client, incident["id"])["comments"] == []


def test_add_comment_unknown_incident_returns_404(
    client: TestClient, actor_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/incidents/INC-555555/comments",
        json={"text": "Комментарий в никуда"},
        headers=actor_headers,
    )

    assert response.status_code == 404