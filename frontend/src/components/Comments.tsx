import { type FormEvent, useState } from "react";

import type { Comment } from "../api/types";
import { COMMENT_MAX_LENGTH, formatDateTime } from "../utils/labels";
import { StateMessage } from "./StateMessage";

interface CommentListProps {
  comments: readonly Comment[];
}

/** Список комментариев в хронологическом порядке (как отдаёт backend). */
export function CommentList({ comments }: CommentListProps) {
  if (comments.length === 0) {
    return (
      <StateMessage
        title="Комментариев пока нет"
        text="Уточнения и ход работ пишите здесь — команда увидит их в карточке."
      />
    );
  }

  return (
    <ul className="comment-list">
      {comments.map((comment) => (
        <li key={comment.id} className="comment">
          <div className="comment__header">
            <span className="comment__author">{comment.author.name}</span>
            <time className="comment__time" dateTime={comment.created_at}>
              {formatDateTime(comment.created_at)}
            </time>
          </div>
          <p className="comment__text">{comment.text}</p>
        </li>
      ))}
    </ul>
  );
}

interface CommentFormProps {
  /** `true` — сервер принял комментарий. */
  onSubmit: (text: string) => Promise<boolean>;
  isSubmitting: boolean;
  /** Инцидент закрыт: комментарии сервер отклоняет (409), форму не рисуем. */
  disabledReason?: string;
}

/** Форма нового комментария: автор — текущий пользователь из `X-User-Id`. */
export function CommentForm({ onSubmit, isSubmitting, disabledReason }: CommentFormProps) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (disabledReason) {
    return (
      <p className="alert alert--warning alert--compact" role="status">
        {disabledReason}
      </p>
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }
    const value = text.trim();
    if (value.length === 0) {
      setError("Введите текст комментария.");
      return;
    }
    if (value.length > COMMENT_MAX_LENGTH) {
      setError(`Максимум ${COMMENT_MAX_LENGTH} символов.`);
      return;
    }
    setError(null);

    const ok = await onSubmit(value);
    if (ok) {
      setText("");
    }
  }

  return (
    <form className="comment-form" onSubmit={handleSubmit} noValidate>
      <label className="field__label" htmlFor="comment-text">
        Новый комментарий
      </label>
      <textarea
        id="comment-text"
        name="comment"
        rows={3}
        value={text}
        maxLength={COMMENT_MAX_LENGTH}
        placeholder="Что уточнить или что уже сделано"
        aria-invalid={Boolean(error)}
        aria-describedby={error ? "comment-error" : "comment-hint"}
        onChange={(event) => {
          setText(event.target.value);
          if (error) {
            setError(null);
          }
        }}
      />
      {error ? (
        <span className="field__error" id="comment-error" role="alert">
          {error}
        </span>
      ) : (
        <span className="field__hint" id="comment-hint">
          До {COMMENT_MAX_LENGTH} символов. Автор — текущий пользователь из шапки.
        </span>
      )}
      <div>
        <button type="submit" className="button button--primary" disabled={isSubmitting}>
          {isSubmitting ? "Отправляем…" : "Добавить комментарий"}
        </button>
      </div>
    </form>
  );
}
