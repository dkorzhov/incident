import type { ReactNode } from "react";

interface FormFieldProps {
  /** id контрола: с ним связаны `label` и подсказка/ошибка. */
  id: string;
  label: string;
  /** Текст ошибки конкретного поля (клиентской или серверной). */
  error?: string;
  hint?: string;
  /** Дополнительный класс обёртки, например `field--grow`. */
  className?: string;
  children: ReactNode;
}

/** id элемента с подсказкой/ошибкой поля — для `aria-describedby`. */
function descriptionId(id: string, hasError: boolean, hasHint: boolean): string | undefined {
  if (hasError) {
    return `${id}-error`;
  }
  return hasHint ? `${id}-hint` : undefined;
}

/**
 * Поле формы: подпись, контрол и ошибка под ним.
 *
 * Общая ошибка формы идёт отдельным `role="alert"`, а ошибка поля привязана к
 * контролу через `aria-describedby` (см. `fieldAria`), чтобы скринридер читал
 * её вместе с полем.
 */
export function FormField({ id, label, error, hint, className, children }: FormFieldProps) {
  const classes = className ? `field ${className}` : "field";
  const describedBy = descriptionId(id, Boolean(error), Boolean(hint));
  return (
    <div className={classes}>
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      {children}
      {hint && !error && (
        <span className="field__hint" id={describedBy}>
          {hint}
        </span>
      )}
      {error && (
        <span className="field__error" id={describedBy}>
          {error}
        </span>
      )}
    </div>
  );
}

/**
 * Атрибуты контрола внутри `FormField`: невалидность и связь с
 * подсказкой/ошибкой. `hasHint` должен совпадать с наличием `hint` у поля.
 */
export function fieldAria(id: string, hasError: boolean, hasHint = false) {
  return {
    "aria-invalid": hasError ? true : undefined,
    "aria-describedby": descriptionId(id, hasError, hasHint),
  } as const;
}
