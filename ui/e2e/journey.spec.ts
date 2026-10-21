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

test("home: what the project does, then its stories; a story lights the parts of each step", async ({ page, isMobile }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}`);
  await expect(page.getByRole("heading", { name: "Ce que fait ce projet" })).toBeVisible();
  await expect(page.getByText("Une boutique de test").first()).toBeVisible();
  await page.getByRole("button", { name: /Passer une commande.*Lire l'histoire/ }).click();
  await expect(page.getByRole("heading", { name: "Passer une commande" })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Étape \d :/ })).toHaveCount(2);
  await expect(page.getByRole("button", { name: /^Étape 1 : Envoie POST \/orders/ })).toHaveAttribute("aria-current", "step");
  const cast = page.getByLabel("Qui intervient");
  if (!isMobile) {
    await expect(cast.getByText("Étape 1 :")).toBeVisible();
    await expect(cast.getByRole("button", { name: /Site web/ })).toBeVisible();
  }
  await page.getByRole("button", { name: /^Étape 2 :/ }).click();
  await expect(page).toHaveURL(/journey=order&step=2/);
  // Plain words first; the code only on demand.
  await page.getByRole("button", { name: "Détails pour développeur" }).click();
  await page.getByRole("button", { name: "api/app/orders.py:8–10" }).click();
  await expect(page.locator('[data-cited="true"]').first()).toContainText("def create_order");
});

test("a part: what it is for, the stories it takes part in, who it works with", async ({ page }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}?select=api`);
  await expect(page.getByRole("heading", { name: "API commandes" })).toBeVisible();
  await expect(page.getByRole("main").getByRole("button", { name: /Passer une commande/ })).toBeVisible();
  await expect(page.getByText("Avec qui elle travaille")).toBeVisible();
  await page.getByRole("button", { name: "Accueil du projet" }).first().click();
  await expect(page.getByRole("heading", { name: "Ce que fait ce projet" })).toBeVisible();
});

test("every part on one map, at a readable size", async ({ page, isMobile }) => {
  test.skip(isMobile, "the map is a desktop view");
  const project = await signIn(page);
  await page.goto(`/#/p/${project}?node=carte%3A`);
  await expect(page.getByRole("heading", { name: "Toutes les pièces" })).toBeVisible();
  await expect(page.locator(".react-flow__node")).toHaveCount(4);
  await page.locator('.react-flow__node[data-id="db"]').click();
  await expect(page.getByRole("heading", { name: "Base PostgreSQL" })).toBeVisible();
});

test("old journey links open the story", async ({ page }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}?node=parcours%3A&journey=order&step=abc`);
  await expect(page.getByRole("heading", { name: "Passer une commande" })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Étape 1 :/ })).toHaveAttribute("aria-current", "step"); // a bad step is step 1
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
