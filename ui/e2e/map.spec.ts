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

test("a question asked in Claude Code lights its answer on the open map within 2 s; « effacer » goes back (#104)", async ({ page, isMobile }) => {
  test.skip(isMobile, "one tab is enough: the highlight is shared by every tab of the Project");
  const project = await signIn(page);
  const { token } = state();
  const headers = { Authorization: `Bearer ${readFileSync(token, "utf-8").trim()}` };
  await page.goto(`/#/p/${project}`);
  await expect(page.getByRole("button", { name: /^Serveur/ })).toBeVisible();
  // What the MCP tool `show` posts for Claude Code: an unknown box is refused with the valid ones.
  const refused = await page.request.post(`/v1/projects/${project}/show`, { headers, data: { caption: "x", parts: ["Serveurs"] } });
  expect(refused.status()).toBe(422);
  expect(((await refused.json()) as { detail: string }).detail).toContain("Serveur");
  const path = [{ part: "api/app/orders.py", note: "ajouter le champ", why: "Order décrit une commande." }, { part: "web/src/app.ts", note: "vérifier" }];
  const shown = await page.request.post(`/v1/projects/${project}/show`, { headers, data: { caption: "où j'ajoute un champ prix à Order ?", parts: ["Base"], path } });
  expect(shown.status()).toBe(200);
  const bar = page.getByRole("region", { name: "Question posée dans Claude Code" });
  await expect(bar).toContainText("« où j'ajoute un champ prix à Order ? »", { timeout: 2_000 });
  await expect(page.getByLabel("2 app.ts : vérifier")).toBeVisible();
  await expect(page.getByLabel("1 orders.py : ajouter le champ")).toBeVisible();
  await page.getByLabel("1 orders.py : ajouter le champ").hover();
  await expect(page.getByRole("tooltip")).toContainText("Order décrit une commande.");
  await bar.getByRole("button", { name: "copier pour Claude" }).click();
  await expect(page.getByRole("status")).toHaveText("Copié");
  await bar.getByRole("button", { name: "effacer" }).click();
  await expect(bar).toHaveCount(0);
  expect(await (await page.request.get(`/v1/projects/${project}/show`, { headers })).json()).toBeNull();
});

test("a click on a box zooms into it: its parts, its neighbours as stubs, the proof on hover; Esc goes up (#105)", async ({ page }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}`);
  await page.getByRole("button", { name: /^Serveur/ }).click();
  await expect(page).toHaveURL(/box=server/);
  const crumbs = page.getByRole("navigation", { name: "Où vous êtes" });
  await expect(crumbs.getByRole("button", { name: "Vue d'ensemble" })).toBeVisible();
  await expect(crumbs.locator("[aria-current=page]")).toHaveText("Serveur");
  await expect(page.getByRole("heading", { name: /Serveur/ })).toContainText("api/app/");
  await expect(page.getByRole("button", { name: /^Porte d'entrée/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "depuis, Application web" })).toBeVisible();
  await expect(page.getByText("ENTRÉE", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /^Porte d'entrée/ }).focus(); // keyboard too: the same card as the mouse
  await expect(page.getByRole("tooltip")).toContainText("api/app/main.py:5");
  await page.keyboard.press("Escape"); // nothing selected: up to Level 0
  await expect(page).not.toHaveURL(/box=/);
  await expect(page.getByRole("button", { name: /^Serveur/ })).toBeVisible();

  // Enter on a focused box zooms in too; a stub goes back to that neighbour, selected on Level 0.
  await page.getByRole("button", { name: /^Serveur/ }).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: /^vers Base/ }).click();
  await expect(page).not.toHaveURL(/box=/);
  await expect(page.getByRole("button", { name: /^Base/ })).toHaveAttribute("aria-pressed", "true");
});

test("Back after zooming in comes back to the whole map; a link to an inside opens it (#105)", async ({ page }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}?box=server%3Aapi`);
  await expect(page.getByRole("button", { name: /^Porte d'entrée/ })).toBeVisible();
  await page.getByRole("button", { name: "Vue d'ensemble" }).click();
  await expect(page.getByRole("button", { name: /^Serveur/ })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("button", { name: /^Porte d'entrée/ })).toBeVisible();
});

test("a question answered from Claude Code while a box is open lights it on the whole map; a file inside lights its box (#104, #105)", async ({ page, isMobile }) => {
  test.skip(isMobile, "one tab is enough: the highlight is shared by every tab of the Project");
  const project = await signIn(page);
  const headers = { Authorization: `Bearer ${readFileSync(state().token, "utf-8").trim()}` };
  await page.goto(`/#/p/${project}?box=server%3Aapi`);
  await expect(page.getByRole("button", { name: /^Porte d'entrée/ })).toBeVisible();
  const shown = await page.request.post(`/v1/projects/${project}/show`, { headers, data: { caption: "où est créée une commande ?", path: [{ part: "api/app/orders.py" }] } });
  expect(shown.status()).toBe(200);
  await expect(page.getByRole("region", { name: "Question posée dans Claude Code" })).toBeVisible({ timeout: 2_000 });
  await expect(page).not.toHaveURL(/box=/);
  await expect(page.getByLabel("1 orders.py")).toBeVisible();
  await page.request.delete(`/v1/projects/${project}/show`, { headers });
});

test("a click on a part opens its card under the map: four lines, its functions open VS Code at their line; Esc goes up one level (#106)", async ({ page }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}?box=server%3Aapi`);
  await page.getByRole("button", { name: /^Modèles/ }).click();
  await expect(page).toHaveURL(/part=server%3Aapi%2Fmodels/);
  const card = page.getByRole("region", { name: "Carte de Modèles" });
  await expect(card).toBeVisible();
  for (const label of ["Reçoit", "Renvoie", "Appelé par", "Appelle"]) await expect(card.getByText(label, { exact: true })).toBeVisible();
  const fn = card.getByRole("link", { name: /create_order/ });
  await expect(fn).toHaveAttribute("href", /^vscode:\/\/file\/.+\/api\/app\/orders\.py:4$/);
  await expect(card.getByRole("link", { name: "ouvrir le code" })).toHaveAttribute("href", /orders\.py:1$/);
  await expect(page.getByRole("button", { name: /^Porte d'entrée/ })).toBeVisible(); // the map stays on the same screen
  const crumbs = page.getByRole("navigation", { name: "Où vous êtes" });
  await expect(crumbs.locator("[aria-current=page]")).toHaveText("Modèles");
  await page.keyboard.press("Escape"); // the card first
  await expect(page).not.toHaveURL(/part=/);
  await expect(page).toHaveURL(/box=server/);
  await expect(card).toHaveCount(0);
  await page.keyboard.press("Escape"); // then the box
  await expect(page).not.toHaveURL(/box=/);
});
