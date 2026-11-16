import type { IncidentCategory, IncidentPriority, IncidentStatus, UserBrief } from "../api/types";
import {
  CATEGORY_LABELS,
  categoryModifier,
  PRIORITY_LABELS,
  priorityModifier,
  STATUS_LABELS,
  statusModifier,
} from "../utils/labels";

interface PriorityBadgeProps {
  priority: IncidentPriority;
}

/** Бейдж приоритета: цвет задаётся модификатором по значению enum. */
export function PriorityBadge({ priority }: PriorityBadgeProps) {
  return (
    <span
      className={`badge badge--priority ${priorityModifier(priority)}`}
      data-priority={priority}
      title={`Приоритет: ${PRIORITY_LABELS[priority]}`}
    >
      {PRIORITY_LABELS[priority]}
    </span>
  );
}

interface StatusBadgeProps {
  status: IncidentStatus;
}

/** Бейдж статуса: цвет задаётся модификатором по значению enum. */
export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={`badge badge--status ${statusModifier(status)}`}
      data-status={status}
      title={`Статус: ${STATUS_LABELS[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

interface AssigneeTextProps {
  assignee: UserBrief | null | undefined;
}

/** Ответственный: имя из вложенного объекта, иначе «Не назначен». */
export function AssigneeText({ assignee }: AssigneeTextProps) {
  if (!assignee) {
    return <span className="table__muted">Не назначен</span>;
  }
  return <span>{assignee.name}</span>;
}

interface CategoryBadgeProps {
  category: IncidentCategory;
}

/** Бейдж категории: серый, чтобы не конкурировать с приоритетом и статусом. */
export function CategoryBadge({ category }: CategoryBadgeProps) {
  return (
    <span
      className={`badge badge--category ${categoryModifier(category)}`}
      data-category={category}
      title={`Категория: ${CATEGORY_LABELS[category]}`}
    >
      {CATEGORY_LABELS[category]}
    </span>
  );
}
