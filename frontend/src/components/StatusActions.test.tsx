import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { IncidentStatus } from "../api/client";
import { StatusActions } from "../components/StatusActions";

/** Переходы, которые отдаёт backend для каждого статуса (TASK.md §2). */
const TRANSITIONS: Record<IncidentStatus, IncidentStatus[]> = {
  New: ["In Progress"],
  "In Progress": ["Resolved"],
  Resolved: ["Closed"],
  Closed: [],
};

function renderActions(
  status: IncidentStatus,
  onChangeStatus = vi.fn().mockResolvedValue(true),
  pendingTarget: IncidentStatus | null = null,
) {
  render(
    <StatusActions
      transitions={TRANSITIONS[status]}
      onChangeStatus={onChangeStatus}
      pendingTarget={pendingTarget}
    />,
  );
  return onChangeStatus;
}

describe("StatusActions — кнопки по allowed_transitions", () => {
  it("для New показывает только «Взять в работу»", () => {
    renderActions("New");

    expect(screen.getByRole("button", { name: "Взять в работу" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Решить" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Закрыть" })).not.toBeInTheDocument();
  });

  it("для In Progress показывает «Решить» и не даёт закрыть напрямую", () => {
    renderActions("In Progress");

    expect(screen.getByRole("button", { name: "Решить" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Закрыть" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Взять в работу" })).not.toBeInTheDocument();
  });

  it("для Resolved показывает только «Закрыть»", () => {
    renderActions("Resolved");

    expect(screen.getByRole("button", { name: "Закрыть" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Решить" })).not.toBeInTheDocument();
  });

  it("для Closed не рисует ни одной кнопки действия", () => {
    renderActions("Closed");

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(
      screen.getByText("Инцидент закрыт: действий по статусу нет", { exact: false }),
    ).toBeInTheDocument();
  });

  it("передаёт целевой статус в обработчик смены статуса", async () => {
    const onChangeStatus = renderActions("New");

    fireEvent.click(screen.getByRole("button", { name: "Взять в работу" }));

    await waitFor(() => {
      expect(onChangeStatus).toHaveBeenCalledWith("In Progress");
    });
  });

  it("блокирует действия, пока переход выполняется", () => {
    renderActions("New", vi.fn().mockResolvedValue(true), "In Progress");

    const button = screen.getByRole("button", { name: /Выполняем/ });
    expect(button).toBeDisabled();
  });
});

describe("StatusActions — форма решения", () => {
  it("не отправляет resolve без текста и показывает ошибку", async () => {
    const onChangeStatus = vi.fn().mockResolvedValue(true);
    renderActions("In Progress", onChangeStatus);

    fireEvent.click(screen.getByRole("button", { name: "Решить" }));
    fireEvent.change(screen.getByLabelText("Описание решения (обязательно)"), {
      target: { value: "   " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Подтвердить решение" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Опишите решение");
    expect(onChangeStatus).not.toHaveBeenCalled();
    // Форма остаётся открытой, чтобы пользователь дописал текст.
    expect(screen.getByLabelText("Описание решения (обязательно)")).toBeInTheDocument();
  });

  it("отправляет Resolved с непустым resolution", async () => {
    const onChangeStatus = vi.fn().mockResolvedValue(true);
    renderActions("In Progress", onChangeStatus);

    fireEvent.click(screen.getByRole("button", { name: "Решить" }));
    fireEvent.change(screen.getByLabelText("Описание решения (обязательно)"), {
      target: { value: "Перезапущен шлюз" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Подтвердить решение" }));

    await waitFor(() => {
      expect(onChangeStatus).toHaveBeenCalledWith("Resolved", "Перезапущен шлюз");
    });
    // При успехе форма закрывается.
    await waitFor(() => {
      expect(screen.queryByLabelText("Описание решения (обязательно)")).not.toBeInTheDocument();
    });
  });

  it("оставляет форму открытой, если сервер отклонил переход", async () => {
    const onChangeStatus = vi.fn().mockResolvedValue(false);
    renderActions("In Progress", onChangeStatus);

    fireEvent.click(screen.getByRole("button", { name: "Решить" }));
    fireEvent.change(screen.getByLabelText("Описание решения (обязательно)"), {
      target: { value: "Проверено" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Подтвердить решение" }));

    await waitFor(() => {
      expect(onChangeStatus).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByLabelText("Описание решения (обязательно)")).toHaveValue("Проверено");
    });
  });
});
