import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import type { ProjectModel } from "../api";
import { buildRoom } from "./room.ts";
import { placeRoom, type Rect } from "./roomLayout.ts";

const load = (name: string): ProjectModel =>
  JSON.parse(readFileSync(new URL(`../../test-fixtures/${name}.json`, import.meta.url), "utf-8")) as ProjectModel;
const overlap = (a: Rect, b: Rect) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
const rooms = [["watchdog", "api"], ["watchdog", "memoire"], ["justicia", "site"], ["justicia", "api"], ["justicia", "courriers"], ["justicia", "outillage"]] as const;

for (const [name, bloc] of rooms)
  for (const width of [460, 790, 990, 1400])
    test(`${name}/${bloc} at ${width} px: nothing overlaps, nothing past the width, read in belt order`, () => {
      const room = buildRoom(load(name), bloc)!;
      const plan = placeRoom(room, width);
      const all = [...plan.rects.entries()].filter(([key]) => key !== "band");
      for (const [i, [a, ra]] of all.entries()) for (const [b, rb] of all.slice(i + 1)) assert.ok(!overlap(ra, rb), `${a} overlaps ${b}`);
      assert.ok(plan.size.width <= Math.max(width, 180), `${plan.size.width} > ${width}`);
      const at = (id: string) => plan.rects.get(id)!.y * 10_000 + plan.rects.get(id)!.x;
      const order = room.belt.map((m) => at(m.id));
      assert.deepEqual(order, [...order].sort((p, q) => p - q));
      for (const door of room.doors) assert.ok(plan.rects.has(`door:${door.bloc}`), door.bloc);
    });

test("the Watchdog entry service fits one line on a 1440 screen (≈990 px for the map)", () => {
  const plan = placeRoom(buildRoom(load("watchdog"), "api")!, 990);
  const ys = new Set(buildRoom(load("watchdog"), "api")!.belt.map((m) => plan.rects.get(m.id)!.y));
  assert.equal(ys.size, 1);
  assert.equal(plan.doorLinks.length, 2); // agent → first machine, last machine → store
});
