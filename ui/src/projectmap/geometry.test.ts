import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import type { SystemMap } from "../api.ts";
import { aroundText, frenchDate, geometry, where, type Rect } from "./geometry.ts";

// The real engine output on the two repos of the mocks (ADR-0007): full-stack-fastapi-template and sqlite-utils.
const load = (name: string) => JSON.parse(readFileSync(new URL(`../../test-fixtures/${name}.json`, import.meta.url), "utf-8")) as SystemMap;
const template = load("system-fastapi-template");
const sqlite = load("system-sqlite-utils");

const overlap = (a: Rect, b: Rect) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
const viewBox = (text: string) => text.split(" ").map(Number) as [number, number, number, number];

test("the template map is laid out as the mock: user, web app, server, base on one line, mail under the server", () => {
  const drawn = geometry(template);
  const at = Object.fromEntries(drawn.boxes.map((b) => [b.box.title, b.rect]));
  assert.deepEqual(
    ["Utilisateur", "Application web", "Serveur", "Base"].map((t) => at[t]?.x),
    [80, 250, 530, 810],
  );
  assert.deepEqual([at.Courriel?.x, at.Courriel?.y], [530, 420]); // under the server that sends it, as the mock
  const sends = drawn.arrows.find((a) => a.label.text === "envoie");
  assert.equal(sends?.label.y, 410); // the verb just above the box it reaches
  assert.deepEqual(drawn.around && [drawn.around.x, drawn.around.y], [24, 520]);
  assert.deepEqual(drawn.viewBox.split(" ").slice(0, 3), ["0", "100", "1200"]);
  assert.equal(drawn.entries.length, 1);
  assert.deepEqual(
    drawn.outputs.map((o) => [o.output.label, o.at[0]]),
    [
      ["écran mis à jour", 1048],
      ["ligne enregistrée", 1048],
      ["courriel envoyé", 1048],
    ],
  );
});

test("an output with a box on its right goes down under every box, then right; the others go straight", () => {
  const drawn = geometry(template);
  const screen = drawn.outputs.find((o) => o.output.label === "écran mis à jour");
  const row = drawn.outputs.find((o) => o.output.label === "ligne enregistrée");
  assert.equal(screen?.path.split(" L").length, 3);
  assert.equal(row?.path.split(" L").length, 2);
  const lowest = Math.max(...drawn.boxes.map((b) => b.rect.y + b.rect.h));
  assert.ok((screen?.at[1] ?? 0) > lowest);
});

test("no two boxes overlap, the chip « + N autour » sits left of every line, all fits in the view", () => {
  for (const map of [template, sqlite]) {
    const drawn = geometry(map);
    const rects = drawn.boxes.map((b) => b.rect);
    rects.forEach((a, i) => rects.slice(i + 1).forEach((b) => assert.ok(!overlap(a, b), `${JSON.stringify(a)} ${JSON.stringify(b)}`)));
    const [, y0, w, h] = viewBox(drawn.viewBox);
    for (const r of rects) assert.ok(r.y >= y0 && r.y + r.h <= y0 + h && r.x + r.w <= w);
    const around = drawn.around;
    assert.ok(around);
    assert.ok(around.y + 36 <= y0 + h);
    const drops = drawn.outputs.filter((o) => o.path.split(" L").length === 3).map((o) => Number(o.path.slice(1).split(",")[0]));
    for (const x of drops) assert.ok(around.x + around.w < x, "the chip must not cross a line going down");
    for (const a of drawn.arrows) assert.ok(a.label.y > y0 && a.label.y < y0 + h);
  }
});

test("on 1280×720 the map is drawn at least at 85 % of its size: no scroll, text still readable", () => {
  const area = { w: 1280 - 40, h: 720 - 48 - 116 - 54 }; // top bar, header, bottom bar (styles.css)
  for (const map of [template, sqlite]) {
    const [, , w, h] = viewBox(geometry(map).viewBox);
    assert.ok(Math.min(area.w / w, area.h / h) >= 0.85, `${w}×${h}`);
  }
});

test("sqlite-utils: two ways in, the command above the library, the file right of the library", () => {
  const drawn = geometry(sqlite);
  const at = Object.fromEntries(drawn.boxes.map((b) => [b.box.title, b.rect]));
  assert.equal(drawn.entries.length, 2);
  assert.deepEqual([at.Commande?.x, at.Bibliothèque?.x, at["Fichier SQLite"]?.x], [300, 300, 690]);
  assert.ok((at.Commande?.y ?? 0) < (at.Bibliothèque?.y ?? 0));
  assert.deepEqual(
    drawn.outputs.map((o) => o.output.label),
    ["résultat affiché", "fichier .db modifié"],
  );
  assert.ok(drawn.outputs.every((o) => o.path.split(" L").length === 2));
});

test("two-way links draw both arrows with their verbs; the same map always draws the same", () => {
  const drawn = geometry(template);
  const verbs = drawn.arrows.map((a) => a.label.text);
  for (const verb of ["clique", "affiche", "appelle", "répond", "écrit", "envoie"]) assert.ok(verbs.includes(verb), verb);
  assert.deepEqual(geometry(template), drawn);
});

test("words around the map", () => {
  assert.equal(aroundText(template), "+ 7 outils autour (tests, CI…)");
  assert.equal(aroundText(sqlite), "+ 4 outils autour (tests, docs…)");
  assert.equal(frenchDate("2026-04-16"), "16/04/2026");
  assert.equal(where({ file: "a.py", start: 7, end: 7 }), "a.py:7");
  assert.equal(where({ file: "a.py", start: 7, end: 9 }), "a.py:7-9");
  assert.equal(where({ file: "copier.yml", start: 0, end: 0 }), "copier.yml");
});
