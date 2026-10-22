import { readFileSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

const state = () =>
  JSON.parse(readFileSync(new URL(".state.json", import.meta.url), "utf-8")) as { project: string; token: string };

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

test("the parts in their zones; a click explains, « Entrer dedans » zooms in, Échap comes back", async ({ page, isMobile }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}`);
  const trail = page.getByRole("navigation", { name: "Où vous êtes" });
  await expect(trail).toContainText("Les pièces");
  if (isMobile) {
    await page.getByRole("button", { name: /API commandes/ }).first().click();
  } else {
    for (const zone of ["Qui l'utilise", "Ce qui reçoit", "Ce qui traite", "Où c'est rangé"])
      await expect(page.getByText(zone, { exact: true })).toBeVisible();
    await page.locator('.react-flow__node[data-id="api"]').click();
  }
  const panel = page.getByLabel("Explication");
  await expect(panel.getByRole("heading", { name: "API commandes" })).toBeVisible();
  await panel.getByRole("button", { name: /Entrer dedans/ }).click();
  await expect(page).toHaveURL(/node=x%3Apart%3Aapi/);
  await expect(trail).toContainText("API commandes");
  await expect(page.getByText("Commandes", { exact: true }).first()).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page).toHaveURL(/node=x%3Aparts/);
});

test("a data path played on the map, step by step, with its code on demand", async ({ page }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}`);
  await page.getByLabel("Explication").getByRole("button", { name: /Passer une commande/ }).click();
  await expect(page).toHaveURL(/journey=order&step=1/);
  const bar = page.getByLabel("Chemin de données en lecture");
  await expect(bar).toContainText("Envoie POST /orders"); // the short action
  await bar.getByRole("button", { name: "Étape suivante" }).click();
  await expect(page).toHaveURL(/journey=order&step=2/);
  await expect(bar).toContainText("L'API valide puis"); // a step without action: its first words
  const panel = page.getByLabel("Explication");
  await panel.getByText("Détails pour développeur (étape 2)").click();
  await panel.getByRole("button", { name: "api/app/orders.py:8–10" }).click();
  await expect(page.locator('[data-cited="true"]').first()).toContainText("def create_order");
});

test("from a part down to its functions, on the same map", async ({ page, isMobile }) => {
  test.skip(isMobile, "the code level is a desktop map");
  const project = await signIn(page);
  await page.goto(`/#/p/${project}?node=x%3Apart%3Aapi`);
  await page.locator('.react-flow__node[data-id="orders"]').getByRole("button", { name: /Entrer dedans/ }).click();
  await expect(page).toHaveURL(/node=x%3Acomponent%3Aorders/);
  await page.locator('.react-flow__node').getByRole("button", { name: /Entrer dedans/ }).first().click();
  await expect(page.locator('.react-flow__node[data-id="api/app/orders.py::create_order"]')).toBeVisible();
  await expect(page.locator(".react-flow__edge.link-hypothesis")).toHaveCount(1); // create_order calls validate
});

test("old links open the parts with the path playing", async ({ page }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}?node=parcours%3A&journey=order&step=abc`);
  await expect(page.getByLabel("Chemin de données en lecture")).toContainText("étape 1 sur 2"); // a bad step is step 1
  await expect(page.getByText("NaN")).toHaveCount(0);
});

test("search jumps to a function and selects it", async ({ page }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}`);
  await expect(page.getByRole("navigation", { name: "Où vous êtes" })).toBeVisible(); // the shortcut exists once the page is up
  await page.keyboard.press("Control+k");
  await page.getByRole("combobox", { name: "Chercher dans le projet" }).fill("validate");
  await page.getByRole("option", { name: /validate/ }).first().click();
  await expect(page).toHaveURL(/select=api%2Fapp%2Forders\.py%3A%3Avalidate/);
  await expect(page.getByLabel("Explication et preuves")).toContainText("validate");
});
