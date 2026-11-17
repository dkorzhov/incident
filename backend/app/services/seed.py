"""Демо-данные для локального запуска (TASK.md §6, DMI-10).

Seed включается переменной ``SEED_DEMO=true`` и выполняется один раз на базу:
повторный старт backend не задваивает инциденты.

Идемпотентность — отдельная таблица-маркер ``demo_seed_state`` (см.
``app/models/demo_seed.py``), а не поиск инцидентов по названию:

* ``title`` демо-инцидента пользователь может изменить через UI — seed,
  ищущий «свой» инцидент по названию, создал бы дубли на следующем старте;
* маркер вставляется через ``INSERT ... ON CONFLICT DO NOTHING``, поэтому два
  параллельно стартующих процесса не создадут набор дважды;
* строка маркера и демо-инциденты коммитятся **одной транзакцией**: при сбое
  посередине не остаётся ни частичных данных, ни маркера — следующий старт
  повторит попытку целиком.

Данные создаются прямыми ORM-вставками, а не через сервисы: сервисы коммитят
каждую операцию по отдельности и не дали бы атомарности «маркер + набор».
События истории пишутся функциями ``app/services/history.py`` — единственным
местом, где формируется формат ``payload``, поэтому демо-история не отличается
от настоящей. Решённый инцидент получает и ``resolution``, и событие
``resolved`` с переходом в Resolved: ``/api/dashboard`` считает
``resolved_today`` именно по истории, а не по ``updated_at``.

Под pytest seed не запускается (``running_under_pytest``): ``TestClient`` в
тестах поднимает ``lifespan``, а ``SessionLocal`` пишет мимо откатываемой
транзакционной фикстуры — демо-инциденты осели бы в тестовой БД навсегда.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.demo_seed import DemoSeedState
from app.models.incident import (
    Incident,
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
)
from app.models.user import User
from app.services import history

logger = logging.getLogger(__name__)

#: Ключ набора демо-данных: новая версия набора — новый ключ (старый остаётся).
DEMO_SEED_KEY: Final = "demo-v1"

#: Префикс названий: видно, что инцидент демонстрационный (не влияет на идемпотентность).
DEMO_TITLE_PREFIX: Final = "Демо: "


@dataclass(frozen=True, slots=True)
class DemoIncident:
    """Описание одного демо-инцидента: конечный статус и его составляющие."""

    title: str
    description: str
    category: IncidentCategory
    priority: IncidentPriority
    status: IncidentStatus
    assignee_index: int | None = None
    resolution: str | None = None
    comment: str | None = None


#: Набор покрывает все статусы и приоритеты: Critical для KPI, Resolved сегодня
#: для ``resolved_today``, Closed — чтобы было видно неизменяемое состояние.
DEMO_INCIDENTS: Final[tuple[DemoIncident, ...]] = (
    DemoIncident(
        title=f"{DEMO_TITLE_PREFIX}недоступен портал самообслуживания",
        description="Портал отдаёт 502 после релиза. Пользователи не могут согласовать заявки.",
        category=IncidentCategory.Portal,
        priority=IncidentPriority.Critical,
        status=IncidentStatus.InProgress,
        assignee_index=1,
        comment="Смотрю логи nginx и приложение за прокси, похоже на упавший upstream.",
    ),
    DemoIncident(
        title=f"{DEMO_TITLE_PREFIX}база данных отвечает по таймауту",
        description="Отчёты в BI перестали строиться: запросы к БД висят дольше 30 секунд.",
        category=IncidentCategory.Database,
        priority=IncidentPriority.Critical,
        status=IncidentStatus.New,
    ),
    DemoIncident(
        title=f"{DEMO_TITLE_PREFIX}не работает почта у отдела продаж",
        description="Письма не приходят с утра, у всей команды продаж.",
        category=IncidentCategory.Mail,
        priority=IncidentPriority.High,
        status=IncidentStatus.Resolved,
        assignee_index=2,
        resolution="Перезапущен почтовый шлюз, очередь писем разобрана. Мониторинг молчит.",
    ),
    DemoIncident(
        title=f"{DEMO_TITLE_PREFIX}принтер в бухгалтерии не печатает",
        description="Печать зависает в очереди, помогает только перезагрузка принтера.",
        category=IncidentCategory.Workplace,
        priority=IncidentPriority.Medium,
        status=IncidentStatus.Closed,
        assignee_index=3,
        resolution="Заменён сетевой кабель, очередь печати очищена.",
    ),
    DemoIncident(
        title=f"{DEMO_TITLE_PREFIX}медленный Wi-Fi в переговорной",
        description="Видеозвонки рассыпаются, скорость около 2 Мбит/с.",
        category=IncidentCategory.Network,
        priority=IncidentPriority.Medium,
        status=IncidentStatus.InProgress,
        assignee_index=1,
    ),
    DemoIncident(
        title=f"{DEMO_TITLE_PREFIX}нужен доступ к общему диску проекта",
        description="Новый сотрудник просит доступ на чтение к каталогу проекта.",
        category=IncidentCategory.Other,
        priority=IncidentPriority.Low,
        status=IncidentStatus.New,
        assignee_index=4,
    ),
)


def running_under_pytest() -> bool:
    """``True`` — процесс запущен pytest'ом, демо-данные писать нельзя.

    Проверка по ``sys.modules``, а не по переменной окружения: compose задаёт
    ``SEED_DEMO=true`` контейнеру backend, и ``docker compose exec backend
    pytest`` унаследовал бы её. Флаг окружения тут не отличит приложение от
    тестов, а импортированный pytest — отличает.
    """
    return "pytest" in sys.modules


def seed_demo_data(db: Session) -> int:
    """Создать демо-инциденты, если набор ещё не применён.

    Возвращает число созданных инцидентов (0 — набор уже есть). Всё пишется
    одной транзакцией: маркер и данные коммитятся вместе.
    """
    users = db.scalars(select(User).order_by(User.id)).all()
    if not users:
        # Справочник заполняет миграция 0001_users; без него назначать некого,
        # а падать из-за демо-данных приложение не должно.
        logger.warning("Демо-данные не созданы: справочник пользователей пуст")
        return 0

    if not _claim_seed_slot(db):
        logger.info("Демо-данные уже применены (ключ %s) — пропускаю", DEMO_SEED_KEY)
        return 0

    actor = users[0]
    for spec in DEMO_INCIDENTS:
        _create_demo_incident(db, spec, users=users, actor=actor)

    db.commit()
    logger.info("Демо-данные созданы: %d инцидентов (ключ %s)", len(DEMO_INCIDENTS), DEMO_SEED_KEY)
    return len(DEMO_INCIDENTS)


def _claim_seed_slot(db: Session) -> bool:
    """Атомарно занять маркер набора: ``True`` — этот процесс создаёт данные.

    ``RETURNING key`` вместо ``rowcount``: при конфликте PostgreSQL возвращает
    ``-1`` в ``rowcount``, а ``ON CONFLICT DO NOTHING`` без ``RETURNING`` не
    отличил бы «уже занято» от «вставлено». Пустой результат ``RETURNING`` —
    ключ уже есть.

    Вызывать только в начале транзакции: ``rollback`` при занятом слоте
    откатил бы и чужие незакоммиченные изменения сессии.
    """
    statement = (
        pg_insert(DemoSeedState)
        .values(key=DEMO_SEED_KEY)
        .on_conflict_do_nothing(index_elements=[DemoSeedState.key])
        .returning(DemoSeedState.key)
    )
    claimed = db.scalar(statement) is not None
    if not claimed:
        # Чужих изменений в этой транзакции нет: откат освобождает блокировку.
        db.rollback()
    return claimed


def _create_demo_incident(
    db: Session, spec: DemoIncident, *, users: list[User], actor: User
) -> None:
    """Провести инцидент по его жизненному циклу, записывая историю.

    Статус ставится шагами автомата §2 (New → In Progress → Resolved → Closed)
    с событием на каждый шаг: карточка демо-инцидента выглядит так же, как у
    созданного руками.
    """
    assignee = users[spec.assignee_index % len(users)] if spec.assignee_index is not None else None

    incident = Incident(
        title=spec.title,
        description=spec.description,
        category=spec.category,
        priority=spec.priority,
        status=IncidentStatus.New,
        assignee_id=assignee.id if assignee else None,
    )
    db.add(incident)
    db.flush()

    history.record_created(db, incident=incident, actor=actor)
    if assignee is not None:
        history.record_assigned(
            db,
            incident=incident,
            actor=actor,
            before_id=None,
            after_id=assignee.id,
            before_name=None,
            after_name=assignee.name,
        )
    if spec.comment:
        comment = Comment(incident_id=incident.id, author_id=actor.id, text=spec.comment)
        db.add(comment)
        db.flush()
        history.record_commented(
            db, incident=incident, actor=actor, comment_id=comment.id, text=comment.text
        )

    if spec.status is IncidentStatus.New:
        return

    incident.status = IncidentStatus.InProgress
    db.flush()
    history.record_status_changed(
        db,
        incident=incident,
        actor=actor,
        before=IncidentStatus.New,
        after=IncidentStatus.InProgress,
    )

    if spec.status is IncidentStatus.InProgress:
        return

    if not spec.resolution:
        # Набор описан в коде: отсутствие resolution — ошибка в DEMO_INCIDENTS,
        # а не данные пользователя. CHECK БД всё равно не пропустит Resolved.
        raise ValueError(f"У демо-инцидента {spec.title!r} нет resolution для Resolved")

    incident.status = IncidentStatus.Resolved
    incident.resolution = spec.resolution
    db.flush()
    history.record_resolved(
        db,
        incident=incident,
        actor=actor,
        before=IncidentStatus.InProgress,
        resolution=spec.resolution,
    )

    if spec.status is IncidentStatus.Resolved:
        return

    incident.status = IncidentStatus.Closed
    db.flush()
    history.record_status_changed(
        db,
        incident=incident,
        actor=actor,
        before=IncidentStatus.Resolved,
        after=IncidentStatus.Closed,
    )


def seed_demo_on_startup(*, session_factory: Callable[[], Session] | None = None) -> int:
    """Точка входа lifespan: выполнить seed, если он разрешён и не под pytest.

    Возвращает число созданных инцидентов (0 — выключено, уже применено или
    ошибка). Сбой демо-данных не должен мешать приложению подняться: без них
    API полностью работоспособен, а причина остаётся в логах.
    """
    if running_under_pytest():
        logger.info("SEED_DEMO пропущен: процесс запущен pytest")
        return 0

    if session_factory is None:
        # Ленивый импорт: движок создаётся только когда seed действительно нужен.
        from app.db import SessionLocal

        session_factory = SessionLocal

    db = session_factory()
    try:
        return seed_demo_data(db)
    except Exception:
        db.rollback()
        logger.exception("Не удалось создать демо-данные (SEED_DEMO=true)")
        return 0
    finally:
        db.close()


__all__ = [
    "DEMO_INCIDENTS",
    "DEMO_SEED_KEY",
    "DEMO_TITLE_PREFIX",
    "DemoIncident",
    "running_under_pytest",
    "seed_demo_data",
    "seed_demo_on_startup",
]
