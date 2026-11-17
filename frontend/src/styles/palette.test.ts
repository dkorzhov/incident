import { describe, expect, it } from "vitest";
import chart from "../components/PriorityChart.tsx?raw";
// Исходники читаем как текст: проверяем, что цвет приоритета задан в одном
// месте (CSS-переменные), а не захардкожен в компоненте диаграммы.
import css from "../styles/global.css?raw";

/** Значение CSS-переменной из `:root`. */
function cssVar(name: string): string {
  const match = css.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`));
  const value = match?.[1];
  if (!value) {
    throw new Error(`CSS-переменная --${name} не найдена`);
  }
  return value.toLowerCase();
}

function channels(hex: string): [number, number, number] {
  return [1, 3, 5].map((index) => Number.parseInt(hex.slice(index, index + 2), 16)) as [
    number,
    number,
    number,
  ];
}

/** Контраст текста и фона по WCAG 2.x. */
function contrast(fgHex: string, bgHex: string): number {
  const channel = (value: number) => {
    const c = value / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  const luminance = (hex: string) => {
    const [r, g, b] = channels(hex);
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
  };
  const [lighter, darker] = [luminance(fgHex), luminance(bgHex)].sort((a, b) => b - a) as [
    number,
    number,
  ];
  return (lighter + 0.05) / (darker + 0.05);
}

describe("палитра приоритетов", () => {
  it("Medium — жёлтый и заметно отличается от оранжевого High (TASK.md §4)", () => {
    const medium = cssVar("priority-medium");
    const high = cssVar("priority-high");

    expect(medium).not.toBe(high);

    const [mr, mg, mb] = channels(medium);
    const [hr, hg] = channels(high);

    // Жёлтый: красный и зелёный высокие, синий низкий.
    expect(mr).toBeGreaterThan(200);
    expect(mg).toBeGreaterThan(140);
    expect(mb).toBeLessThan(80);
    // High — оранжевый (красный заметно выше зелёного).
    expect(hr - hg).toBeGreaterThan(60);
  });

  it("текст каждого бейджа приоритета читаем на своём фоне (AA, ≥4.5:1)", () => {
    for (const priority of ["critical", "high", "medium", "low"]) {
      const fg = cssVar(`priority-${priority}-fg`);
      const bg = cssVar(`priority-${priority}-bg`);
      expect(contrast(fg, bg), `${priority}: ${fg} на ${bg}`).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("сегменты диаграммы и точки легенды берут те же переменные, что бейджи", () => {
    // В TSX нет собственных оттенков — единственный источник цвета CSS.
    expect(chart).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    for (const priority of ["critical", "high", "medium", "low"]) {
      expect(chart).toContain(`var(--priority-${priority})`);
    }

    // Точки легенды Medium/Low больше не на старом хардкоде.
    for (const priority of ["critical", "high", "medium", "low"]) {
      expect(css).toMatch(
        new RegExp(
          `\\.priority-chart__dot\\.badge--priority-${priority}\\s*{\\s*background:\\s*var\\(--priority-${priority}\\);`,
        ),
      );
    }
  });
});
