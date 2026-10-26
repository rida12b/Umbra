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

test("the factory floor: ENTRÉE to SORTIE, tools aside; a click explains, « Entrer dedans » zooms in, Échap comes back", async ({ page, isMobile }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}`);
  const trail = page.getByRole("navigation", { name: "Où vous êtes" });
  await expect(trail).toContainText("L'usine");
  if (isMobile) {
    await expect(page.getByText("Autour du projet (ne tourne pas)")).toBeVisible();
    await page.getByRole("button", { name: /API commandes/ }).first().click();
  } else {
    await expect(page.locator('[data-floor-id="user"]')).toContainText("ENTRÉE");
    await expect(page.getByRole("button", { name: /^Entrée : Client/ })).toBeVisible(); // said to keyboard and screen readers too
    await expect(page.getByRole("list", { name: "Le chemin de la donnée, pièce par pièce" })).toContainText("Base PostgreSQL (sortie)"); // the end is said to screen readers
    await expect(page.locator('[data-floor-id="db"]')).toContainText("SORTIE");
    // The belt reads like text: left to right, then the next line.
    const at = async (id: string) => {
      const box = await page.locator(`[data-floor-id="${id}"]`).boundingBox();
      return box ? box.y * 10_000 + box.x : Number.NaN;
    };
    const order = [await at("user"), await at("web"), await at("api"), await at("db")];
    expect(order).toEqual([...order].sort((a, b) => a - b));
    await expect(page.getByText("Autour du projet (ne tourne pas)")).toBeVisible();
    await expect(page.locator('[data-floor-id="docs"]')).toBeVisible();
    const drawn = await page.locator("[data-shape]").evaluateAll((els) => [...new Set(els.map((e) => e.getAttribute("data-shape")))].sort());
    const keyed = await page.locator("[data-key-shape]").evaluateAll((els) => els.map((e) => e.getAttribute("data-key-shape")).sort());
    for (const shape of drawn) expect(keyed).toContain(shape); // every kind drawn is in the key (mockup B keeps the usual kinds even when absent)
    await page.locator('[data-floor-id="api"]').click();
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  const panel = page.getByRole("region", { name: "API commandes", exact: true }); // the part's plate: side panel, or bottom sheet on a phone (#79)
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
  // In the step's room, the panel keeps the room's step cards, each with its code (V53).
  const panel = page.getByLabel("Explication");
  await expect(panel.locator('[aria-current="step"]')).toContainText("L'API valide puis");
  await panel.getByRole("button", { name: "api/app/orders.py:8–10" }).click();
  await expect(page.locator('[data-cited="true"]').first()).toContainText("def create_order");
});

test("on a phone, from a part down to its functions: lists, then the map over its explanation", async ({ page, isMobile }) => {
  test.skip(!isMobile, "the phone layout");
  const project = await signIn(page);
  await page.goto(`/#/p/${project}?node=x%3Apart%3Aapi`);
  await page.getByRole("button", { name: /Entrer dedans/ }).first().click();
  await expect(page).toHaveURL(/node=x%3Acomponent%3A/);
  await page.getByRole("button", { name: /Entrer dedans/ }).first().click();
  const map = page.locator(".react-flow");
  const panel = page.getByLabel("Explication et preuves");
  await expect(map).toBeVisible();
  await expect(panel).toBeVisible();
  const [mapBox, panelBox] = [await map.boundingBox(), await panel.boundingBox()];
  expect(mapBox && mapBox.width).toBeGreaterThan(300); // not squeezed by a side panel
  expect(panelBox && mapBox && panelBox.y).toBeGreaterThanOrEqual((mapBox?.y ?? 0) + (mapBox?.height ?? 0) - 1);
});

