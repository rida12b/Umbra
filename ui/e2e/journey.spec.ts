import { readFileSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

const state = () =>
  JSON.parse(readFileSync(new URL(".state.json", import.meta.url), "utf-8")) as { project: string; token: string };

/** Two clicks 150 ms apart, as a person double-clicks (Playwright's own dblclick is instantaneous). */
async function open(page: Page, key: string): Promise<void> {
  const block = page.locator(`.react-flow__node[data-id="${key}"]`);
  await block.click();
  await page.waitForTimeout(150);
  await block.click();
}

/** A fresh one-time login, as `umbra-engine open` would give: the token stays out of the browser. */
async function signIn(page: Page): Promise<string> {
  const { project, token } = state();
  const secret = readFileSync(token, "utf-8").trim();
  const minted = await page.request.post("/v1/ui/login-codes", { headers: { Authorization: `Bearer ${secret}` } });
  const { code } = (await minted.json()) as { code: string };
  await page.goto(`/#login=${code}`);
  await expect(page.getByRole("heading", { name: "Projets" })).toBeVisible();
  expect(page.url()).not.toContain(code); // the code leaves the address bar at once
  return project;
}

test("a journey as a sequence: blocks across, steps in order, linked with the step list", async ({ page, isMobile }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}`);
  await expect(page.getByText("Une boutique de test").first()).toBeVisible();
  if (isMobile) await page.getByLabel("Suivre un parcours").selectOption("order");
  else await page.getByRole("region", { name: "Parcours" }).getByRole("button", { name: /Passer une commande/ }).click();
  await expect(page.getByRole("heading", { name: "Passer une commande" })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Étape \d$/ })).toHaveCount(2);
  // Plain words first; the code only on demand.
  await page.getByRole("button", { name: "Détail technique et code" }).click();
  await page.getByRole("button", { name: "web/src/app.ts:1–3" }).click();
  await expect(page.locator('[data-cited="true"]').first()).toContainText("submit");
  if (isMobile) return; // phones get the step list without the diagram
  const map = page.getByRole("region", { name: "Carte de l'architecture" });
  await expect(map.getByRole("button", { name: /Envoie POST \/orders/ })).toBeVisible(); // the short action
  await expect(map.getByRole("button", { name: /Base PostgreSQL/ })).toBeVisible(); // a block the journey reaches
  await expect(map.getByRole("button", { name: /^Client/ })).toHaveCount(0); // a block it does not
  await map.getByRole("button", { name: /^Étape 2 :/ }).click();
  await expect(page).toHaveURL(/journey=order&step=2/);
  await page.getByRole("button", { name: "Détail technique et code" }).click();
  await page.getByRole("button", { name: "api/app/orders.py:8–10" }).click();
  await expect(page.locator('[data-cited="true"]').first()).toContainText("def create_order");
});

test("old journey links open the journey on the architecture", async ({ page }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}?node=parcours%3A&journey=order&step=abc`);
  await expect(page.getByRole("heading", { name: "Passer une commande" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Étape 1", exact: true })).toHaveAttribute("aria-current", "step"); // a bad step is step 1
  await expect(page.getByText("NaN")).toHaveCount(0);
});

test("code map down to a function, back up with the breadcrumbs", async ({ page, isMobile }) => {
  test.skip(isMobile, "the graph is a list on phones; covered by the next test");
  const project = await signIn(page);
  await page.goto(`/#/p/${project}?node=app%3A`);
  await open(page, "service:api");
  await open(page, "dir:api/app");
  await open(page, "api/app/orders.py");
  const fn = page.locator('.react-flow__node[data-id="api/app/orders.py::create_order"]');
  await expect(fn).toBeVisible();
  await expect(page.locator(".react-flow__edge.link-hypothesis")).toHaveCount(1); // create_order calls validate
  await fn.click();
  await expect(page.getByLabel("Explication et preuves")).toContainText("create_order");
  await page.getByRole("navigation", { name: "Niveaux" }).getByRole("link", { name: "shop" }).click();
  await expect(page.locator('.react-flow__node[data-id="service:api"]')).toBeVisible();
});

test("search jumps to a function and selects it", async ({ page }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}?node=app%3A`);
  await expect(page.getByRole("navigation", { name: "Vues" })).toBeVisible(); // the shortcut exists once the page is up
  await page.keyboard.press("Control+k");
  await page.getByRole("combobox", { name: "Chercher dans le projet" }).fill("validate");
  await page.getByRole("option", { name: /validate/ }).first().click();
  await expect(page).toHaveURL(/select=api%2Fapp%2Forders\.py%3A%3Avalidate/);
  await expect(page.getByLabel("Explication et preuves")).toContainText("validate");
});
