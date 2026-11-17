interface StateMessageProps {
  title: string;
  text?: string;
  onRetry?: () => void;
  retryLabel?: string;
}

/** Единое пустое/информационное состояние: без «молчания» и без ложного успеха. */
export function StateMessage({
  title,
  text,
  onRetry,
  retryLabel = "Повторить",
}: StateMessageProps) {
  return (
    <div className="state-message">
      <p className="state-message__title">{title}</p>
      {text && <p className="state-message__text">{text}</p>}
      {onRetry && (
        <button type="button" className="button button--secondary" onClick={onRetry}>
          {retryLabel}
        </button>
      )}
    </div>
  );
}

interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

/** Ошибка сети/4xx/5xx — понятным текстом, с повтором запроса. */
export function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className="alert alert--error" role="alert">
      <div>
        <strong>Не удалось загрузить данные</strong>
        <p className="alert__text">{message}</p>
      </div>
      {onRetry && (
        <button type="button" className="button button--secondary" onClick={onRetry}>
          Повторить
        </button>
      )}
    </div>
  );
}

/** Скелетон загрузки — чтобы не показывать нули дашборда до ответа API. */
export function LoadingMessage({ label = "Загрузка…" }: { label?: string }) {
  return (
    <p className="loading" role="status">
      {label}
    </p>
  );
}
