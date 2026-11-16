import type { PriorityCounts } from "../api/types";
import { INCIDENT_PRIORITIES } from "../api/types";
import { PRIORITY_LABELS, priorityModifier } from "../utils/labels";

/** Цвет сегмента диаграммы — тот же, что у бейджа приоритета. */
const PRIORITY_COLORS: Record<string, string> = {
  Critical: "#d92d20",
  High: "#f79009",
  Medium: "#eaaa08",
  Low: "#6172f3",
};

interface PriorityChartProps {
  byPriority: PriorityCounts;
}

/** Кольцевая диаграмма по приоритетам (SVG, без внешних библиотек). */
export function PriorityChart({ byPriority }: PriorityChartProps) {
  const total = INCIDENT_PRIORITIES.reduce((sum, priority) => sum + byPriority[priority], 0);
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <div className="priority-chart" data-testid="priority-chart">
      <div className="priority-chart__donut">
        <svg viewBox="0 0 140 140" role="img" aria-label="Инциденты по приоритетам">
          <circle cx="70" cy="70" r={radius} fill="none" stroke="#eef2f7" strokeWidth="18" />
          {total > 0 &&
            INCIDENT_PRIORITIES.map((priority) => {
              const value = byPriority[priority];
              if (value === 0) {
                return null;
              }
              const length = (value / total) * circumference;
              const segment = (
                <circle
                  key={priority}
                  cx="70"
                  cy="70"
                  r={radius}
                  fill="none"
                  stroke={PRIORITY_COLORS[priority] ?? "#94a3b8"}
                  strokeWidth="18"
                  strokeDasharray={`${length} ${circumference - length}`}
                  strokeDashoffset={-offset}
                  transform="rotate(-90 70 70)"
                />
              );
              offset += length;
              return segment;
            })}
        </svg>
        <div className="priority-chart__center">
          <strong>{total}</strong>
          <span>всего</span>
        </div>
      </div>

      <ul className="priority-chart__legend">
        {INCIDENT_PRIORITIES.map((priority) => (
          <li key={priority} className="priority-chart__legend-item">
            <span
              className={`priority-chart__dot badge ${priorityModifier(priority)}`}
              aria-hidden="true"
            />
            <span className="priority-chart__legend-label">{PRIORITY_LABELS[priority]}</span>
            <span className="priority-chart__legend-value">{byPriority[priority]}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
