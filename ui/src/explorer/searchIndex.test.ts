import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import type { ProjectModel } from "../api";
import { buildIndex, searchIndex, type Group, type Result } from "./searchIndex.ts";

// Ctrl K with the reader's own words (#80): « nom du client » reaches the machine, its setting X-Tenant-ID and the
// steps, though the code says « tenant ». Real study models: Watchdog v1.7 and the older v1.6 studies.

const load = (name: string): ProjectModel =>
  JSON.parse(readFileSync(new URL(`../../test-fixtures/${name}.json`, import.meta.url), "utf-8")) as ProjectModel;
const find = (model: ProjectModel, query: string) => searchIndex(buildIndex(model), query);
const group = (groups: Group[], kind: Group["kind"]) => groups.find((g) => g.kind === kind)?.results ?? [];
const machineOf = (r: Result | undefined) => (r?.target.kind === "machine" ? r.target.machine : null);

test("« nom du client » finds the machine first, its X-Tenant-ID setting, the steps and the « Je veux changer… »", () => {
  const groups = find(load("watchdog-v17"), "nom du client");
  assert.equal(groups[0]!.kind, "changer"); // the intentions come first
  assert.equal(machineOf(group(groups, "machine")[0]), "porte-client");
  assert.ok(group(groups, "reglage").some((r) => r.label === "Nom de l'en-tête du client" && r.detail.includes("X-Tenant-ID")));
  assert.ok(group(groups, "etape").length >= 1);
  assert.match(group(groups, "machine")[0]!.address, /Porte d'entrée du service › Contrôle du nom du client/);
});

test("« tenant » (the code's word) reaches the same machine through its terms, not every machine", () => {
  const model = load("watchdog-v17");
  const machines = group(find(model, "tenant"), "machine");
  assert.equal(machineOf(machines[0]), "porte-client");
  assert.ok(machines.length < model.composants.length, `${machines.length} of ${model.composants.length} machines`);
});

test("« port » finds the project setting APP_PORT, marked as not read by the code", () => {
  const settings = group(find(load("watchdog-v17"), "port"), "reglage");
  const port = settings.find((r) => r.detail.includes("APP_PORT=8000"))!;
  assert.ok(port, settings.map((r) => r.detail).join(" | "));
  assert.equal(port.target.kind, "projet");
  assert.match(port.note ?? "", /lu par le code : non/);
});

test("accents and capitals do not count", () => {
  const model = load("watchdog-v17");
  const ids = (q: string) => JSON.stringify(find(model, q).map((g) => g.results.map((r) => r.key)));
  assert.equal(ids("ecran"), ids("écran"));
  assert.equal(ids("Client"), ids("client"));
  assert.equal(ids("RELEVÉ"), ids("releve"));
  assert.ok(find(model, "releve").length > 0);
});

test("older models (no v1.7 fields): machines, functions and files are found, nothing breaks", () => {
  for (const name of ["watchdog", "justicia"]) {
    const model = load(name);
    const index = buildIndex(model);
    const c = model.composants[0]!;
    assert.ok(group(searchIndex(index, c.nom), "machine").some((r) => machineOf(r) === c.id), `${name}: ${c.nom}`);
    const fn = model.composants.flatMap((x) => x.expose)[0]!;
    assert.ok(group(searchIndex(index, fn.quoi), "code").length > 0, `${name}: ${fn.quoi}`);
    const file = c.fichiers[0]!.split("/").pop()!.replace(/\.\w+$/, "");
    assert.ok(group(searchIndex(index, file), "code").length > 0, `${name}: ${file}`);
  }
});

test("one letter finds nothing, a word must match the start of a word (« port » is not « rapport »)", () => {
  const model = load("watchdog-v17");
  assert.deepEqual(find(model, "p"), []);
  const all = find(model, "port").flatMap((g) => g.results);
  assert.ok(all.every((r) => !/rapport|support/i.test(`${r.label} ${r.detail}`) || /\bport/i.test(`${r.label} ${r.detail}`)));
});

test("a journey is found by its name, and lands on its first step", () => {
  const model = load("watchdog-v17");
  const first = group(find(model, "garder le relevé"), "etape")[0]!;
  assert.equal(first.label, model.parcours[0]!.nom);
  assert.deepEqual(first.target, { kind: "etape", journey: model.parcours[0]!.id, step: 1 });
});
