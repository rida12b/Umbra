import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import type { ProjectModel } from "../api";
import { followedRoom, groupOf, journeyStations, stationKey, stepGroups, stepsWord } from "./stations.ts";
import { enterable } from "./room.ts";

// Playing a journey moves the data machine by machine (#77): every « Suivante » changes the station, or says
// why it does not. Real study models: two before v1.7 (Watchdog, JusticIA), two after (Watchdog, fastapi).

const load = (name: string): ProjectModel =>
  JSON.parse(readFileSync(new URL(`../../test-fixtures/${name}.json`, import.meta.url), "utf-8")) as ProjectModel;
const MODELS = ["watchdog", "justicia", "watchdog-v17", "fastapi-template"] as const;
const journey = (model: ProjectModel, id: string) => model.parcours.find((j) => j.id === id)!;

test("every step change of every journey moves the station or gives the reason it stays (0 silent no-moves)", () => {
  const silent: string[] = [];
  for (const name of MODELS) {
    const model = load(name);
    for (const j of model.parcours) {
      const stations = journeyStations(model, j);
      assert.equal(stations.length, j.etapes.length);
      stations.slice(1).forEach((s, i) => {
        if (stationKey(s) === stationKey(stations[i]!) && !s.note) silent.push(`${name}/${j.id} ${i + 1}→${i + 2}`);
      });
    }
  }
  assert.deepEqual(silent, []);
});

test("the station is the step's machine, not the parts it touches (Watchdog « envoi-evenement »)", () => {
  const model = load("watchdog");
  const stations = journeyStations(model, journey(model, "envoi-evenement"));
  assert.deepEqual(
    stations.map((s) => [s.machine, s.room]),
    [["auth-tenant", "api"], ["schemas", "api"], ["route-events", "api"], ["stockage-events", "memoire"], ["route-events", "api"]],
  );
  // The parts a step reaches stay a faint ring, never the station.
  assert.ok(stations.every((s) => !s.touches.includes(s.room!)));
  assert.equal(stations[3]!.move, "room");
  assert.equal(stations[4]!.move, "back");
  assert.match(stations[4]!.note!, /étape 3/);
});

test("a step on the same machine as the one before says so (JusticIA « courrier-pdf », « remplir-base »)", () => {
  const model = load("justicia");
  for (const id of ["courrier-pdf", "remplir-base"]) {
    const stations = journeyStations(model, journey(model, id));
    assert.ok(stations.every((s) => s.machine), `${id} lights nothing on a step`);
    for (const s of stations.slice(1)) {
      assert.equal(s.move, "same");
      assert.match(s.note!, /^Même machine/);
    }
  }
});

test("a step done by hand outside the code is a person station, never nothing", () => {
  const v17 = load("watchdog-v17");
  const start = journeyStations(v17, journey(v17, "demarrer"))[0]!;
  assert.deepEqual([start.machine, start.room, start.person, start.manual], [null, null, "operateur", true]);
  const fastapi = load("fastapi-template");
  const nobody = journeyStations(fastapi, journey(fastapi, "demarrage"))[0]!; // touches no part at all
  assert.deepEqual([nobody.machine, nobody.person, nobody.manual], [null, null, true]);
  assert.match(nobody.note!, /personne/);
  // By hand on a machine (pre-v1.7 models): the machine stays the station, marked as done by a person.
  const justicia = load("justicia");
  const ask = journeyStations(justicia, journey(justicia, "poser-question"))[1]!;
  assert.deepEqual([ask.machine, ask.manual], ["ui-chat", true]);
});

test("a long journey is grouped: by the model's phases, else by room past 9 steps, else not at all", () => {
  const fastapi = load("fastapi-template");
  assert.deepEqual(
    stepGroups(fastapi, journey(fastapi, "mot-de-passe-oublie"))!.map((g) => [g.title, g.from, g.to]),
    [["Demander le lien", 1, 3], ["Envoyer le courriel", 4, 7], ["Revenir par le lien", 8, 10], ["Enregistrer le nouveau mot de passe", 11, 13]],
  );
  const justicia = load("justicia");
  const groups = stepGroups(justicia, journey(justicia, "poser-question"))!;
  assert.deepEqual([groups[0]!.from, groups.at(-1)!.to], [1, 16]);
  assert.ok(groups.every((g, i) => i === 0 || g.from === groups[i - 1]!.to + 1), "groups leave a gap");
  assert.ok(groups.length < 16 && groups.some((g) => g.to > g.from), "grouping by room groups nothing");
  assert.equal(stepGroups(justicia, journey(justicia, "voir-article")), null);
  // An empty phase list (v1.7 « phases: [] ») on a short journey: no group.
  const v17 = load("watchdog-v17");
  assert.equal(stepGroups(v17, journey(v17, "recevoir-releve")), null);
});

test("phases that leave steps out still cover every step, in order", () => {
  const model = load("fastapi-template");
  const j = structuredClone(journey(model, "mot-de-passe-oublie"));
  j.phases = [{ nom: "Envoyer le courriel", de: 4, a: 7 }];
  const groups = stepGroups(model, j)!;
  assert.deepEqual([groups[0]!.from, groups.at(-1)!.to], [1, 13]);
  assert.ok(groups.every((g, i) => i === 0 || g.from === groups[i - 1]!.to + 1));
  assert.ok(groups.some((g) => g.title === "Envoyer le courriel" && g.from === 4 && g.to === 7));
});

test("every step of a long journey has a group in the bar, a few groups only, never « étapes 11–11 »", () => {
  const justicia = load("justicia");
  const j = journey(justicia, "poser-question");
  const groups = stepGroups(justicia, j)!;
  for (let n = 1; n <= j.etapes.length; n++) assert.ok(groupOf(groups, n), `step ${n} has no group`);
  assert.ok(groups.length <= 5, `${groups.length} groups for 16 steps`);
  assert.ok(groups.every((g) => !/(\d+)–\1$/.test(stepsWord(g))));
  assert.equal(stepsWord({ title: "", from: 11, to: 11 }), "étape 11");
});

test("overlapping and out-of-range phases still cover each step exactly once, in order", () => {
  const model = load("fastapi-template");
  const base = journey(model, "mot-de-passe-oublie");
  for (const phases of [
    [{ nom: "A", de: 1, a: 5 }, { nom: "B", de: 2, a: 3 }, { nom: "C", de: 4, a: 9 }],
    [{ nom: "A", de: 1, a: 6 }, { nom: "Z", de: 20, a: 25 }],
    [{ nom: "B", de: 6, a: 3 }, { nom: "A", de: 2, a: 40 }],
  ]) {
    const groups = stepGroups(model, { ...base, phases })!;
    const covered = groups.flatMap((g) => {
      assert.ok(g.from <= g.to, JSON.stringify(g));
      return Array.from({ length: g.to - g.from + 1 }, (_, i) => g.from + i);
    });
    assert.deepEqual(covered, Array.from({ length: base.etapes.length }, (_, i) => i + 1), JSON.stringify(phases));
  }
});

test("a step naming a whole part (before v1.7) is shown on the floor, where that part lights; never an empty room", () => {
  const model = load("watchdog");
  const j = structuredClone(journey(model, "envoi-evenement"));
  j.etapes[1]!.composant = "api"; // a part with machines, not a machine
  const stations = journeyStations(model, j);
  assert.deepEqual([stations[1]!.machine, stations[1]!.room], [null, "api"]);
  assert.equal(followedRoom(stations[1], enterable(model)), null); // the floor, not « api » with nothing lit
  assert.equal(followedRoom(stations[0], enterable(model)), "api");
});
