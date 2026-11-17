import type { ReactNode } from "react";

interface KpiCardProps {
  label: string;
  /** Нет данных (ошибка загрузки) — показываем прочерк, а не ложный ноль. */
  value: number | string | null;
  /** Тон значения: критические — красным, решения — зелёным. */
  tone?: "default" | "critical" | "success" | "info";
  isLoading?: boolean;
  hint?: string;
}

/** KPI-карточка дашборда/реестра: число крупно, подпись сверху. */
export function KpiCard({ label, value, tone = "default", isLoading = false, hint }: KpiCardProps) {
  const isMissing = !isLoading && value === null;

  return (
    <div className={`kpi kpi--${tone}`}>
      <span className="kpi__label">{label}</span>
      <span className={isMissing ? "kpi__value kpi__value--empty" : "kpi__value"}>
        {isLoading ? "…" : (value ?? "—")}
      </span>
      {hint && <span className="kpi__hint">{hint}</span>}
    </div>
  );
}

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
}

/** Шапка страницы внутри контента: заголовок, пояснение и действия. */
export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="page-header">
      <div className="page-header__text">
        <h2 className="page-header__title">{title}</h2>
        {description && <p className="page-header__description">{description}</p>}
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </div>
  );
}
