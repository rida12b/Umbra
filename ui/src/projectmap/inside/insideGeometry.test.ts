import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import type { InsideMap } from "../../api.ts";
import type { Rect } from "../geometry.ts";
import { insideAroundText, insideGeometry } from "./insideGeometry.ts";

// The real engine output (#105) inside three boxes: the template's Serveur and Application web, sqlite-utils' Bibliothèque.
const fixtures = JSON.parse(readFileSync(new URL("../../../test-fixtures/inside.json", import.meta.url), "utf-8")) as Record<"server" | "web" | "library", InsideMap>;

const overlap = (a: Rect, b: Rect) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
const at = (inside: InsideMap) => {
  const drawn = insideGeometry(inside);
  const byName = Object.fromEntries(drawn.parts.map((p) => [p.part.kind === "stub" ? `${p.part.title} ${p.part.detail}` : p.part.title, p.rect]));
  return { drawn, byName };
};

test("inside Serveur, as the mock: stub, entry, routes on one line; access, models, data under; Base and Courriel on the right", () => {
  const { drawn, byName } = at(fixtures.server);
  const [stub, entry, routes] = [byName["depuis Application web"], byName["Porte d'entrée"], byName.Routes];
  assert.ok(stub && entry && routes);
  assert.equal(stub.x, 20);
  assert.ok(stub.x + stub.w < entry.x && entry.x + entry.w < routes.x); // left → right
  const mid = (r: Rect) => r.y + r.h / 2;
  assert.equal(mid(stub), mid(entry));
  assert.equal(mid(entry), mid(routes));
  const base = byName["vers Base ◉ ligne enregistrée"];
  const mail = byName["vers Courriel ◉ courriel envoyé"];
  assert.ok(base && mail);
  assert.equal(mid(base), mid(routes)); // the store stays on the top line, the mail service goes above it
  assert.ok(mail.y + mail.h < base.y);
  const lower = ["Contrôle d'accès", "Modèles", "Accès aux données"].map((t) => byName[t] as Rect);
  assert.ok(lower.every((r) => r.y > routes.y + routes.h)); // the lower row
  assert.ok((lower[0] as Rect).x + (lower[0] as Rect).w / 2 > routes.x); // its first part hangs under Routes
  assert.equal(drawn.parts.find((p) => p.part.title === "Routes")?.chips.length, 5); // the 5 route files
  assert.equal(insideAroundText(fixtures.server), "+ 2 autour (réglages, migrations)");
  assert.deepEqual(drawn.entry, { x: 20, y: stub.y - 14 });
  assert.equal(drawn.sorties?.x, mail.x);
});

test("inside Application web, as the mock: start, pages, screens, client in a row; sign-in under; « écran mis à jour » leaves the screens", () => {
  const { drawn, byName } = at(fixtures.web);
  const row = ["depuis Utilisateur", "Démarrage", "Pages", "Écrans", "Client", "vers Serveur"].map((t) => byName[t] as Rect);
  for (let i = 1; i < row.length; i++) assert.ok((row[i - 1] as Rect).x + (row[i - 1] as Rect).w < (row[i] as Rect).x, `order at ${i}`);
  const [screens, client, signIn] = [byName["Écrans"], byName.Client, byName.Connexion] as Rect[];
  assert.ok(signIn && screens && client && signIn.y > screens.y + screens.h);
  const proof = drawn.arrows.find((a) => a.label.text === "joint la preuve");
  assert.ok(proof?.path.endsWith(`L${client.x + client.w / 2},${client.y + client.h}`)); // up into the client, from below
  const [screen] = drawn.outputs;
  assert.equal(screen?.output.label, "écran mis à jour");
  assert.ok(screen?.path.startsWith(`M${screens.x + screens.w / 2},${screens.y}`));
});

test("no two boxes overlap and every arrow has its verb, on every inside", () => {
  for (const inside of Object.values(fixtures)) {
    const { drawn } = at(inside);
    const rects = drawn.parts.map((p) => p.rect);
    for (let i = 0; i < rects.length; i++)
      for (let j = i + 1; j < rects.length; j++) assert.ok(!overlap(rects[i] as Rect, rects[j] as Rect), `${inside.title}: ${drawn.parts[i]?.part.title} / ${drawn.parts[j]?.part.title}`);
    assert.ok(drawn.arrows.length === inside.links.length && drawn.arrows.every((a) => a.label.text));
    const [, , width] = drawn.viewBox.split(" ").map(Number);
    assert.ok((width ?? 0) <= 1300, `${inside.title} fits the screen: ${width}`); // words stay readable at 1280 px
    assert.ok(drawn.parts.filter((p) => p.part.kind !== "stub").length <= 7);
  }
});

test("a lower part never sits under the stubs on the left (sqlite-utils: two ways in)", () => {
  const { byName } = at(fixtures.library);
  const ins = [byName["depuis Programme Python"], byName["depuis Commande"]] as Rect[];
  const lower = Object.values(byName).filter((r) => r.y >= 330 && r.x > 20);
  assert.ok(ins.every(Boolean) && lower.every((r) => r.x > (ins[0] as Rect).x + (ins[0] as Rect).w));
});
