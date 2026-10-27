import { readFileSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

const state = () =>
  JSON.parse(readFileSync(new URL(".state.json", import.meta.url), "utf-8")) as { project: string; token: string; spare: string };

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

const cells = (page: Page) =>
  page.locator("[data-box]").evaluateAll((boxes) => boxes.map((b) => `${b.getAttribute("data-box")}@${JSON.stringify((b as SVGGraphicsElement).getBBox())}`));

test("a project opens on its map: who comes in, the parts, what leaves; the proof on hover; nothing scrolls", async ({ page }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}`);
  await expect(page.getByRole("heading", { name: "shop" })).toBeVisible();
  await expect(page.getByText("Une appli web : on gère des « orders ».")).toBeVisible(); // what it is for, from its tables
  for (const name of ["Utilisateur", "Application web", "Serveur", "Base"]) await expect(page.getByRole("button", { name: new RegExp(`^${name}`) })).toBeVisible();
  await expect(page.getByText("ENTRÉE")).toBeVisible();
  await expect(page.getByLabel("Sortie : ligne enregistrée")).toBeVisible();
  await expect(page.getByLabel("Sortie : écran mis à jour")).toBeVisible();
  await expect(page.getByLabel("Où on en est")).toContainText(/pas d'historique git|branche/);
  await expect(page.getByLabel("Où on en est")).toContainText("à définir avec toi");
  await expect(page.getByRole("button", { name: "Ce qu'on peut faire (1)" })).toBeVisible();
  // The page never scrolls; on a phone only the map itself slides sideways, its words kept readable.
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollHeight <= document.documentElement.clientHeight)).toBe(true);

  await page.getByRole("button", { name: /^Serveur/ }).focus(); // keyboard too: the same card as the mouse
  await expect(page.getByRole("tooltip")).toContainText("api/app/main.py:5");
  await expect(page.getByRole("tooltip")).toContainText("clic : voir dedans →"); // a part with an inside (#105)
  await page.getByLabel("Application web appelle Serveur").hover();
  await expect(page.getByRole("tooltip")).toContainText("web/src/app.ts:2");
});

test("the map does not move on reload", async ({ page }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}`);
  await expect(page.getByRole("button", { name: /^Serveur/ })).toBeVisible();
  const before = await cells(page);
  await page.reload();
  await expect(page.getByRole("button", { name: /^Serveur/ })).toBeVisible();
  expect(await cells(page)).toEqual(before);
});

test("« + N outils autour » unfolds what does not make the app run; « ? » explains how to read the map", async ({ page, isMobile }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}`);
  const around = page.getByRole("button", { name: /outils autour/ });
  if (isMobile) await around.click();
  else await around.hover();
  await expect(page.getByText("Autour du projet : ne fait pas tourner l'appli")).toBeVisible();
  await expect(page.getByText("Documentation", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Aide : comment lire la carte" }).click();
  await expect(page.getByRole("dialog", { name: "Lire la carte" })).toContainText("pointillés = supposé");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Lire la carte" })).toHaveCount(0);
});

test("a project added while the engine runs is read, then opens on its map (#85)", async ({ page }) => {
  await signIn(page);
  const { token, spare } = state();
  const secret = readFileSync(token, "utf-8").trim();
  const added = await page.request.post("/v1/projects", { headers: { Authorization: `Bearer ${secret}` }, data: { path: spare } });
  const { id } = (await added.json()) as { id: string };
  await page.goto(`/#/p/${id}`);
  await expect(page.getByRole("button", { name: /^Serveur/ })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("a échoué")).toHaveCount(0);
});

test("a failed read says so, offers « Réessayer », and the retry opens the map", async ({ page }) => {
  const project = await signIn(page);
  const system = `**/v1/projects/${project}/system`;
  await page.route(system, (route) =>
    route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "reading the project failed: OSError: file locked" }) }),
  );
  await page.goto(`/#/p/${project}`);
  await expect(page.getByRole("heading", { name: "La lecture du projet a échoué" })).toBeVisible();
  await expect(page.getByText("file locked")).toBeVisible();
  await page.unroute(system); // the cause went away
  await page.getByRole("button", { name: "Réessayer" }).click();
  await expect(page.getByRole("button", { name: /^Serveur/ })).toBeVisible();
});

test("Claude's activity is one click away and comes back to the map", async ({ page }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}`);
  await page.getByRole("button", { name: "Activité de Claude" }).click();
  await expect(page).toHaveURL(/node=activite/);
  await page.getByRole("button", { name: "Vue d'ensemble" }).click();
  await expect(page.getByRole("button", { name: /^Serveur/ })).toBeVisible();
});
