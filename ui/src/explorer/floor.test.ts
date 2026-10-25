import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import type { ProjectModel } from "../api";
import { buildFloor, mainJourney, type Floor } from "./floor.ts";

// Run with `npm test` (Node's own runner strips the types). The two fixtures are real study models
// (Watchdog, JusticIA) taken on 2026-10-25: the floor must read right on real data, not a toy.

const load = (name: string): ProjectModel =>
  JSON.parse(readFileSync(new URL(`../../test-fixtures/${name}.json`, import.meta.url), "utf-8")) as ProjectModel;
const watchdog = () => load("watchdog");
const justicia = () => load("justicia");

const roleOf = (floor: Floor, id: string) => floor.items.find((item) => item.id === id)?.role;
const attachOf = (floor: Floor, id: string) => floor.items.find((item) => item.id === id)?.attach;
const styleOf = (floor: Floor, from: string, to: string) => floor.links.find((l) => l.from === from && l.to === to)?.style;

test("the main journey is the one through the most components; a tie is flagged and model order wins", () => {
  assert.equal(mainJourney(watchdog()).journey?.id, "envoi-evenement");
  assert.equal(mainJourney(justicia()).journey?.id, "poser-question");
  const tied = watchdog();
  const copy = { ...tied.parcours[1]!, id: "copie" };
  tied.parcours.unshift(copy);
  const found = mainJourney(tied);
  assert.equal(found.journey?.id, "copie");
  assert.equal(found.equivalents, 2);
});

test("Watchdog: ENTRÉE first, the service, SORTIE last; the operator is a side door; tools leave the floor", () => {
  const floor = buildFloor(watchdog());
  assert.equal(floor.entree, "agent-surveille");
  assert.deepEqual(floor.belt, ["api", "memoire"]);
  assert.deepEqual(floor.sortie, { kind: "store", id: "memoire" });
  assert.equal(roleOf(floor, "operateur"), "side");
  assert.equal(attachOf(floor, "operateur"), "api");
  assert.deepEqual(floor.strip, ["docs", "outillage"]);
  assert.equal(floor.limit, "Tout est perdu au redémarrage.");
});

test("JusticIA: only the parts doing the work ride the belt; what they call hangs above them", () => {
  const floor = buildFloor(justicia());
  assert.equal(floor.entree, "user");
  assert.deepEqual(floor.belt, ["site", "api", "agent", "analyse", "memoire-nav"]);
  assert.deepEqual(floor.sortie, { kind: "store", id: "memoire-nav" });
  assert.match(floor.limit ?? "", /au plus 50 conversations/i);
  for (const [id, anchor] of [["modele-vecteurs", "api"], ["base-lois", "api"], ["llm-kimi", "agent"], ["llm-gemini", "agent"]] as const) {
    assert.equal(roleOf(floor, id), "supplier", id);
    assert.equal(attachOf(floor, id), anchor, id);
  }
  assert.equal(attachOf(floor, "courriers"), "api");
  assert.equal(attachOf(floor, "ingestion"), "base-lois");
  assert.equal(attachOf(floor, "hf-dataset"), "ingestion");
  assert.deepEqual(floor.strip, ["outillage", "docs"]);
});

test("SORTIE is never a store the floor only reads", () => {
  const floor = buildFloor(justicia());
  assert.notDeepEqual(floor.sortie, { kind: "store", id: "base-lois" });
  const readOnly = watchdog();
  readOnly.flux = readOnly.flux.map((f) => (f.vers === "memoire" ? { ...f, verbe: "cherche dans" } : f));
  assert.deepEqual(buildFloor(readOnly).sortie, { kind: "reply", to: "agent-surveille" });
});

test("arrow styles come from the graph: a reply goes back upstream, a lookup is thin, a start is control", () => {
  const w = buildFloor(watchdog());
  assert.equal(styleOf(w, "agent-surveille", "api"), "data");
  assert.equal(styleOf(w, "api", "memoire"), "data");
  assert.equal(styleOf(w, "api", "agent-surveille"), "reply");
  assert.equal(styleOf(w, "operateur", "api"), "control");
  const j = buildFloor(justicia());
  assert.equal(styleOf(j, "api", "site"), "reply");
  assert.equal(styleOf(j, "api", "base-lois"), "lookup");
  assert.equal(styleOf(j, "agent", "base-lois"), "lookup");
  assert.equal(styleOf(j, "ingestion", "hf-dataset"), "lookup");
});

