import { expect, type Page, test } from "@playwright/test";

/**
 * Главный e2e-сценарий TASK.md §5: создать → назначить → взять в работу →
 * решить с resolution → закрыть, с комментарием и историей в карточке.
 *
 * Правила сценария:
 * - никаких `sleep`: синхронизация только по состоянию UI (`expect().toBeVisible`,
 *   `toHaveURL`) и по ответам API (`waitForResponse`);
 * - данные уникальны на прогон (метка времени в названии), поэтому тесты не
 *   конфликтуют при повторных и параллельных прогонах;
 * - сценарий не опирается на количество инцидентов в БД и на demo-seed:
 *   он работает и на пустой базе.
 */

const RUN_ID = `${Date.now()}-${Math.floor(Math.random() * 1000)}`;

/** Уникальное название инцидента: 5–120 символов, видно в реестре. */
function uniqueTitle(kind: string): string {
  return `E2E ${kind} ${RUN_ID}`;
}

/** Выбрать текущего пользователя через UI (а не только через localStorage). */
async function selectCurrentUser(page: Page): Promise<string> {
  const select = page.getByLabel("Текущий пользователь");
  await expect(select).toBeEnabled();

  const options = select.locator("option");
  await expect(options.first()).toBeAttached();
  // Второй пользователь, а не автоматически выбранный первый: так проверяем
  // именно ручной выбор в шапке и что он реально уходит в X-User-Id.
  await select.selectOption({ index: 1 });

  const value = await select.inputValue();
  expect(value).not.toBe("");
  const name = (await options.nth(1).textContent())?.trim();
  expect(name).toBeTruthy();
  return name as string;
}

test.describe("Жизненный цикл инцидента", () => {
  test("создать → назначить → взять в работу → решить → закрыть", async ({ page }) => {
    const title = uniqueTitle("жизненный цикл");
    const description = `Проверка полного пути через UI, прогон ${RUN_ID}.`;
    const commentText = `Комментарий проверки ${RUN_ID}`;
    const resolutionText = `Перезапущен сервис, проблема ушла (прогон ${RUN_ID}).`;

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Дашборд", level: 1 })).toBeVisible();
    const currentUserName = await selectCurrentUser(page);

    // --- создать ----------------------------------------------------------
    await page.goto("/incidents/new");
    // «Новый инцидент» есть и в topbar (h1), и в заголовке страницы (h2): берём первый.
    await expect(
      page.getByRole("heading", { name: "Новый инцидент" }).first(),
    ).toBeVisible();

    await page.getByLabel("Название").fill(title);
    await page.getByLabel("Описание").fill(description);
    await page.getByLabel("Категория").selectOption("Portal");
    await page.getByLabel("Приоритет").selectOption("High");

    const createResponse = page.waitForResponse(
      (response) =>
        response.url().includes("/api/incidents") &&
        response.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Создать инцидент" }).click();

    const created = await createResponse;
    expect(created.status()).toBe(201);
    const incidentId = ((await created.json()) as { id: string }).id;
    expect(incidentId).toMatch(/^INC-\d+$/);

    // Карточка созданного инцидента: номер и название из ответа сервера.
    await expect(page).toHaveURL(new RegExp(`/incidents/${incidentId}$`));
    await expect(page.getByText(`${incidentId} · ${title}`)).toBeVisible();
    await expect(page.locator('[data-status="New"]')).toBeVisible();
    await expect(page.locator('[data-priority="High"]')).toBeVisible();

    // --- назначить --------------------------------------------------------
    // Создавали без ответственного: назначение — отдельный PATCH из карточки.
    const assigneeSelect = page.getByLabel("Ответственный");
    await expect(assigneeSelect).toBeEnabled();
    const assigneeValue = await assigneeSelect
      .locator("option")
      .nth(1)
      .getAttribute("value");
    expect(assigneeValue).toBeTruthy();

    const assignResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith(`/api/incidents/${incidentId}`) &&
        response.request().method() === "PATCH",
    );
    await assigneeSelect.selectOption(assigneeValue as string);
    expect((await assignResponse).status()).toBe(200);
    await expect(assigneeSelect).toHaveValue(assigneeValue as string);
    await expect(page.locator(".incident-card__assignee")).not.toContainText("Не назначен");

    // --- взять в работу ---------------------------------------------------
    const takeResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith(`/api/incidents/${incidentId}/status`) &&
        response.request().method() === "PATCH",
    );
    await page.getByRole("button", { name: "Взять в работу" }).click();
    expect((await takeResponse).status()).toBe(200);
    await expect(page.locator('[data-status="In Progress"]')).toBeVisible();
    await expect(page.getByRole("button", { name: "Взять в работу" })).toHaveCount(0);

    // --- решить с resolution ---------------------------------------------
    await expect(page.getByRole("button", { name: "Решить" })).toBeVisible();
    await page.getByRole("button", { name: "Решить" }).click();
    await page.getByLabel("Описание решения (обязательно)").fill(resolutionText);

    const resolveResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith(`/api/incidents/${incidentId}/status`) &&
        response.request().method() === "PATCH",
    );
    await page.getByRole("button", { name: "Подтвердить решение" }).click();
    expect((await resolveResponse).status()).toBe(200);
    await expect(page.locator('[data-status="Resolved"]')).toBeVisible();

    // Решение видно в карточке (вкладка «Информация»).
    await expect(page.getByText("Решение", { exact: true })).toBeVisible();
    await expect(page.getByText(resolutionText)).toBeVisible();

    // --- комментарий ------------------------------------------------------
    await page.getByRole("tab", { name: "Комментарии" }).click();
    await expect(page.getByText("Комментариев пока нет")).toBeVisible();
    await page.getByLabel("Новый комментарий").fill(commentText);

    const commentResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith(`/api/incidents/${incidentId}/comments`) &&
        response.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Добавить комментарий" }).click();
    expect((await commentResponse).status()).toBe(201);
    await expect(page.getByText(commentText)).toBeVisible();
    // Автор — в списке комментариев; имя также встречается в <option> селектов.
    await expect(
      page.locator(".comment__author").filter({ hasText: currentUserName }),
    ).toBeVisible();

    // --- история ----------------------------------------------------------
    await page.getByRole("tab", { name: "История" }).click();
    // События пишутся автоматически на каждое действие: создание, назначение,
    // два перехода статуса, решение и комментарий.
    await expect(page.getByText("Инцидент создан")).toBeVisible();
    await expect(page.getByText("Назначение", { exact: true })).toBeVisible();
    await expect(page.getByText("Комментарий", { exact: true })).toBeVisible();
    await expect(page.getByText("Решение", { exact: true })).toBeVisible();
    await expect(page.getByText(resolutionText.slice(0, 40)).first()).toBeVisible();

    // --- закрыть ----------------------------------------------------------
    const closeResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith(`/api/incidents/${incidentId}/status`) &&
        response.request().method() === "PATCH",
    );
    await page.getByRole("button", { name: "Закрыть" }).click();
    expect((await closeResponse).status()).toBe(200);
    await expect(page.locator('[data-status="Closed"]')).toBeVisible();

    // --- Closed неизменяем: действий и формы комментария нет --------------
    await expect(
      page.getByText("Инцидент закрыт: действий по статусу нет", { exact: false }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Взять в работу" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Решить" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Закрыть" })).toHaveCount(0);
    await expect(page.getByLabel("Ответственный")).toBeDisabled();

    await page.getByRole("tab", { name: "Комментарии" }).click();
    await expect(page.getByLabel("Новый комментарий")).toHaveCount(0);
    await expect(
      page.getByText("Инцидент закрыт: новые комментарии сервер не принимает (409)."),
    ).toBeVisible();
  });
});