test("a room opened in place: its machine in data order, the door data comes in by, then down to its functions", async ({ page, isMobile }) => {
  test.skip(isMobile, "the desktop map");
  const project = await signIn(page);
  await page.goto(`/#/p/${project}?node=x%3Apart%3Aapi`);
  await expect(page.locator('[data-room-item="door:web"]')).toContainText("depuis Site web");
  await expect(page.locator(":focus")).toContainText("API commandes"); // the keyboard lands in the room, on its title
  await expect(page.locator('[data-room-item="door:db"]')).toContainText("SORTIE"); // where the data ends: the way out, not a tag
  await expect(page.locator('[data-room-item="door:db"]')).toContainText("Base PostgreSQL");
  await page.locator('[data-room-item="orders"]').click();
  await page.getByLabel("Explication").getByRole("button", { name: /Entrer dedans/ }).click();
  await expect(page).toHaveURL(/node=x%3Acomponent%3Aorders/);
  await page.locator('.react-flow__node').getByRole("button", { name: /Entrer dedans/ }).first().click();
  await expect(page.locator('.react-flow__node[data-id="api/app/orders.py::create_order"]')).toBeVisible();
  await expect(page.locator(".react-flow__edge.link-hypothesis")).toHaveCount(1); // create_order calls validate
});

test("on a phone, the keyboard follows: into the room's name, then back on the room after Échap", async ({ page, isMobile }) => {
  test.skip(!isMobile, "the phone layout");
  const project = await signIn(page);
  await page.goto(`/#/p/${project}`);
  await page.locator('[data-narrow-id="api"]').getByRole("button", { name: /Entrer dedans/ }).click();
  await expect(page).toHaveURL(/node=x%3Apart%3Aapi/);
  await expect(page.locator(":focus")).toHaveText("API commandes");
  await page.keyboard.press("Escape");
  await expect(page).toHaveURL(/node=x%3Aparts/);
  await expect(page.locator('[data-narrow-id="api"] :focus')).toHaveCount(1);
});

test("a project added while the engine runs opens on its factory floor, never on « l'étude a échoué » (#85)", async ({ page }) => {
  await signIn(page);
  const { token, spare } = state();
  const secret = readFileSync(token, "utf-8").trim();
  const added = await page.request.post("/v1/projects", { headers: { Authorization: `Bearer ${secret}` }, data: { path: spare } });
  const { id } = (await added.json()) as { id: string };
  await page.goto(`/#/p/${id}`);
  await expect(page.getByRole("navigation", { name: "Où vous êtes" })).toContainText("L'usine", { timeout: 20_000 });
  await expect(page.getByText("a échoué")).toHaveCount(0);
});

test("a failed read says so, offers « Réessayer », and the retry opens the project (review of #85)", async ({ page }) => {
  const project = await signIn(page);
  const model = `**/v1/projects/${project}/model`;
  await page.route(model, (route) =>
    route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "reading the project failed: OSError: file locked" }) }),
  );
  await page.goto(`/#/p/${project}`);
  await expect(page.getByRole("heading", { name: "Umbra n'a pas pu lire le projet" })).toBeVisible();
  await expect(page.getByText("file locked")).toBeVisible();
  await expect(page.getByText(/Claude Code est connecté|moteur Umbra tourne/)).toHaveCount(0); // neither wrong culprit
  await page.unroute(model); // the cause went away
  await page.getByRole("button", { name: "Réessayer" }).click();
  await expect(page.getByRole("navigation", { name: "Où vous êtes" })).toContainText("L'usine");
});

/** Records whether the floor is drawn at any moment once the URL has moved to step 2 (the transit is 900 ms). */
async function watchFloor(page: Page) {
  await page.evaluate(() => {
    const w = window as unknown as { floorSeen: boolean };
    w.floorSeen = false;
    const look = () => {
      if (location.hash.includes("step=2") && document.querySelector("[data-floor-id]")) w.floorSeen = true;
    };
    new MutationObserver(look).observe(document.body, { subtree: true, childList: true, attributes: true });
    window.addEventListener("hashchange", look);
  });
}
const floorSeen = (page: Page) => page.evaluate(() => (window as unknown as { floorSeen: boolean }).floorSeen);

