import { useMemo } from "react";

import type { HistoryEvent } from "../api/types";
import { describeHistoryEvent, HISTORY_TYPE_LABELS } from "../utils/history";
import { formatDateTime } from "../utils/labels";
import { StateMessage } from "./StateMessage";

interface HistoryListProps {
  events: readonly HistoryEvent[];
}

/**
 * История изменений: тип события, актор, время и описание «было → стало».
 *
 * Описание строит `describeHistoryEvent` по `payload` backend, поэтому новые
 * поля в payload не требуют правок разметки — они попадут в текст как
 * «поле: было → стало».
 */
export function HistoryList({ events }: HistoryListProps) {
  // Свежие события сверху: так последнее действие видно без прокрутки.
  // Копия и разворот — только при смене данных, а не на каждом рендере.
  const ordered = useMemo(() => [...events].reverse(), [events]);

  if (events.length === 0) {
    return (
      <StateMessage
        title="История пуста"
        text="Записи появляются автоматически при создании, смене полей, статуса и комментариях."
      />
    );
  }

  return (
    <ol className="history-list">
      {ordered.map((event) => (
        <li key={event.id} className="history-item">
          <span
            className={`history-item__dot history-item__dot--${event.type}`}
            aria-hidden="true"
          />
          <div className="history-item__body">
            <p className="history-item__title">
              <span className="history-item__type">{HISTORY_TYPE_LABELS[event.type]}</span>
              <span className="history-item__actor">{event.actor.name}</span>
              <time className="history-item__time" dateTime={event.created_at}>
                {formatDateTime(event.created_at)}
              </time>
            </p>
            <p className="history-item__description">
              {describeHistoryEvent(event.type, event.payload)}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}
