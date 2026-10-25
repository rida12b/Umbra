import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import type { ProjectModel } from "../api";
import { buildRoom, drivingJourney, enterable, stepRuns, type Room } from "./room.ts";

// A room is a part opened in place (#76): its machines in the order the data visits them, the doors to
// its neighbours, the refusals under the machine that handles them. Real study models, as for the floor.

const load = (name: string): ProjectModel =>
  JSON.parse(readFileSync(new URL(`../../test-fixtures/${name}.json`, import.meta.url), "utf-8")) as ProjectModel;
const watchdog = () => load("watchdog");
const justicia = () => load("justicia");
const room = (model: ProjectModel, bloc: string) => buildRoom(model, bloc)!;
const crossings = (r: Room, bloc: string) => r.doors.find((d) => d.bloc === bloc)?.crossings.map((c) => `${c.dir}${c.step}`);

test("a room follows the main journey when it passes there, else the journey with most steps there", () => {
  assert.equal(drivingJourney(watchdog(), "api")?.id, "envoi-evenement"); // not parcours[0], « demarrage »
  assert.equal(drivingJourney(justicia(), "site")?.id, "poser-question");
  assert.equal(drivingJourney(justicia(), "courriers")?.id, "courrier-pdf");
  assert.equal(drivingJourney(justicia(), "ingestion")?.id, "remplir-base");
});

test("start-up wiring leaves the belt: no step on the driving journey, and only main.py/app.py or no step at all", () => {
  assert.deepEqual(room(watchdog(), "api").band, ["app"]);
  assert.deepEqual(room(justicia(), "api").band, ["api-socle"]);
  assert.deepEqual(room(justicia(), "outillage").band, ["atelier"]);
  for (const [bloc, id] of [["courriers", "courriers-pdf"], ["ingestion", "remplissage"], ["site", "ui-etat"], ["analyse", "analyse-reponse"]] as const)
    assert.ok(room(justicia(), bloc).belt.some((m) => m.id === id), id);
});

test("machines ride the belt in the order the data visits them, with their step numbers", () => {
  const api = room(watchdog(), "api");
  assert.deepEqual(api.belt.map((m) => [m.id, m.steps]), [["auth-tenant", [1]], ["schemas", [2]], ["route-events", [3, 5]]]);
  assert.deepEqual(room(justicia(), "site").belt.map((m) => m.id), ["ui-pages", "ui-chat", "ui-api", "ui-etat"]);
  const jApi = room(justicia(), "api");
  assert.deepEqual(jApi.belt.map((m) => m.id), ["api-chat", "recherche"]);
  assert.deepEqual(jApi.belt[0]!.steps, [5, 10, 13]);
  assert.deepEqual(room(justicia(), "courriers").belt.map((m) => [m.id, m.steps]), [["courriers-pdf", [1, 2, 3, 4]]]);
  const workshop = room(justicia(), "outillage");
  assert.deepEqual(workshop.belt, []);
});

test("a step naming a part the model does not know changes nothing", () => {
  const model = watchdog();
  model.parcours.find((j) => j.id === "envoi-evenement")!.etapes.push({ ...model.parcours[1]!.etapes[0]!, composant: "ghost" });
  assert.deepEqual(room(model, "api").belt.map((m) => m.id), ["auth-tenant", "schemas", "route-events"]);
});

test("only parts with machines can be entered", () => {
  assert.deepEqual([...enterable(watchdog())].sort(), ["api", "memoire"]);
  const j = enterable(justicia());
  for (const id of ["user", "memoire-nav", "base-lois", "modele-vecteurs", "llm-kimi", "llm-gemini", "hf-dataset", "docs"]) assert.ok(!j.has(id), id);
  assert.equal(buildRoom(watchdog(), "agent-surveille"), null);
});

test("Watchdog entry service: one door in from the agent, one door out to the store, with the steps that cross them", () => {
  const api = room(watchdog(), "api");
  assert.deepEqual(api.doors.map((d) => [d.bloc, d.side]), [["agent-surveille", "left"], ["memoire", "right"]]);
  const agent = api.doors[0]!;
  assert.equal(agent.verb, "envoie ses comptes rendus à");
  assert.deepEqual(crossings(api, "agent-surveille"), ["in1", "out5"]);
  assert.deepEqual(api.doors[1]!.crossings, [
    { step: 4, dir: "out", machine: "Rangement des événements" },
    { step: 5, dir: "in", machine: "Réception des comptes rendus" },
  ]);
  const store = room(watchdog(), "memoire");
  assert.deepEqual(store.doors.map((d) => d.bloc), ["api"]);
  assert.deepEqual(crossings(store, "api"), ["in4", "out5"]);
});

test("JusticIA server: each neighbour once, in the order the data meets it", () => {
  const api = room(justicia(), "api");
  const ids = api.doors.map((d) => d.bloc);
  assert.equal(new Set(ids).size, ids.length);
  assert.deepEqual(api.doors.filter((d) => d.side === "left").map((d) => d.bloc), ["site"]);
  assert.deepEqual(crossings(api, "site"), ["in5", "out14"]);
  assert.deepEqual(crossings(api, "agent"), ["out7", "in9", "out11"]);
  assert.deepEqual(crossings(api, "analyse"), ["in13"]);
  assert.ok(ids.indexOf("agent") < ids.indexOf("analyse"));
  assert.ok(ids.includes("courriers"));
});