test("a played journey follows the data: the step's room opens, the step moves, the bar covers nothing (#77)", async ({ page, isMobile }) => {
  await page.setViewportSize(isMobile ? { width: 375, height: 812 } : { width: 1440, height: 900 });
  const project = await signIn(page);
  await page.goto(`/#/p/${project}?journey=order&step=1`);
  const bar = page.getByLabel("Chemin de données en lecture");
  await expect(bar.getByRole("button", { name: "web/src/app.ts l.1-3" })).toBeVisible(); // file:lines on the step
  if (!isMobile) await expect(page.locator("animateMotion")).not.toHaveCount(0); // the data runs along the lit belt
  await watchFloor(page);
  await bar.getByRole("button", { name: "Étape suivante" }).click();
  // The camera opens the room of the step's machine, and says the data moved there.
  await expect(page).toHaveURL(/node=x%3Apart%3Aapi&journey=order&step=2/);
  await expect(bar).toContainText("Passage dans « API commandes »");
  const station = isMobile ? page.locator('[data-narrow-id="orders"] > div') : page.locator(".fl-machine.lit");
  await expect(station).toContainText("Commandes");
  // On a wide screen the data first runs on the floor to the new room (transit); a phone opens the room at once.
  expect(await floorSeen(page)).toBe(!isMobile);
  // The lit machine is in full view: under the top bar, above the player bar, at 1440 and at 375.
  const [machine, under, top] = [await station.boundingBox(), await bar.boundingBox(), await page.getByLabel("Où vous êtes").boundingBox()];
  expect(machine && under && top && machine.y >= top.y + top.height && machine.y + machine.height <= under.y).toBe(true);
  if (!isMobile) {
    const map = await page.locator(".map-surface").boundingBox(); // the drawing itself, the bar under it
    expect(map && under && map.y + map.height <= under.y + 1).toBe(true);
  }
});

test("with reduced motion, a played journey moves without any animation (#77)", async ({ page, isMobile }) => {
  test.skip(isMobile, "the phone shows a list: no belt to animate");
  await page.emulateMedia({ reducedMotion: "reduce" });
  const project = await signIn(page);
  await page.goto(`/#/p/${project}?journey=order&step=1`);
  const bar = page.getByLabel("Chemin de données en lecture");
  await expect(bar).toContainText("étape 1 sur 2");
  await expect(page.locator("animateMotion")).toHaveCount(0);
  await watchFloor(page);
  await bar.getByRole("button", { name: "Étape suivante" }).click();
  await expect(page.locator(".fl-machine.lit")).toContainText("Commandes");
  expect(await floorSeen(page)).toBe(false); // straight into the room, no floor shown first
  await expect(page.locator(".room-open, animateMotion")).toHaveCount(0);
});

