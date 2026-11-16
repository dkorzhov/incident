import type { Incident } from "../api/types";

export interface DynamicsPoint {
  /** Локальная дата `yyyy-mm-dd`. */
  key: string;
  /** Подпись оси: `Пн`, `Вт`, … */
  label: string;
  /** Полная подпись для aria/tooltip: `16.11`. */
  fullLabel: string;
  created: number;
  closed: number;
}

const DAY_LABELS = ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"];
const CHART_WIDTH = 340;
const CHART_HEIGHT = 170;
const PADDING = { top: 16, right: 12, bottom: 26, left: 28 };

function localDateKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Динамика за последние `days` дней по данным реестра: «Создано» — по
 * `created_at`, «Закрыто» — по `updated_at` инцидентов в статусе Closed
 * (закрытый инцидент неизменяем, поэтому время закрытия точное).
 */
export function buildDynamics(incidents: Incident[], days = 7, now = new Date()): DynamicsPoint[] {
  // Без guard отрицательное значение сделало бы цикл бесконечным.
  if (days <= 0) {
    return [];
  }

  const points: DynamicsPoint[] = [];
  const byKey = new Map<string, DynamicsPoint>();

  for (let shift = days - 1; shift >= 0; shift -= 1) {
    const date = new Date(now.getFullYear(), now.getMonth(), now.getDate() - shift);
    const point: DynamicsPoint = {
      key: localDateKey(date),
      label: DAY_LABELS[date.getDay()] ?? "",
      fullLabel: `${String(date.getDate()).padStart(2, "0")}.${String(date.getMonth() + 1).padStart(2, "0")}`,
      created: 0,
      closed: 0,
    };
    points.push(point);
    byKey.set(point.key, point);
  }

  for (const incident of incidents) {
    const createdKey = localDateKey(new Date(incident.created_at));
    const createdPoint = byKey.get(createdKey);
    if (createdPoint) {
      createdPoint.created += 1;
    }

    if (incident.status === "Closed") {
      const closedPoint = byKey.get(localDateKey(new Date(incident.updated_at)));
      if (closedPoint) {
        closedPoint.closed += 1;
      }
    }
  }

  return points;
}

interface DynamicsChartProps {
  points: DynamicsPoint[];
}

/** График динамики созданных/закрытых инцидентов (SVG, без зависимостей). */
export function DynamicsChart({ points }: DynamicsChartProps) {
  const maxValue = Math.max(1, ...points.map((point) => Math.max(point.created, point.closed)));
  const innerWidth = CHART_WIDTH - PADDING.left - PADDING.right;
  const innerHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom;
  const step = points.length > 1 ? innerWidth / (points.length - 1) : 0;

  const x = (index: number) => PADDING.left + index * step;
  const y = (value: number) => PADDING.top + innerHeight - (value / maxValue) * innerHeight;

  const createdPath = points.map((point, index) => `${x(index)},${y(point.created)}`).join(" ");
  const closedPath = points.map((point, index) => `${x(index)},${y(point.closed)}`).join(" ");
  const gridValues = [0, Math.ceil(maxValue / 2), maxValue];

  const hasData = points.some((point) => point.created > 0 || point.closed > 0);

  return (
    <div className="dynamics">
      <div className="dynamics__legend">
        <span className="dynamics__legend-item dynamics__legend-item--created">Создано</span>
        <span className="dynamics__legend-item dynamics__legend-item--closed">Закрыто</span>
      </div>

      {hasData ? (
        <svg
          className="dynamics__svg"
          viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
          role="img"
          aria-label="Динамика инцидентов за 7 дней"
        >
          {gridValues.map((value) => (
            <g key={value}>
              <line
                x1={PADDING.left}
                x2={CHART_WIDTH - PADDING.right}
                y1={y(value)}
                y2={y(value)}
                stroke="#e6ecf5"
                strokeWidth="1"
              />
              <text
                x={PADDING.left - 8}
                y={y(value) + 4}
                textAnchor="end"
                className="dynamics__axis"
              >
                {value}
              </text>
            </g>
          ))}

          <polyline
            points={createdPath}
            fill="none"
            stroke="#2f6fed"
            strokeWidth="2.5"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
          <polyline
            points={closedPath}
            fill="none"
            stroke="#12805c"
            strokeWidth="2.5"
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {points.map((point, index) => (
            <g key={point.key}>
              <circle cx={x(index)} cy={y(point.created)} r="3.5" fill="#2f6fed">
                <title>{`${point.fullLabel}: создано ${point.created}`}</title>
              </circle>
              <circle cx={x(index)} cy={y(point.closed)} r="3.5" fill="#12805c">
                <title>{`${point.fullLabel}: закрыто ${point.closed}`}</title>
              </circle>
              <text
                x={x(index)}
                y={CHART_HEIGHT - 8}
                textAnchor="middle"
                className="dynamics__axis"
              >
                {point.label}
              </text>
            </g>
          ))}
        </svg>
      ) : (
        <p className="state-message__text dynamics__empty">
          За последние 7 дней инцидентов не создавали и не закрывали.
        </p>
      )}
    </div>
  );
}
