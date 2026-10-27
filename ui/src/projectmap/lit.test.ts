import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import type { Highlight, LitStep, SystemMap } from "../api.ts";
import { geometry, type Rect } from "./geometry.ts";
import { applyEvent, callouts, copyText, gapsUnder, labelY, newer, viewBoxWith } from "./lit.ts";

const template = JSON.parse(readFileSync(new URL("../../test-fixtures/system-fastapi-template.json", import.meta.url), "utf-8")) as SystemMap;
const step = (n: number, box: string, label: string, path: string, note: string): LitStep => ({ n, box, label, path, note, why: "" });

// The question of the mock (p-question.png): « où j'ajoute un champ prix à Item ? ».
const price: Highlight = {
  caption: "où j'ajoute un champ prix à Item ?",
  boxes: ["web:frontend", "server:backend", "store:db"],
  steps: [
    step(1, "web:frontend", "components/Items/", "frontend/src/components/Items/", "formulaire, tableau"),
    step(2, "web:frontend", "client/", "frontend/src/client/", "recréé automatiquement"),
    step(3, "server:backend", "models.py", "backend/app/models.py", "ajouter le champ"),
    step(4, "server:backend", "alembic/versions/", "backend/app/alembic/versions/", "nouvelle migration"),
    step(5, "server:backend", "api/routes/items.py", "backend/app/api/routes/items.py", "vérifier"),
  ],
  files: ["frontend/src/components/Items/", "frontend/src/client/", "backend/app/models.py", "backend/app/alembic/versions/", "backend/app/api/routes/items.py"],
  serial: 3,
};

const overlap = (a: Rect, b: Rect) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

test("each lit box with steps gets one callout under it, rows in step order, side by side without overlap", () => {
  const drawn = geometry(template);
  const placed = callouts(drawn, price);
  assert.deepEqual(
    placed.map((c) => [c.box, c.rows.map((r) => r.step.n)]),
    [
      ["web:frontend", [1, 2]],
      ["server:backend", [3, 4, 5]],
    ],
  ); // Base is lit but has no step: no callout
  const [web, server] = placed as [(typeof placed)[0], (typeof placed)[0]];
  assert.ok(!overlap(web, server), "the two callouts overlap");
  for (const callout of placed) {
    const box = drawn.boxes.find((b) => b.box.id === callout.box)?.rect as Rect;
    assert.equal(callout.y, box.y + box.h + 28); // just under its box (mock: 260 → 288)
    const [x1, y1, x2, y2] = callout.connector;
    assert.ok(x1 === x2 && x1 > callout.x && x1 < callout.x + callout.w, "the connector leaves the callout's side");
    assert.deepEqual([y1, y2], [box.y + box.h, callout.y]);
    assert.ok(callout.x >= 16);
  }
});

test("a callout that would leave the map grows the view downwards; the map itself does not move", () => {
  const drawn = geometry(template);
  const many: Highlight = { ...price, steps: [1, 2, 3, 4, 5, 6].map((n) => step(n, "server:backend", `f${n}.py`, `backend/app/f${n}.py`, "")) };
  const grown = viewBoxWith(drawn.viewBox, callouts(drawn, many)).split(" ").map(Number);
  const plain = drawn.viewBox.split(" ").map(Number);
  assert.deepEqual(grown.slice(0, 3), plain.slice(0, 3));
  assert.ok((grown[3] as number) >= (plain[3] as number));
  assert.equal(viewBoxWith(drawn.viewBox, []), drawn.viewBox);
});

test("« copier pour Claude » copies the question and the files, as the mock", () => {
  assert.equal(
    copyText(price),
    "Tâche : où j'ajoute un champ prix à Item ?\nFichiers (5) :\n- frontend/src/components/Items/\n- frontend/src/client/\n" +
      "- backend/app/models.py\n- backend/app/alembic/versions/\n- backend/app/api/routes/items.py",
  );
});

test("the live stream: show lights, cleared dims nothing, anything else reads the project again", () => {
  const idle: { connected: boolean; revision: number; highlight: Highlight | null } = { connected: false, revision: 4, highlight: null };
  const lit = applyEvent(idle, JSON.stringify({ type: "show", highlight: price }));
  assert.deepEqual(lit, { connected: true, revision: 4, highlight: price }); // the map is not read again
  assert.equal(applyEvent(lit, JSON.stringify({ type: "cleared" })).highlight, null);
  assert.equal(applyEvent(lit, JSON.stringify({ type: "indexed", changed: [] })).revision, 5);
  assert.equal(applyEvent(lit, "not json").revision, 5);
  const older = { ...price, serial: 2, caption: "old" };
  assert.deepEqual(applyEvent(lit, JSON.stringify({ type: "show", highlight: older })).highlight, price); // late answer
  assert.equal(newer(price, null), null);
  assert.equal(newer(null, older), older);
});

test("a box with another box right under it gets its callout on its right, clear of every box (sqlite-utils)", () => {
  const sqlite = JSON.parse(readFileSync(new URL("../../test-fixtures/system-sqlite-utils.json", import.meta.url), "utf-8")) as SystemMap;
  const drawn = geometry(sqlite);
  const command = sqlite.boxes.find((b) => b.title === "Commande")?.id as string;
  const library = sqlite.boxes.find((b) => b.title === "Bibliothèque")?.id as string;
  const export_: Highlight = {
    ...price,
    boxes: [command, library],
    steps: [step(1, command, "cli.py", "sqlite_utils/cli.py", "ajouter la commande"), step(2, library, "db.py", "sqlite_utils/db.py", "lire les lignes")],
  };
  const placed = callouts(drawn, export_);
  const commandBox = drawn.boxes.find((b) => b.box.id === command)?.rect as Rect;
  const onRight = placed.find((c) => c.box === command) as (typeof placed)[0];
  assert.ok(onRight.x >= commandBox.x + commandBox.w, "the command's callout is not on its right");
  for (const callout of placed) for (const box of drawn.boxes) assert.ok(!overlap(callout, box.rect), `${callout.box} callout covers ${box.box.id}`);
  const [x1, y1, x2, y2] = onRight.connector;
  assert.deepEqual([x1, x2, y1 === y2], [commandBox.x + commandBox.w, onRight.x, true]);
  const midLine = commandBox.y + commandBox.h / 2; // where the command's output line leaves it
  assert.ok(onRight.y > midLine, "the command's callout sits on its output line");
  const chip = drawn.around as NonNullable<typeof drawn.around>;
  for (const callout of placed) assert.ok(!overlap(callout, { ...chip, w: chip.w + 16, h: 36 }), `${callout.box} callout touches the pill`);
  assert.deepEqual(gapsUnder(placed).length, 1); // only the callout under its box has a gap to cover
});

test("between a lit box and its callout only the blue connector shows; a covered arrow label moves under the callout", () => {
  const drawn = geometry(template);
  const placed = callouts(drawn, price);
  const gaps = gapsUnder(placed);
  assert.equal(gaps.length, 2);
  for (const [i, gap] of gaps.entries()) {
    const callout = placed[i] as (typeof placed)[0];
    assert.deepEqual([gap.x, gap.w, gap.y + gap.h], [callout.x, callout.w, callout.y]);
    assert.ok(gap.y > callout.connector[1], "the gap covers the box's border");
  }
  const server = placed[1] as (typeof placed)[0];
  const inside = labelY(server.x + 30, server.y + 20, placed);
  assert.equal(inside, server.y + server.h + 13);
  assert.equal(labelY(server.x + 30, server.y - 30, placed), server.y - 30); // a free label stays
});