test("a machine's plate: six fixed slots, ✓ and ?, refusals in red, plays from « Vu dans », opens its code, Échap closes it first (#79)", async ({ page, isMobile }) => {
  if (isMobile) await page.setViewportSize({ width: 375, height: 812 });
  const project = await signIn(page);
  await page.goto(`/#/p/${project}?node=x%3Apart%3Aapi`);
  const machine = page.locator('[data-room-item="orders"], [data-narrow-id="orders"] button').first();
  await machine.click();
  const plate = page.getByRole("region", { name: "Commandes", exact: true });
  await expect(plate).toBeVisible();
  // Always the same slots, in the same order (V69).
  const slots = await plate.locator("[data-slot] h3").allTextContents();
  expect(slots.map((t) => t.toLowerCase())).toEqual(["fait", "reçoit", "rend", "réglages", "où", "vu dans"]);
  await expect(plate.locator('[data-slot="Rend"] .text-fl-refus')).toHaveText("ou un refus si elle est vide");
  // The check is the engine's: lines found in the file ✓, lines that are not there ?.
  const settings = plate.locator('[data-slot="Réglages"] li');
  await expect(settings.filter({ hasText: "validate(order)" })).toContainText("✓ vérifié");
  await expect(settings.filter({ hasText: "save_to_disk(order)" })).toContainText("? hypothèse");
  if (isMobile) {
    // A bottom sheet: focus is in it, its close button on screen; closing gives the keyboard back to the machine.
    const close = page.getByRole("button", { name: "Fermer la fiche" });
    await expect(close).toBeFocused();
    const box = await close.boundingBox();
    expect(box && box.y >= 0 && box.y + box.height <= 812).toBe(true);
    expect(await page.getByRole("dialog").evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(true);
  }
  // Échap closes the plate first: the room stays.
  await page.keyboard.press("Escape");
  await expect(plate).toHaveCount(0);
  await expect(page).toHaveURL(/node=x%3Apart%3Aapi/);
  if (isMobile) await expect(machine).toBeFocused();
  // « Vu dans » plays the journey from that step.
  await machine.click();
  await page.getByRole("region", { name: "Commandes", exact: true }).getByRole("button", { name: /Passer une commande · étape 2/ }).click();
  await expect(page).toHaveURL(/journey=order&step=2/);
  // A cited file opens the code level at the lines, shown first.
  await page.goto(`/#/p/${project}?node=x%3Apart%3Aapi&select=orders`);
  await page.getByRole("region", { name: "Commandes", exact: true }).getByRole("button", { name: "api/app/orders.py l.8-10" }).click();
  await expect(page).toHaveURL(/node=api%2Fapp%2Forders\.py.*select=line%3A8-10/);
  await expect(page.getByLabel("Les lignes citées")).toContainText("def create_order");
});

test("a room's plate opens its machines from the floor; the project's settings open from any settings card (#79)", async ({ page, isMobile }) => {
  const project = await signIn(page);
  await page.goto(`/#/p/${project}?select=api`);
  await page.getByRole("region", { name: "API commandes", exact: true }).getByRole("button", { name: /^Commandes —/ }).click();
  await expect(page).toHaveURL(/node=x%3Apart%3Aapi.*select=orders/);
  await expect(page.getByRole("region", { name: "Commandes", exact: true })).toBeVisible();
  await page.goto(`/#/p/${project}`);
  await page.getByRole("button", { name: /Réglages du projet/ }).first().click();
  const settings = page.getByRole("region", { name: "Réglages du projet" });
  await expect(settings).toContainText("image: postgres:16");
  await expect(settings).toContainText("lu par le code : non");
  if (!isMobile) {
    await page.goto(`/#/p/${project}?node=x%3Apart%3Aapi`);
    await page.getByRole("button", { name: /Réglages du projet/ }).click();
    await expect(page.getByRole("region", { name: "Réglages du projet" })).toBeVisible();
  }
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

test("a person cannot be entered; a link to a part without machines says so and leads back", async ({ page, isMobile }) => {
  test.skip(isMobile, "the desktop floor");
  const project = await signIn(page);
  await page.goto(`/#/p/${project}`);
  await expect(page.locator('[data-floor-id="user"]')).toBeVisible();
  await expect(page.locator('[data-floor-id="user"]').getByRole("button", { name: /Entrer/ })).toHaveCount(0);
  await page.goto(`/#/p/${project}?node=x%3Apart%3Auser`);
  await expect(page.getByText("n'a pas de machine à ouvrir")).toBeVisible();
  await expect(page.getByText("README.md")).toHaveCount(0);
  await page.getByRole("button", { name: "Revenir à l'usine" }).click();
  await expect(page).toHaveURL(/node=x%3Aparts/);
});

test("inside a room nothing is cut, and Échap goes back to the floor with the room in focus", async ({ page, isMobile }) => {
  test.skip(isMobile, "the desktop map");
  const project = await signIn(page);
  await page.goto(`/#/p/${project}`);
  await page.locator('[data-floor-id="api"]').getByRole("button", { name: /Entrer dans/ }).click();
  await expect(page).toHaveURL(/node=x%3Apart%3Aapi/);
  const map = await page.locator(".map-surface").boundingBox();
  const boxes = await page.locator("[data-room-item]").evaluateAll((els) => els.map((e) => e.getBoundingClientRect().toJSON() as DOMRect));
  const outside = boxes.filter((b) => !map || b.left < map.x - 1 || b.right > map.x + map.width + 1 || b.top < map.y - 1 || b.bottom > map.y + map.height + 1);
  const indicator = page.getByRole("button", { name: /hors champ/ });
  if (outside.length === 0) await expect(indicator).toHaveCount(0);
  else await expect(indicator).toContainText(String(outside.length));
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  await page.keyboard.press("Escape");
  await expect(page).toHaveURL(/node=x%3Aparts/);
  await expect.poll(() => page.evaluate(() => document.activeElement?.closest("[data-floor-id]")?.getAttribute("data-floor-id"))).toBe("api");
});
