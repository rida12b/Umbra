import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import type { ProjectModel } from "../api";
import { buildFloor } from "./floor.ts";
import { placeFloor, type Rect } from "./floorLayout.ts";
import { buildRoom } from "./room.ts";

// Shapes no known project has yet, built from the fastapi-template model (review of #86): the rules must
// hold on any studied project, not only on the fixtures they were tuned on.

const load = (): ProjectModel => JSON.parse(readFileSync(new URL("../../test-fixtures/fastapi-template.json", import.meta.url), "utf-8")) as ProjectModel;
type Flow = ProjectModel["flux"][number];
const flow = (de: string, vers: string, verbe: string, quoi: string, nature: "donnee" | "controle" = "donnee") => ({ de, vers, verbe, quoi, nature }) as Flow;

test("a called service that also answers its room stays below it (an answer is not a send)", () => {
  const model = load();
  model.flux.push(flow("sentry", "api", "renvoie l'identifiant de l'erreur à", "identifiant"), flow("smtp", "api", "confirme l'envoi à", "accusé"));
  const plan = placeFloor(buildFloor(model), 974, { web: 3, api: 6 });
  const api = plan.rects.get("api")!;
  for (const called of ["sentry", "smtp"]) assert.ok(plan.rects.get(called)!.y > api.y + api.h, `${called} is not below the server`);
});

test("a flow the model calls « controle » is no door in either room, even when a journey step crosses it", () => {
  const model = load();
  assert.ok(!buildRoom(model, "prestart")!.doors.some((d) => d.bloc === "api"), "api is a door of prestart");
  model.parcours.forEach((j) => (j.principal = j.id === "demarrage"));
  assert.ok(!buildRoom(model, "api")!.doors.some((d) => d.bloc === "prestart"), "prestart is a door of api");
});

/** The fastapi model with a queue mid-belt: the server fills it, a worker takes the jobs, the queue feeds a dashboard. */
function queueModel(): ProjectModel {
  const model = load();
  const like = <T extends { id: string }>(list: T[], id: string) => list.find((x) => x.id === id)!;
  model.blocs.push({ ...like(model.blocs, "db"), id: "file", nom: "File des tâches", type: "queue" });
  model.blocs.push({ ...like(model.blocs, "api"), id: "travail", nom: "Travailleur", type: "worker" });
  model.blocs.push({ ...like(model.blocs, "sentry"), id: "stats", nom: "Tableau de bord", type: "external", importance: "coeur" });
  model.composants.push({ ...like(model.composants, "donnees"), id: "file-c", nom: "File", bloc: "file" });
  model.composants.push({ ...like(model.composants, "donnees"), id: "travail-c", nom: "Tâche", bloc: "travail" });
  const main = model.parcours[0]!;
  const step = (composant: string, touche: string[]) => ({ ...main.etapes[0]!, composant, touche, manuel: false });
  main.etapes.splice(6, 0, step("file-c", []), step("travail-c", ["db"]));
  model.flux.push(
    flow("api", "file", "dépose les tâches dans", "tâche"),
    flow("file", "travail", "livre les tâches à", "tâche"),
    flow("travail", "db", "enregistre dans", "élément"),
    flow("file", "stats", "publie sa longueur vers", "longueur"),
  );
  return model;
}

test("a store mid-belt at a line end: no belt segment runs through a card", () => {
  const model = queueModel();
  const crosses = (p: { x: number; y: number }, q: { x: number; y: number }, r: Rect) =>
    p.x === q.x
      ? p.x > r.x && p.x < r.x + r.w && Math.max(p.y, q.y) > r.y && Math.min(p.y, q.y) < r.y + r.h
      : p.y > r.y && p.y < r.y + r.h && Math.max(p.x, q.x) > r.x && Math.min(p.x, q.x) < r.x + r.w;
  const plan = placeFloor(buildFloor(model), 974, { web: 3, api: 6, travail: 1 });
  const hits: string[] = [];
  for (const route of plan.belt)
    route.points.slice(1).forEach((q, k) => {
      const p = route.points[k]!;
      for (const [id, r] of plan.rects) if (id !== route.link.from && id !== route.link.to && crosses(p, q, r)) hits.push(`${route.link.id} through ${id}`);
    });
  assert.deepEqual(hits, []);
});

// A part may both start its room and send it data: the drawing must not depend on the order of the model's flows.
for (const order of ["data first", "control first"]) {
  test(`a part that controls its room and sends it data goes above it (${order})`, () => {
    const model = load();
    const data = flow("sentry", "api", "envoie les alertes à", "alerte");
    const control = flow("sentry", "api", "surveille", "santé", "controle");
    model.flux.push(...(order === "data first" ? [data, control] : [control, data]));
    const plan = placeFloor(buildFloor(model), 974, { web: 3, api: 6 });
    const [sentry, api] = [plan.rects.get("sentry")!, plan.rects.get("api")!];
    assert.ok(sentry.y + sentry.h <= api.y, "sentry is not above the server although it controls it");
  });
  test(`a step move between parts joined by control and data is a door (${order})`, () => {
    const model = load();
    model.parcours.forEach((j) => (j.principal = j.id === "demarrage"));
    const at = model.flux.findIndex((f) => f.de === "prestart" && f.vers === "api");
    model.flux.splice(order === "data first" ? at : at + 1, 0, flow("prestart", "api", "transmet la configuration à", "configuration"));
    assert.ok(buildRoom(model, "api")!.doors.some((d) => d.bloc === "prestart"), "no prestart door although prestart sends its configuration");
  });
}

test("the wrap lane stays inside the visible floor at every width (a tag hung below sticks out)", () => {
  const model = queueModel();
  const out: string[] = [];
  for (let available = 300; available <= 1500; available += 1) {
    const plan = placeFloor(buildFloor(model), available, { web: 3, api: 6, travail: 1 });
    for (const r of plan.belt) for (const p of r.points) if (p.x > available + 24) out.push(`${available}: ${r.link.id} x=${p.x}`);
  }
  assert.deepEqual(out.slice(0, 5), []);
});
