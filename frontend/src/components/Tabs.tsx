import { type KeyboardEvent, type ReactNode, useId, useRef } from "react";

export interface TabItem {
  id: string;
  label: string;
  /** Счётчик справа от подписи, например число комментариев. */
  badge?: number;
}

interface TabsProps {
  items: readonly TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  /** Содержимое активной вкладки. */
  children: ReactNode;
  label: string;
}

/**
 * Вкладки карточки с ARIA-семантикой: `tablist` → `tab` → `tabpanel`.
 *
 * Активная панель рендерится одна, поэтому скрытые вкладки не попадают в
 * доступное дерево и в поиск по странице.
 */
export function Tabs({ items, activeId, onChange, children, label }: TabsProps) {
  const baseId = useId();
  const tabsRef = useRef<(HTMLButtonElement | null)[]>([]);

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") {
      return;
    }
    event.preventDefault();
    const offset = event.key === "ArrowRight" ? 1 : -1;
    const nextIndex = (index + offset + items.length) % items.length;
    const next = items[nextIndex];
    if (!next) {
      return;
    }
    onChange(next.id);
    tabsRef.current[nextIndex]?.focus();
  }

  return (
    <div className="tabs-block">
      <div className="tabs" role="tablist" aria-label={label}>
        {items.map((item, index) => {
          const isActive = item.id === activeId;
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              id={`${baseId}-tab-${item.id}`}
              aria-selected={isActive}
              // Панель рендерится только у активной вкладки, поэтому ссылка
              // aria-controls есть только там — висячих ссылок не остаётся.
              aria-controls={isActive ? `${baseId}-panel-${activeId}` : undefined}
              tabIndex={isActive ? 0 : -1}
              className={isActive ? "tabs__tab tabs__tab--active" : "tabs__tab"}
              ref={(element) => {
                tabsRef.current[index] = element;
              }}
              onClick={() => onChange(item.id)}
              onKeyDown={(event) => handleKeyDown(event, index)}
            >
              {item.label}
              {item.badge !== undefined && item.badge > 0 && (
                // Счётчик не входит в доступное имя вкладки: селекторы и
                // скринридеры видят стабильное «Комментарии».
                <span className="tabs__count" aria-hidden="true">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
      <div
        role="tabpanel"
        id={`${baseId}-panel-${activeId}`}
        aria-labelledby={`${baseId}-tab-${activeId}`}
        className="tab-panel"
      >
        {children}
      </div>
    </div>
  );
}
