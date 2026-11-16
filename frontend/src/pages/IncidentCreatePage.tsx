import { type FormEvent, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { IncidentCategory, IncidentPriority } from "../api/client";
import { api, INCIDENT_CATEGORIES, INCIDENT_PRIORITIES } from "../api/client";
import { FormField, fieldAria } from "../components/FormField";
import { PageHeader } from "../components/KpiCard";
import { useCurrentUserId } from "../hooks/useCurrentUserId";
import { useUsers } from "../hooks/useUsers";
import { describeError, fieldErrors } from "../utils/apiError";
import {
  CATEGORY_LABELS,
  DESCRIPTION_MAX_LENGTH,
  PRIORITY_LABELS,
  TITLE_MAX_LENGTH,
  TITLE_MIN_LENGTH,
} from "../utils/labels";

interface FormValues {
  title: string;
  description: string;
  category: IncidentCategory;
  priority: IncidentPriority;
  /** `""` — без ответственного. */
  assigneeId: string;
}

const INITIAL_VALUES: FormValues = {
  title: "",
  description: "",
  category: "Other",
  priority: "Medium",
  assigneeId: "",
};

const FALLBACK_ERROR = "Не удалось создать инцидент. Повторите попытку.";

/** Клиентская проверка — подсказка пользователю; окончательно решает backend. */
function validate(values: FormValues): Record<string, string> {
  const errors: Record<string, string> = {};
  const title = values.title.trim();
  if (title.length === 0) {
    errors.title = "Укажите название инцидента.";
  } else if (title.length < TITLE_MIN_LENGTH) {
    errors.title = `Минимум ${TITLE_MIN_LENGTH} символов, сейчас ${title.length}.`;
  } else if (title.length > TITLE_MAX_LENGTH) {
    errors.title = `Максимум ${TITLE_MAX_LENGTH} символов, сейчас ${title.length}.`;
  }
  if (values.description.length > DESCRIPTION_MAX_LENGTH) {
    errors.description = `Максимум ${DESCRIPTION_MAX_LENGTH} символов.`;
  }
  return errors;
}

/** Форма создания инцидента (TASK.md §4): после успеха — переход в карточку. */
export function IncidentCreatePage() {
  const [values, setValues] = useState<FormValues>(INITIAL_VALUES);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();
  const currentUserId = useCurrentUserId();
  const { users, isLoading: usersLoading, error: usersError } = useUsers();

  const categoryOptions = useMemo(
    () => INCIDENT_CATEGORIES.map((value) => ({ value, label: CATEGORY_LABELS[value] })),
    [],
  );
  const priorityOptions = useMemo(
    () => INCIDENT_PRIORITIES.map((value) => ({ value, label: PRIORITY_LABELS[value] })),
    [],
  );

  /** Обновить поле и снять его ошибку — текст снова актуален после правки. */
  function update<K extends keyof FormValues>(key: K, value: FormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
    setErrors((current) => {
      if (!(key in current)) {
        return current;
      }
      const { [key]: _removed, ...rest } = current;
      return rest;
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }

    const clientErrors = validate(values);
    setErrors(clientErrors);
    setSubmitError(null);
    if (Object.keys(clientErrors).length > 0) {
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await api.incidents.create({
        title: values.title.trim(),
        description: values.description.trim(),
        category: values.category,
        priority: values.priority,
        assignee_id: values.assigneeId === "" ? null : Number(values.assigneeId),
      });
      navigate(`/incidents/${created.id}`);
    } catch (cause) {
      // Ошибки полей от backend показываем у самих полей, общий текст — сверху.
      setErrors(fieldErrors(cause));
      setSubmitError(describeError(cause, FALLBACK_ERROR));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="page">
      <PageHeader
        title="Новый инцидент"
        description="Опишите проблему, выберите категорию и приоритет. Номер INC-NNN и статус New присвоит сервер."
        actions={
          <Link className="button button--secondary" to="/incidents">
            К реестру
          </Link>
        }
      />

      <form className="panel form" onSubmit={handleSubmit} noValidate>
        {submitError && (
          <div className="alert alert--error" role="alert">
            <div>
              <strong>Инцидент не создан</strong>
              <p className="alert__text">{submitError}</p>
            </div>
          </div>
        )}

        <FormField
          id="title"
          label="Название"
          hint={`От ${TITLE_MIN_LENGTH} до ${TITLE_MAX_LENGTH} символов. Коротко: что не работает.`}
          error={errors.title}
        >
          <input
            id="title"
            name="title"
            type="text"
            value={values.title}
            maxLength={TITLE_MAX_LENGTH}
            placeholder="Например, «Не работает почта»"
            autoComplete="off"
            onChange={(event) => update("title", event.target.value)}
            {...fieldAria("title", Boolean(errors.title), true)}
          />
        </FormField>

        <FormField
          id="description"
          label="Описание"
          hint={`Необязательно, до ${DESCRIPTION_MAX_LENGTH} символов. Детали: когда началось, что уже проверено.`}
          error={errors.description}
        >
          <textarea
            id="description"
            name="description"
            rows={5}
            value={values.description}
            maxLength={DESCRIPTION_MAX_LENGTH}
            placeholder="Письма не приходят с 9:00, у всей команды"
            onChange={(event) => update("description", event.target.value)}
            {...fieldAria("description", Boolean(errors.description), true)}
          />
        </FormField>

        <div className="form__row">
          <FormField id="category" label="Категория" error={errors.category}>
            <select
              id="category"
              name="category"
              value={values.category}
              onChange={(event) => update("category", event.target.value as IncidentCategory)}
              {...fieldAria("category", Boolean(errors.category))}
            >
              {categoryOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </FormField>

          <FormField id="priority" label="Приоритет" error={errors.priority}>
            <select
              id="priority"
              name="priority"
              value={values.priority}
              onChange={(event) => update("priority", event.target.value as IncidentPriority)}
              {...fieldAria("priority", Boolean(errors.priority))}
            >
              {priorityOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </FormField>

          <FormField
            id="assignee"
            label="Ответственный"
            hint={usersError ? `Справочник недоступен: ${usersError}` : "Можно назначить позже."}
            error={errors.assignee_id}
          >
            <select
              id="assignee"
              name="assignee"
              value={values.assigneeId}
              disabled={usersLoading || users.length === 0}
              onChange={(event) => update("assigneeId", event.target.value)}
              {...fieldAria("assignee", Boolean(errors.assignee_id), true)}
            >
              <option value="">
                {usersLoading
                  ? "Загрузка…"
                  : users.length === 0
                    ? "Нет пользователей"
                    : "Не назначен"}
              </option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.name}
                </option>
              ))}
            </select>
          </FormField>
        </div>

        {currentUserId === null && (
          <p className="alert alert--warning alert--compact" role="status">
            Текущий пользователь не выбран — сервер отклонит создание. Выберите пользователя в
            шапке.
          </p>
        )}

        <div className="form__actions">
          <button type="submit" className="button button--primary" disabled={isSubmitting}>
            {isSubmitting ? "Создаём…" : "Создать инцидент"}
          </button>
          <Link className="button button--secondary" to="/incidents">
            Отмена
          </Link>
        </div>
      </form>
    </section>
  );
}
