import { type FormEvent, useId, useState } from "react";

import type { IncidentStatus } from "../api/types";
import { RESOLUTION_MAX_LENGTH } from "../utils/labels";
import { canResolve, immediateStatusActions } from "../utils/transitions";

interface StatusActionsProps {
  /** Переходы, разрешённые сервером (`allowed_transitions` карточки). */
  transitions: readonly IncidentStatus[];
  /**
   * Выполнить переход. `true` — сервер принял изменение; `false` — ошибка
   * показана вызывающей стороной, форму решения закрывать не нужно.
   */
  onChangeStatus: (target: IncidentStatus, resolution?: string) => Promise<boolean>;
  /** Переход, который сейчас выполняется (блокирует кнопки). */
  pendingTarget: IncidentStatus | null;
  /** Карточка перечитывается: старые переходы на экране уже неактуальны. */
  isRefreshing?: boolean;
}

/**
 * Действия карточки. Источник истины — `allowed_transitions` из API: UI не
 * дублирует автомат статусов (TASK.md §2, ADR 0003 §4) и просто не рисует
 * недопустимые кнопки. Для перехода в Resolved показывается форма решения.
 */
export function StatusActions({
  transitions,
  onChangeStatus,
  pendingTarget,
  isRefreshing = false,
}: StatusActionsProps) {
  const uid = useId();
  const resolutionId = `${uid}-resolution`;
  const resolutionErrorId = `${uid}-resolution-error`;
  const resolutionHintId = `${uid}-resolution-hint`;
  const [isResolveOpen, setIsResolveOpen] = useState(false);
  const [resolution, setResolution] = useState("");
  const [resolveError, setResolveError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const actions = immediateStatusActions(transitions);
  const canResolveNow = canResolve(transitions);
  const isBusy = pendingTarget !== null || isSubmitting || isRefreshing;

  if (transitions.length === 0) {
    return (
      <p className="status-actions status-actions--closed">
        Инцидент закрыт: действий по статусу нет, карточка доступна только для чтения.
      </p>
    );
  }

  async function handleResolve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }

    const text = resolution.trim();
    if (text.length === 0) {
      setResolveError("Опишите решение — без этого сервер не переведёт инцидент в «Решён».");
      return;
    }
    if (text.length > RESOLUTION_MAX_LENGTH) {
      setResolveError(`Максимум ${RESOLUTION_MAX_LENGTH} символов, сейчас ${text.length}.`);
      return;
    }

    setResolveError(null);
    setIsSubmitting(true);
    try {
      const ok = await onChangeStatus("Resolved", text);
      if (ok) {
        setResolution("");
        setIsResolveOpen(false);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="status-actions">
      <div className="status-actions__buttons">
        {actions.map((action) => (
          <button
            key={action.target}
            type="button"
            className={
              action.kind === "close" ? "button button--secondary" : "button button--primary"
            }
            disabled={isBusy}
            onClick={() => {
              void onChangeStatus(action.target);
            }}
          >
            {pendingTarget === action.target ? "Выполняем…" : action.label}
          </button>
        ))}

        {canResolveNow && !isResolveOpen && (
          <button
            type="button"
            className="button button--primary"
            disabled={isBusy}
            onClick={() => {
              setResolveError(null);
              setIsResolveOpen(true);
            }}
          >
            Решить
          </button>
        )}
      </div>

      {canResolveNow && isResolveOpen && (
        <form className="resolve-form" onSubmit={handleResolve} noValidate>
          <label className="field__label" htmlFor={resolutionId}>
            Описание решения (обязательно)
          </label>
          <textarea
            id={resolutionId}
            name="resolution"
            rows={4}
            value={resolution}
            maxLength={RESOLUTION_MAX_LENGTH}
            placeholder="Что сделали, чтобы проблема ушла"
            aria-invalid={Boolean(resolveError)}
            aria-describedby={resolveError ? resolutionErrorId : resolutionHintId}
            onChange={(event) => {
              setResolution(event.target.value);
              if (resolveError) {
                setResolveError(null);
              }
            }}
          />
          {resolveError ? (
            <span className="field__error" id={resolutionErrorId} role="alert">
              {resolveError}
            </span>
          ) : (
            <span className="field__hint" id={resolutionHintId}>
              Попадёт в карточку и историю: «Решение: …». До {RESOLUTION_MAX_LENGTH} символов.
            </span>
          )}
          <div className="resolve-form__actions">
            <button type="submit" className="button button--primary" disabled={isBusy}>
              {pendingTarget === "Resolved" ? "Сохраняем…" : "Подтвердить решение"}
            </button>
            <button
              type="button"
              className="button button--ghost"
              disabled={isBusy}
              onClick={() => {
                setIsResolveOpen(false);
                setResolveError(null);
                setResolution("");
              }}
            >
              Отмена
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
