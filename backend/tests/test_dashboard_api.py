"""HTTP-тесты дашборда (TASK.md §3, DMI-7).

Главное требование — **сходимость с БД**: каждый счётчик сверяется с прямым
SQL-запросом, а не с ожидаемым числом «на глаз». Сверка идёт по приросту
(``after - before``), поэтому тест не зависит от того, были ли в БД строки
до него, и одновременно доказывает, что API считает ровно то же, что SQL.

Отдельно проверяется семантика ``resolved_today``: считается по событию
перехода в Resolved (история), а не по ``updated_at``.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models.history import HistoryEvent, HistoryEventType
from app.models.incident import Incident, IncidentPriority, IncidentStatus
from app.services.dashboard import RECENT_ACTIVITY_LIMIT


def _utc_day_bounds() -> tuple[datetime, datetime]:
    start = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)
    return start, start + timedelta(days=1)


def _db_resolved_today(db: Session) -> int:
    """Эталон «решено сегодня»: переходы в Resolved по истории за сутки UTC."""
    start, end = _utc_day_bounds()
    stmt = (
        select(func.count(distinct(HistoryEvent.incident_id)))
        .select_from(HistoryEvent)
        .where(
            HistoryEvent.type.in_(
                (HistoryEventType.status_changed, HistoryEventType.resolved)
            ),
            HistoryEvent.payload["status"]["to"].astext == IncidentStatus.Resolved.value,
            HistoryEvent.created_at >= start,
            HistoryEvent.created_at < end,
        )
    )
    return db.scalar(stmt) or 0


def _db_counts(db: Session) -> dict[str, int]:
    """Эталонные значения — прямыми запросами к БД."""

    def count(*conditions) -> int:
        return db.scalar(select(func.count()).select_from(Incident).where(*conditions)) or 0

    return {
        "open": count(Incident.status != IncidentStatus.Closed),
        "new": count(Incident.status == IncidentStatus.New),
        "in_progress": count(Incident.status == IncidentStatus.InProgress),
        "critical": count(
            Incident.priority == IncidentPriority.Critical,
            Incident.status != IncidentStatus.Closed,
        ),
        "resolved_today": _db_resolved_today(db),
    }


def _db_by_priority(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(Incident.priority, func.count()).group_by(Incident.priority)
    ).all()
    return {priority.value: total for priority, total in rows}


def _api_counts(client: TestClient) -> dict[str, int]:
    response = client.get("/api/dashboard")
    assert response.status_code == 200, response.text
    return response.json()["counts"]


def _delta(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    return {key: after[key] - before[key] for key in after}


# --- форма ответа и пустые данные ----------------------------------------


def test_dashboard_returns_documented_shape(client: TestClient) -> None:
    body = client.get("/api/dashboard").json()

    assert set(body) == {"counts", "by_priority", "recent_activity"}
    assert set(body["counts"]) == {
        "open",
        "new",
        "in_progress",
        "critical",
        "resolved_today",
    }
    # ключи приоритетов есть всегда: frontend не должен проверять их наличие
    assert set(body["by_priority"]) == {"Critical", "High", "Medium", "Low"}
    assert isinstance(body["recent_activity"], list)


def test_dashboard_recent_activity_is_empty_before_any_event(
    client: TestClient, db_session: Session
) -> None:
    events_in_db = db_session.scalar(select(func.count()).select_from(HistoryEvent))

    body = client.get("/api/dashboard").json()

    if events_in_db == 0:
        assert body["recent_activity"] == []
    else:  # pragma: no cover - защита от «грязной» БД, в CI БД чистая
        assert len(body["recent_activity"]) <= RECENT_ACTIVITY_LIMIT


def test_dashboard_does_not_require_user_header(client: TestClient) -> None:
    assert client.get("/api/dashboard").status_code == 200


# --- сходимость счётчиков с БД -------------------------------------------


def test_dashboard_counts_match_database(
    client: TestClient, db_session: Session, make_incident
) -> None:
    """Все счётчики сходятся с БД на смешанном наборе инцидентов."""
    before_api = _api_counts(client)
    before_db = _db_counts(db_session)

    make_incident(title="Новый критичный", priority="Critical", status="New")
    make_incident(title="Новый низкий", priority="Low", status="New")
    make_incident(title="В работе высокий", priority="High", status="In Progress")
    make_incident(title="В работе критичный", priority="Critical", status="In Progress")
    make_incident(title="Решённый средний", priority="Medium", status="Resolved")
    make_incident(title="Закрытый критичный", priority="Critical", status="Closed")

    after_api = _api_counts(client)
    after_db = _db_counts(db_session)

    # API и SQL дают одинаковый прирост по каждому счётчику
    assert _delta(before_api, after_api) == _delta(before_db, after_db)

    growth = _delta(before_api, after_api)
    assert growth["open"] == 5  # закрытый в open не входит
    assert growth["new"] == 2
    assert growth["in_progress"] == 2
    assert growth["critical"] == 2  # закрытый Critical не считается открытым
    # Resolved и Closed переведены в Resolved сегодня — оба попали в счёт
    assert growth["resolved_today"] == 2
    # эталон и после прироста совпадает по абсолютным значениям
    assert after_api == after_db


def test_dashboard_by_priority_matches_group_by(
    client: TestClient, db_session: Session, make_incident
) -> None:
    before = client.get("/api/dashboard").json()["by_priority"]

    make_incident(title="Критичный один", priority="Critical")
    make_incident(title="Критичный два", priority="Critical")
    make_incident(title="Низкий один", priority="Low")

    after_api = client.get("/api/dashboard").json()["by_priority"]
    after_db = _db_by_priority(db_session)

    for priority in after_api:
        assert after_api[priority] == after_db.get(priority, 0), priority

    assert after_api["Critical"] - before["Critical"] == 2
    assert after_api["Low"] - before["Low"] == 1

    # разрез покрывает весь реестр: сумма ключей = число инцидентов
    total = db_session.scalar(select(func.count()).select_from(Incident))
    assert sum(after_api.values()) == total


# --- resolved_today: по истории, а не по updated_at -----------------------


def test_dashboard_resolved_today_counts_only_today(
    client: TestClient, db_session: Session, make_incident
) -> None:
    """Вчерашний переход в Resolved не попадает в «решено сегодня»."""
    before = _api_counts(client)["resolved_today"]

    make_incident(title="Решённый сегодня", status="Resolved")
    yesterday = make_incident(title="Решённый вчера", status="Resolved")

    # Сдвигаем событие resolved в прошлое — эмулируем вчерашнее решение.
    event = db_session.scalars(
        select(HistoryEvent).where(
            HistoryEvent.incident_id == yesterday["id"],
            HistoryEvent.type == HistoryEventType.resolved,
        )
    ).one()
    event.created_at = datetime.now(UTC) - timedelta(days=1)
    db_session.flush()

    counts = _api_counts(client)

    assert counts["resolved_today"] - before == 1
    assert counts["resolved_today"] == _db_resolved_today(db_session)


def test_dashboard_resolved_today_ignores_updated_at(
    client: TestClient, db_session: Session, make_incident
) -> None:
    """Правка инцидента после решения не делает его «решённым сегодня»."""
    incident = make_incident(title="Решённый давно", status="In Progress")
    client.patch(
        f"/api/incidents/{incident['id']}/status",
        json={"status": "Resolved", "resolution": "Старое решение"},
        headers={"X-User-Id": "1"},
    )

    history = db_session.scalars(
        select(HistoryEvent)
        .where(HistoryEvent.incident_id == incident["id"])
        .order_by(HistoryEvent.id)
    ).all()
    for event in history:
        event.created_at = datetime.now(UTC) - timedelta(days=3)
    db_session.flush()

    before = _api_counts(client)["resolved_today"]

    # PATCH обновляет updated_at, но статус уже Resolved — правим приоритет.
    patched = client.patch(
        f"/api/incidents/{incident['id']}",
        json={"priority": "Critical"},
        headers={"X-User-Id": "1"},
    )
    assert patched.status_code == 200, patched.text

    after = _api_counts(client)["resolved_today"]
    assert after == before, "updated_at не должен влиять на resolved_today"
    assert after == _db_resolved_today(db_session)


# --- recent_activity ------------------------------------------------------


def test_dashboard_recent_activity_matches_history(
    client: TestClient, make_incident
) -> None:
    """Лента — последние события истории, свежие сверху."""
    created = [make_incident(title=f"Инцидент активности {index}") for index in range(8)]

    recent = client.get("/api/dashboard").json()["recent_activity"]

    assert len(recent) <= RECENT_ACTIVITY_LIMIT

    timestamps = [event["created_at"] for event in recent]
    assert timestamps == sorted(timestamps, reverse=True)

    # все восемь только что созданных инцидентов видны в ленте (по 1 событию created)
    listed = {event["incident_id"] for event in recent if event["type"] == "created"}
    assert {incident["id"] for incident in created} <= listed

    newest = recent[0]
    assert newest["type"] == "created"
    assert newest["incident"]["id"].startswith("INC-")
    assert newest["incident"]["title"].startswith("Инцидент активности")
    assert newest["actor"] == {"id": 1, "name": "Иван Петров"}
    assert newest["payload"]["status"] == {"from": None, "to": "New"}


def test_dashboard_recent_activity_limited_to_ten(
    client: TestClient, make_incident, actor_headers: dict[str, str]
) -> None:
    incident = make_incident(title="Инцидент с длинной историей")
    for index in range(12):
        response = client.patch(
            f"/api/incidents/{incident['id']}",
            json={"description": f"Уточнение номер {index}"},
            headers=actor_headers,
        )
        assert response.status_code == 200, response.text

    recent = client.get("/api/dashboard").json()["recent_activity"]

    assert len(recent) == RECENT_ACTIVITY_LIMIT == 10
    # последнее изменение — сверху
    assert recent[0]["payload"]["description"]["to"] == "Уточнение номер 11"
    assert all(event["incident_id"] == incident["id"] for event in recent)


def test_dashboard_recent_activity_includes_status_events(
    client: TestClient, make_incident
) -> None:
    incident = make_incident(title="Инцидент для ленты статусов", status="Resolved")

    recent = client.get("/api/dashboard").json()["recent_activity"]

    types = [event["type"] for event in recent if event["incident_id"] == incident["id"]]
    # лента: свежие сверху — resolved, затем New → In Progress, затем создание
    assert types == ["resolved", "status_changed", "created"]
    resolved_event = next(event for event in recent if event["type"] == "resolved")
    assert resolved_event["payload"]["status"] == {"from": "In Progress", "to": "Resolved"}


# --- семантика «открытых» -------------------------------------------------


def test_dashboard_open_excludes_only_closed(
    client: TestClient, db_session: Session, make_incident
) -> None:
    """Resolved ещё не закрыт: он входит в `open`, но не в `new`/`in_progress`."""
    before = _api_counts(client)

    make_incident(title="Решённый но не закрытый", status="Resolved")

    after = _api_counts(client)

    assert _delta(before, after) == {
        "open": 1,
        "new": 0,
        "in_progress": 0,
        "critical": 0,
        "resolved_today": 1,
    }
    assert after == _db_counts(db_session)


@pytest.mark.parametrize("status", ["New", "In Progress", "Resolved", "Closed"])
def test_dashboard_counts_are_consistent_with_status(
    client: TestClient, db_session: Session, make_incident, status: str
) -> None:
    before = _api_counts(client)

    make_incident(title=f"Инцидент в статусе {status}", status=status)

    growth = _delta(before, _api_counts(client))

    assert growth["new"] == (1 if status == "New" else 0)
    assert growth["in_progress"] == (1 if status == "In Progress" else 0)
    assert growth["open"] == (0 if status == "Closed" else 1)
    # Closed тоже переведён в Resolved сегодня — по семантике «по истории» он в счёте
    assert growth["resolved_today"] == (0 if status in {"New", "In Progress"} else 1)
    assert _api_counts(client) == _db_counts(db_session)