test.describe("Границы автомата статусов", () => {
  test("сервер блокирует недопустимый переход (409) и resolve без resolution (400)", async ({
    request,
  }) => {
    const usersResponse = await request.get("/api/users");
    expect(usersResponse.ok()).toBeTruthy();
    const users = (await usersResponse.json()) as { id: number }[];
    expect(users.length).toBeGreaterThan(0);
    const headers = { "X-User-Id": String(users[0].id) };

    const createdResponse = await request.post("/api/incidents", {
      headers,
      data: {
        title: uniqueTitle("границы автомата"),
        description: "Проверка 409/400 на уровне API",
        category: "Network",
        priority: "Medium",
      },
    });
    expect(createdResponse.status()).toBe(201);
    const { id } = (await createdResponse.json()) as { id: string };

    // Закрыть напрямую из New нельзя.
    const closeFromNew = await request.patch(`/api/incidents/${id}/status`, {
      headers,
      data: { status: "Closed" },
    });
    expect(closeFromNew.status()).toBe(409);
    expect((await closeFromNew.json()).detail).toBeTruthy();

    // Перепрыгнуть In Progress нельзя.
    const resolveFromNew = await request.patch(`/api/incidents/${id}/status`, {
      headers,
      data: { status: "Resolved", resolution: "Пробую в обход автомата" },
    });
    expect(resolveFromNew.status()).toBe(409);

    const inProgress = await request.patch(`/api/incidents/${id}/status`, {
      headers,
      data: { status: "In Progress" },
    });
    expect(inProgress.status()).toBe(200);

    // Resolved без resolution — 400 с ошибкой поля.
    const resolveWithoutResolution = await request.patch(
      `/api/incidents/${id}/status`,
      { headers, data: { status: "Resolved" } },
    );
    expect(resolveWithoutResolution.status()).toBe(400);

    // Resolved с пробельным resolution — тоже 400.
    const resolveBlank = await request.patch(`/api/incidents/${id}/status`, {
      headers,
      data: { status: "Resolved", resolution: "   " },
    });
    expect(resolveBlank.status()).toBe(400);

    // Легальный маршрут после отказов работает.
    const resolved = await request.patch(`/api/incidents/${id}/status`, {
      headers,
      data: { status: "Resolved", resolution: "Перезапущен сетевой сервис" },
    });
    expect(resolved.status()).toBe(200);
    expect((await resolved.json()).status).toBe("Resolved");
  });
});