"""Автомат статусов инцидента (TASK.md §2).

Разрешены ровно три перехода; всё остальное — конфликт состояния (409):

    New         → In Progress
    In Progress → Resolved   (только с непустым resolution)
    Resolved    → Closed
"""

from __future__ import annotations

from typing import Final

from app.domain.errors import ConflictError
from app.models.incident import Incident, IncidentStatus

#: Допустимые переходы. ``Closed`` — конечное состояние.
ALLOWED_TRANSITIONS: Final[dict[IncidentStatus, frozenset[IncidentStatus]]] = {
    IncidentStatus.New: frozenset({IncidentStatus.InProgress}),
    IncidentStatus.InProgress: frozenset({IncidentStatus.Resolved}),
    IncidentStatus.Resolved: frozenset({IncidentStatus.Closed}),
    IncidentStatus.Closed: frozenset(),
}

#: Человекочитаемые названия действий — для текстов ошибок и будущего UI (DMI-7).
TRANSITION_ACTIONS: Final[dict[tuple[IncidentStatus, IncidentStatus], str]] = {
    (IncidentStatus.New, IncidentStatus.InProgress): "Взять в работу",
    (IncidentStatus.InProgress, IncidentStatus.Resolved): "Отметить решённым",
    (IncidentStatus.Resolved, IncidentStatus.Closed): "Закрыть",
}


def allowed_transitions(current: IncidentStatus) -> frozenset[IncidentStatus]:
    """Статусы, в которые можно перевести инцидент из текущего."""
    return ALLOWED_TRANSITIONS[current]


def action_for(current: IncidentStatus, target: IncidentStatus) -> str | None:
    """Название действия для допустимого перехода (``None`` — переход недопустим)."""
    return TRANSITION_ACTIONS.get((current, target))


def ensure_transition_allowed(current: IncidentStatus, target: IncidentStatus) -> None:
    """409, если перехода ``current → target`` нет в автомате."""
    if target in ALLOWED_TRANSITIONS[current]:
        return

    allowed = ALLOWED_TRANSITIONS[current]
    if allowed:
        hint = "допустимо: " + ", ".join(_sorted_values(allowed))
    else:
        hint = "инцидент закрыт, переходы недоступны"
    raise ConflictError(
        f"Недопустимый переход статуса: {current.value} → {target.value} ({hint})"
    )


def ensure_editable(incident: Incident, *, action: str = "изменять инцидент") -> None:
    """409, если инцидент закрыт: после ``Closed`` он неизменяем."""
    if incident.status is IncidentStatus.Closed:
        raise ConflictError(
            f"Инцидент {incident.id} закрыт (Closed): {action} нельзя"
        )


def _sorted_values(statuses: frozenset[IncidentStatus]) -> list[str]:
    order = list(IncidentStatus)
    return [status.value for status in sorted(statuses, key=order.index)]