test("no arrow is drawn to or from the strip, even when the model links a tool to the code", () => {
  for (const model of [watchdog(), justicia()]) {
    const floor = buildFloor(model);
    for (const link of floor.links) {
      assert.ok(!floor.strip.includes(link.from) && !floor.strip.includes(link.to), `${link.from}>${link.to}`);
    }
  }
  const extra = watchdog();
  extra.flux.push({ de: "api", vers: "docs", quoi: "écrit", verbe: "écrit dans" });
  const floor = buildFloor(extra);
  assert.ok(floor.stripLinks.some((l) => l.from === "api" && l.to === "docs"));
});

test("a tool stays in the strip even when a step touches it", () => {
  const model = watchdog();
  model.parcours[1]!.etapes[0]!.touche.push("docs");
  const floor = buildFloor(model);
  assert.equal(roleOf(floor, "docs"), "strip");
  assert.ok(!floor.belt.includes("docs"));
});

test("every bloc shows exactly once, whatever the model", () => {
  const noJourney = watchdog();
  noJourney.parcours = [];
  const oneBloc = watchdog();
  oneBloc.blocs = oneBloc.blocs.filter((b) => b.id === "api");
  oneBloc.flux = [];
  oneBloc.parcours = [];
  const unknown = watchdog();
  unknown.parcours[1]!.etapes[1]!.composant = "does-not-exist";
  const worker = watchdog();
  worker.blocs.push({ id: "worker", nom: "Tâche", type: "worker", role: "Nettoie.", importance: "coeur", techno: "", code: [], indices: "" });
  for (const model of [watchdog(), justicia(), noJourney, oneBloc, unknown, worker]) {
    const floor = buildFloor(model);
    const shown = [...floor.items.map((i) => i.id), ...floor.overflow];
    assert.deepEqual([...shown].sort(), model.blocs.map((b) => b.id).sort());
    assert.equal(new Set(shown).size, shown.length);
  }
  const none = buildFloor(noJourney);
  assert.equal(none.journey, null);
  assert.deepEqual(none.belt, []);
  assert.equal(roleOf(none, "api"), "orphan");
  assert.equal(buildFloor(unknown).skipped, 1);
  assert.equal(roleOf(buildFloor(worker), "worker"), "orphan");
});

test("a step naming a bloc instead of a component still places that bloc (older models)", () => {
  const model = watchdog();
  model.parcours[1]!.etapes[1]!.composant = "api";
  const floor = buildFloor(model);
  assert.deepEqual(floor.belt, ["api", "memoire"]);
  assert.equal(floor.skipped, 0);
});

test("past sixteen parts on the floor, side doors fold first into « +N », the belt never does", () => {
  const model = watchdog();
  for (let i = 0; i < 14; i++) {
    model.blocs.push({ id: `ext${i}`, nom: `Service ${i}`, type: "external", role: "Appelé.", importance: "secondaire", techno: "", code: [], indices: "" });
    model.flux.push({ de: "api", vers: `ext${i}`, quoi: "appel", verbe: "appelle" });
  }
  const floor = buildFloor(model);
  const onFloor = floor.items.filter((i) => i.role !== "strip" && i.role !== "orphan");
  assert.ok(onFloor.length <= 16);
  assert.ok(floor.overflow.length >= 2);
  assert.deepEqual(floor.belt, ["api", "memoire"]);
});

test("the key lists exactly the shapes on the floor", () => {
  assert.deepEqual([...buildFloor(watchdog()).shapes].sort(), ["person", "room", "store", "tool"]);
  assert.deepEqual([...buildFloor(justicia()).shapes].sort(), ["outside", "person", "room", "store", "tool"]);
});

