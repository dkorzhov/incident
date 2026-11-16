"""HTTP-тесты реестра и карточки инцидентов (TASK.md §3, DMI-7).

Проверяем контракт, который использует frontend: snake_case, коды 200/201/400/404,
поиск/фильтры/сортировку и наличие комментариев с историей в карточке.
Бизнес-правила (автомат, неизменяемость Closed) — в ``test_incidents_actions_api``.

Сверки идут относительно данных, найденных по ID/фильтру, поэтому тесты не
зависят от строк, которые уже лежат в БД (demo-seed при ``SEED_DEMO=true``).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import ACTOR_ID, ASSIGNEE_ID


def _listed_ids(client: TestClient, **params: str) -> list[str]:
    response = client.get("/api/incidents", params=params)
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()]


# --- реестр: GET /api/incidents -------------------------------------------


def test_list_incidents_returns_array(client: TestClient) -> None:
    response = client.get("/api/incidents")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_incidents_returns_created_incident(
    client: TestClient, make_incident
) -> None:
    incident = make_incident(
        title="Не открывается портал",
        category="Portal",
        priority="Critical",
        assignee_id=ASSIGNEE_ID,
    )

    response = client.get("/api/incidents")

    assert response.status_code == 200
    item = next(entry for entry in response.json() if entry["id"] == incident["id"])
    assert item["title"] == "Не открывается портал"
    assert item["category"] == "Portal"
    assert item["priority"] == "Critical"
    assert item["status"] == "New"
    assert item["assignee_id"] == ASSIGNEE_ID
    assert item["assignee"] == {"id": ASSIGNEE_ID, "name": "Иванов Иван"}
    assert item["created_at"] and item["updated_at"]
    # контракт — snake_case без вложенных DTO-обёрток
    assert set(item) >= {
        "id",
        "title",
        "description",
        "category",
        "priority",
        "status",
        "assignee_id",
        "assignee",
        "resolution",
        "created_at",
        "updated_at",
    }


def test_list_incidents_does_not_require_user_header(client: TestClient) -> None:
    """Реестр — чтение: X-User-Id не обязателен."""
    response = client.get("/api/incidents")

    assert response.status_code == 200


def test_list_incidents_sorts_by_created_at_desc(
    client: TestClient, make_incident
) -> None:
    marker = "сортировкареестра"
    first = make_incident(title=f"Первый инцидент {marker}")
    second = make_incident(title=f"Второй инцидент {marker}")

    ids = _listed_ids(client, q=marker)

    assert ids == [second["id"], first["id"]]


def test_list_incidents_sorts_all_by_created_at_desc(client: TestClient) -> None:
    """Без фильтров реестр тоже упорядочен: свежие сверху."""
    incidents = client.get("/api/incidents").json()

    timestamps = [item["created_at"] for item in incidents]
    assert timestamps == sorted(timestamps, reverse=True)


def test_list_incidents_searches_by_id(client: TestClient, make_incident) -> None:
    target = make_incident(title="Не открывается портал")
    make_incident(title="Не работает почта")

    assert _listed_ids(client, q=target["id"].lower()) == [target["id"]]


def test_list_incidents_searches_by_title_case_insensitive(
    client: TestClient, make_incident
) -> None:
    marker = "портал7д"
    target = make_incident(title=f"Не открывается {marker}")
    make_incident(title="Не работает почта")

    assert _listed_ids(client, q=marker.upper()) == [target["id"]]


def test_list_incidents_filters_by_status(client: TestClient, make_incident) -> None:
    marker = "фильтрстатуса"
    new_id = make_incident(title=f"Новый инцидент {marker}")["id"]
    in_progress_id = make_incident(title=f"Инцидент в работе {marker}", status="In Progress")[
        "id"
    ]

    listed = _listed_ids(client, q=marker, status="In Progress")

    assert listed == [in_progress_id]
    assert new_id not in listed


def test_list_incidents_filters_by_priority(client: TestClient, make_incident) -> None:
    marker = "фильтрприоритета"
    critical_id = make_incident(title=f"Критичный инцидент {marker}", priority="Critical")["id"]
    make_incident(title=f"Некритичный инцидент {marker}", priority="Low")

    assert _listed_ids(client, q=marker, priority="Critical") == [critical_id]


def test_list_incidents_combines_search_and_filters(
    client: TestClient, make_incident
) -> None:
    """q + status + priority сужают выборку вместе, а не по отдельности."""
    marker = "комбифильтр"
    target = make_incident(
        title=f"Портал недоступен {marker}", status="In Progress", priority="Critical"
    )
    make_incident(title=f"Портал медленный {marker}", status="In Progress", priority="Low")
    make_incident(title=f"Почта недоступна {marker}", priority="Critical")

    # q=marker — все три строки теста; добавление фильтров оставляет одну
    assert len(_listed_ids(client, q=marker)) == 3

    listed = _listed_ids(client, q=marker, status="In Progress", priority="Critical")

    assert listed == [target["id"]]


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"status": "Opened"}, "status"),
        ({"priority": "Urgent"}, "priority"),
        ({"status": ""}, None),  # пустой фильтр = без фильтра
    ],
)
def test_list_incidents_validates_filter_values(
    client: TestClient, params: dict[str, str], field: str | None
) -> None:
    response = client.get("/api/incidents", params=params)

    if field is None:
        assert response.status_code == 200
        return
    assert response.status_code == 400, response.text
    body = response.json()
    assert body["errors"][0]["field"] == field
    assert "допустимые значения" in body["errors"][0]["reason"]


# --- создание: POST /api/incidents ---------------------------------------


def test_create_incident_returns_201_and_generated_number(
    client: TestClient, actor_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/incidents",
        json={
            "title": "Не работает VPN",
            "description": "Подключение обрывается",
            "category": "Network",
            "priority": "Medium",
            "assignee_id": ASSIGNEE_ID,
        },
        headers=actor_headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"].startswith("INC-")
    assert body["status"] == "New"
    assert body["resolution"] is None
    assert body["assignee_id"] == ASSIGNEE_ID


def test_create_incident_numbers_are_sequential(
    client: TestClient, actor_headers: dict[str, str]
) -> None:
    def create(title: str) -> str:
        response = client.post(
            "/api/incidents",
            json={"title": title, "category": "Mail", "priority": "Low"},
            headers=actor_headers,
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    first = create("Первая проблема последовательности")
    second = create("Вторая проблема последовательности")

    assert int(second.removeprefix("INC-")) == int(first.removeprefix("INC-")) + 1


def test_create_incident_without_optional_fields(
    client: TestClient, actor_headers: dict[str, str]
) -> None:
    """description и assignee_id необязательны: описание пустое, ответственного нет."""
    response = client.post(
        "/api/incidents",
        json={"title": "Проблема без деталей", "category": "Other", "priority": "Low"},
        headers=actor_headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["description"] == ""
    assert body["assignee_id"] is None
    assert body["assignee"] is None


@pytest.mark.parametrize(
    ("payload", "expected_field"),
    [
        ({"title": "abc", "category": "Mail", "priority": "High"}, "title"),
        ({"title": "x" * 121, "category": "Mail", "priority": "High"}, "title"),
        ({"category": "Mail", "priority": "High"}, "title"),
        ({"title": "Норм заголовок", "category": "Hardware", "priority": "High"}, "category"),
        ({"title": "Норм заголовок", "category": "Mail", "priority": "Urgent"}, "priority"),
        ({"title": "Норм заголовок", "priority": "High"}, "category"),
        (
            {
                "title": "Норм заголовок",
                "category": "Mail",
                "priority": "High",
                "assignee_id": 987654,
            },
            "assignee_id",
        ),
    ],
)
def test_create_incident_validates_fields(
    client: TestClient,
    actor_headers: dict[str, str],
    payload: dict,
    expected_field: str,
) -> None:
    """Валидация — 400 с указанием поля и причины (TASK.md §2)."""
    response = client.post("/api/incidents", json=payload, headers=actor_headers)

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["detail"]
    assert expected_field in {error["field"] for error in body["errors"]}


def test_create_incident_reports_all_domain_errors_at_once(
    client: TestClient, actor_headers: dict[str, str]
) -> None:
    """Домен копит ошибки полей: все причины в одном ответе, а не первая.

    Существование `assignee_id` домен проверяет после валидации полей (нужен
    запрос в БД), поэтому здесь — только проверки без обращения к БД.
    """
    response = client.post(
        "/api/incidents",
        json={
            "title": "abc",
            "description": "d" * 2001,
            "category": "Mail",
            "priority": "High",
        },
        headers=actor_headers,
    )

    assert response.status_code == 400, response.text
    assert {error["field"] for error in response.json()["errors"]} == {
        "title",
        "description",
    }


def test_create_incident_rejects_unknown_enum_values_in_schema(
    client: TestClient, actor_headers: dict[str, str]
) -> None:
    """Неизвестные enum ловит схема запроса: тоже 400 и список полей."""
    response = client.post(
        "/api/incidents",
        json={"title": "Норм заголовок", "category": "Nope", "priority": "Nope"},
        headers=actor_headers,
    )

    assert response.status_code == 400, response.text
    body = response.json()
    assert {error["field"] for error in body["errors"]} == {"category", "priority"}
    assert "допустимые значения" in body["errors"][0]["reason"]


def test_create_incident_rejects_too_long_description(
    client: TestClient, actor_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/incidents",
        json={
            "title": "Проблема с описанием",
            "description": "d" * 2001,
            "category": "Mail",
            "priority": "High",
        },
        headers=actor_headers,
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "description"


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-User-Id": ""},
        {"X-User-Id": "abc"},
        {"X-User-Id": "0"},
        {"X-User-Id": "987654"},
    ],
)
def test_create_incident_requires_valid_user(
    client: TestClient, headers: dict[str, str]
) -> None:
    """X-User-Id обязателен и валидируется против users (400)."""
    response = client.post(
        "/api/incidents",
        json={"title": "Проблема без пользователя", "category": "Mail", "priority": "High"},
        headers=headers,
    )

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["errors"][0]["field"] == "X-User-Id"


def test_create_incident_writes_created_history(
    client: TestClient, actor_headers: dict[str, str]
) -> None:
    """Создание автоматически пишет событие `created` с «было/стало»."""
    created = client.post(
        "/api/incidents",
        json={"title": "Инцидент с историей", "category": "Mail", "priority": "High"},
        headers=actor_headers,
    ).json()

    card = client.get(f"/api/incidents/{created['id']}").json()

    assert [event["type"] for event in card["history"]] == ["created"]
    event = card["history"][0]
    assert event["actor_id"] == ACTOR_ID
    assert event["actor"] == {"id": ACTOR_ID, "name": "Иван Петров"}
    assert event["payload"]["status"] == {"from": None, "to": "New"}
    assert event["payload"]["priority"] == {"from": None, "to": "High"}


# --- карточка: GET /api/incidents/{id} -----------------------------------


def test_get_incident_returns_comments_and_history(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    incident = make_incident(title="Инцидент для карточки")

    client.post(
        f"/api/incidents/{incident['id']}/comments",
        json={"text": "Проверяю настройки"},
        headers=actor_headers,
    )

    response = client.get(f"/api/incidents/{incident['id']}")

    assert response.status_code == 200
    card = response.json()
    assert card["id"] == incident["id"]
    assert len(card["comments"]) == 1
    comment = card["comments"][0]
    assert comment["text"] == "Проверяю настройки"
    assert comment["author_id"] == ACTOR_ID
    assert comment["author"] == {"id": ACTOR_ID, "name": "Иван Петров"}
    assert [event["type"] for event in card["history"]] == ["created", "commented"]


def test_get_incident_returns_allowed_transitions(
    client: TestClient, make_incident
) -> None:
    """UI берёт кнопки действий из `allowed_transitions`, а не дублирует автомат."""
    new = make_incident(title="Новый инцидент переходов")
    in_progress = make_incident(title="Инцидент в работе", status="In Progress")
    resolved = make_incident(title="Решённый инцидент", status="Resolved")
    closed = make_incident(title="Закрытый инцидент", status="Closed")

    def transitions(incident_id: str) -> list[str]:
        return client.get(f"/api/incidents/{incident_id}").json()["allowed_transitions"]

    assert transitions(new["id"]) == ["In Progress"]
    assert transitions(in_progress["id"]) == ["Resolved"]
    assert transitions(resolved["id"]) == ["Closed"]
    assert transitions(closed["id"]) == []


def test_get_incident_returns_empty_comments_list(
    client: TestClient, make_incident
) -> None:
    incident = make_incident()

    card = client.get(f"/api/incidents/{incident['id']}").json()

    assert card["comments"] == []


def test_get_unknown_incident_returns_404(client: TestClient) -> None:
    response = client.get("/api/incidents/INC-999999")

    assert response.status_code == 404
    assert "INC-999999" in response.json()["detail"]