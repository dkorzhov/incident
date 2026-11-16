import { expect, test } from "@playwright/test";

test.describe("Каркас приложения", () => {
  test("главная открывается и показывает сайдбар", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("link", { name: "Дашборд" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Инциденты" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Пользователи" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Дашборд", level: 1 })).toBeVisible();
  });

  test("backend отвечает на /api/health", async ({ request }) => {
    const response = await request.get("/api/health");

    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.status).toBe("ok");
  });
});