test("the belt carries the data from room to room: each room after the first gets the real flow that feeds it", () => {
  const belt = (floor: Floor) => floor.beltLinks.map((l) => `${l.from}>${l.to} ${l.verb}`);
  assert.deepEqual(belt(buildFloor(watchdog())), [
    "agent-surveille>api envoie ses comptes rendus à",
    "api>memoire range l'événement dans",
  ]);
  const j = buildFloor(justicia());
  assert.deepEqual(belt(j), [
    "user>site écrit sa question sur",
    "site>api envoie les demandes à",
    "api>agent confie la question à",
    "agent>analyse Serveur de l'assistant fait analyser par", // the server, not the engine, hands it over
    "analyse>memoire-nav Site web de l'assistant enregistre dans",
  ]);
});

test("a hung part says in words how it is linked to the room it hangs on", () => {
  const j = buildFloor(justicia());
  assert.equal(j.relations["base-lois"], "Serveur de l'assistant cherche dans");
  assert.equal(j.relations["ingestion"], "remplit Base des articles de loi");
  assert.equal(j.relations["hf-dataset"], "Outil de remplissage de la base télécharge depuis");
  assert.equal(buildFloor(watchdog()).relations["operateur"], "démarre Porte d'entrée du service");
});

test("SORTIE is the store the journey writes to last, not the first one", () => {
  const model = watchdog();
  model.blocs.push({ id: "cache", nom: "File", type: "queue", role: "x.", importance: "secondaire", techno: "", code: [], indices: "" });
  model.flux.push({ de: "api", vers: "cache", quoi: "pousse", verbe: "pousse dans" });
  model.parcours.find((j) => j.id === "envoi-evenement")!.etapes[2]!.touche.push("cache");
  assert.deepEqual(buildFloor(model).sortie, { kind: "store", id: "memoire" });
});

test("the limit under SORTIE keeps only the clause that states it", () => {
  assert.equal(buildFloor(justicia()).limit, "Au plus 50 conversations de 50 messages chacune.");
});

test("the key never lists a kind whose only part was folded, and folding keeps every hang valid", () => {
  const model = watchdog();
  const blk = (id: string, type: "backend" | "external") => ({ id, nom: id, type, role: "x.", importance: "secondaire" as const, techno: "", code: [], indices: "" });
  for (let i = 0; i < 14; i++) {
    model.blocs.push(blk(`svc${i}`, "backend"));
    model.flux.push({ de: "api", vers: `svc${i}`, quoi: "appel", verbe: "appelle" });
  }
  model.blocs.push(blk("llm", "external"));
  model.flux.push({ de: "api", vers: "llm", quoi: "appel", verbe: "appelle" });
  const floor = buildFloor(model);
  assert.ok(floor.overflow.includes("llm"));
  assert.ok(!floor.shapes.includes("outside"));
  const shown = new Set(floor.items.map((i) => i.id));
  for (const item of floor.items) if (item.attach) assert.ok(shown.has(item.attach), item.id);
});

test("a hung part's link fits its tag (three short lines) on the real models", () => {
  for (const model of [watchdog(), justicia()])
    for (const [id, words] of Object.entries(buildFloor(model).relations)) assert.ok(words.length <= 75, `${id}: ${words}`);
});

test("a step done by hand with no component (v1.7) changes nothing on the floor", () => {
  const model = watchdog();
  model.parcours.find((j) => j.id === "demarrage")!.etapes[0]!.composant = null;
  const floor = buildFloor(model);
  assert.deepEqual(floor.belt, buildFloor(watchdog()).belt);
  assert.equal(floor.skipped, 0);
});

test("a main journey declared by the study (v1.7) is the one the belt follows", () => {
  const model = watchdog();
  model.parcours.find((j) => j.id === "demarrage")!.principal = true;
  assert.equal(buildFloor(model).journey?.id, "demarrage");
  model.parcours.find((j) => j.id === "demarrage")!.principal_deduit = true; // deduced: the floor's own rule
  assert.equal(buildFloor(model).journey?.id, "envoi-evenement");
});

test("v1.7 Watchdog: the validation library hangs on the service it answers; the belt keeps the rooms", () => {
  const floor = buildFloor(load("watchdog-v17"));
  assert.equal(floor.entree, "agent-surveille");
  assert.deepEqual(floor.belt, ["api", "memoire"]);
  assert.equal(roleOf(floor, "validation"), "supplier");
  assert.equal(attachOf(floor, "validation"), "api");
});