test("what a machine searches or calls hangs under it, unless it is already a door", () => {
  const recherche = room(justicia(), "api").belt.find((m) => m.id === "recherche")!;
  assert.deepEqual(recherche.hung.map((h) => [h.bloc, h.steps]), [["modele-vecteurs", [6, 9]], ["base-lois", [6, 9]]]);
  assert.ok(room(justicia(), "api").belt.every((m) => m.hung.every((h) => h.bloc !== "site")));
});

test("refusals hang under the one machine whose files hold them; others are listed, never guessed", () => {
  const api = room(watchdog(), "api");
  const chutes = (id: string) => api.belt.find((m) => m.id === id)!.chutes;
  assert.match(chutes("auth-tenant")[0]!.alors, /401/);
  assert.match(chutes("schemas")[0]!.alors, /422/);
  assert.equal(chutes("auth-tenant")[0]!.technical, true);
  assert.deepEqual(chutes("route-events"), []);
  assert.ok(api.elsewhere.some((b) => b.journey === "acces-sans-client")); // its journey is not the driving one
  const store = room(watchdog(), "memoire");
  assert.match(store.belt[0]!.chutes[0]!.quand, /^Le même event_id est envoyé deux fois/);
  const site = room(justicia(), "site");
  assert.equal(site.belt.find((m) => m.id === "ui-api")!.chutes.length, 2); // matched by an exposed file
  assert.equal(site.belt.find((m) => m.id === "ui-chat")!.chutes.length, 2);
  assert.deepEqual(site.unplaced, []);
  assert.equal(room(justicia(), "courriers").belt[0]!.chutes.length, 2);
});

test("a refusal two machines could hold is listed, not drawn", () => {
  const model = watchdog();
  model.composants.find((c) => c.id === "route-events")!.fichiers.push("watchdog_ai/ingestion/schemas.py");
  const api = room(model, "api");
  assert.deepEqual(api.belt.find((m) => m.id === "schemas")!.chutes, []);
  assert.ok(api.unplaced.some((b) => b.fichier === "watchdog_ai/ingestion/schemas.py"));
});

test("a journey's steps are grouped by the room they happen in; the way back is named", () => {
  const titles = (model: ProjectModel, id: string) => stepRuns(model, model.parcours.find((j) => j.id === id)!).map((r) => `${r.title} ${r.from}-${r.to}`);
  assert.deepEqual(titles(watchdog(), "envoi-evenement"), [
    "Porte d'entrée du service 1-3",
    "Mémoire temporaire des événements 4-4",
    "Retour à l'expéditeur 5-5",
  ]);
  assert.deepEqual(titles(justicia(), "poser-question"), [
    "Site web de l'assistant 1-4",
    "Serveur de l'assistant 5-6",
    "Moteur de raisonnement juridique 7-8",
    "Serveur de l'assistant 9-10",
    "Moteur de raisonnement juridique 11-11",
    "Lecture de la réponse 12-12",
    "Serveur de l'assistant 13-13",
    "Retour à l'expéditeur 14-16",
  ]);
});

test("a person's own action at a door comes in; the machine answering them goes back", () => {
  const site = room(justicia(), "site");
  assert.deepEqual(site.doors.map((d) => [d.bloc, d.side]), [["user", "left"], ["api", "right"]]);
  assert.deepEqual(crossings(site, "user"), ["in1", "in2", "out15"]); // step 2: the person sends the question
  assert.deepEqual(crossings(site, "api"), ["out5", "in14"]);
  assert.deepEqual(crossings(room(watchdog(), "api"), "agent-surveille"), ["in1", "out5"]);
});

test("the other journeys' refusals never repeat the driving journey's own", () => {
  assert.deepEqual([...new Set(room(watchdog(), "api").elsewhere.map((b) => b.journey))], ["demarrage", "acces-sans-client"]);
  for (const model of [watchdog(), justicia()])
    for (const bloc of enterable(model)) {
      const r = room(model, bloc);
      assert.ok(r.elsewhere.every((b) => b.journey !== r.journey?.id), bloc);
    }
});

test("« Retour à l'expéditeur » only for a last run back in a part seen before that answers the sender", () => {
  const titles = (model: ProjectModel, id: string) => stepRuns(model, model.parcours.find((j) => j.id === id)!).map((r) => `${r.title} ${r.from}-${r.to}`);
  assert.deepEqual(titles(watchdog(), "acces-sans-client"), ["Porte d'entrée du service 1-2"]);
  assert.deepEqual(titles(watchdog(), "demarrage"), ["Porte d'entrée du service 1-3"]);
  assert.deepEqual(titles(justicia(), "remplir-base"), ["Outil de remplissage de la base 1-6"]);
  assert.deepEqual(titles(justicia(), "courrier-pdf"), ["Fabrique de courriers 1-4"]);
  assert.equal(titles(justicia(), "voir-article").at(-1), "Retour à l'expéditeur 4-4");
  const manual = watchdog();
  const send = manual.parcours.find((j) => j.id === "envoi-evenement")!;
  send.etapes[4]!.manuel = true; // the last run is the person's own action, not an answer
  assert.ok(!titles(manual, "envoi-evenement").at(-1)!.startsWith("Retour"));
});
