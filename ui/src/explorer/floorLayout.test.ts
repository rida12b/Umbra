import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import type { ProjectModel } from "../api";
import { buildFloor } from "./floor.ts";
import { placeFloor, type Rect } from "./floorLayout.ts";

const load = (name: string): ProjectModel =>
  JSON.parse(readFileSync(new URL(`../../test-fixtures/${name}.json`, import.meta.url), "utf-8")) as ProjectModel;
const overlap = (a: Rect, b: Rect) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

for (const name of ["watchdog", "justicia"])
  for (const width of [1040, 880, 1400])
    test(`${name} at ${width} px: every part placed, nothing overlaps, no sideways scroll`, () => {
      const floor = buildFloor(load(name));
      const plan = placeFloor(floor, width);
      assert.deepEqual([...plan.rects.keys()].sort(), floor.items.map((i) => i.id).sort());
      const all = [...plan.rects.entries()];
      for (const [i, [a, ra]] of all.entries())
        for (const [b, rb] of all.slice(i + 1)) assert.ok(!overlap(ra, rb), `${a} overlaps ${b}`);
      assert.ok(plan.size.width <= width, `${plan.size.width} > ${width}`);
    });

test("ENTRÉE opens the first line on the left, SORTIE closes the belt", () => {
  for (const name of ["watchdog", "justicia"]) {
    const floor = buildFloor(load(name));
    const plan = placeFloor(floor, 1040);
    const entree = plan.rects.get(floor.entree!)!;
    const belt = [floor.entree!, ...floor.belt].map((id) => plan.rects.get(id)!);
    assert.equal(entree.x, 0);
    assert.ok(belt.every((r) => r.y >= entree.y));
    const last = belt.at(-1)!;
    assert.ok(belt.every((r) => r.y < last.y || (r.y === last.y && r.x <= last.x)));
  }
});

test("a long belt wraps to a new line instead of growing sideways", () => {
  const floor = buildFloor(load("justicia"));
  const plan = placeFloor(floor, 1040);
  assert.ok(plan.belt.some((r) => r.points.length > 2));
});

test("Watchdog's three rooms fit one line at the mockup's width (1440 px: 1040 px canvas − scrollbar − padding ≈ 990 px)", () => {
  for (const name of ["watchdog", "watchdog-v17"]) {
    const floor = buildFloor(load(name));
    assert.ok(placeFloor(floor, 990).belt.every((r) => r.points.length === 2), name);
  }
});

test("no drawn line runs through a part it does not join", () => {
  for (const name of ["watchdog", "justicia"])
    for (const width of [800, 1040]) {
      const plan = placeFloor(buildFloor(load(name)), width);
      for (const { link, points } of [...plan.routes, ...plan.belt])
        for (let i = 1; i < points.length; i++) {
          const [p, q] = [points[i - 1]!, points[i]!];
          for (const [id, r] of plan.rects) {
            if (id === link.from || id === link.to) continue;
            const inside = (x: number, y: number) => x > r.x + 1 && x < r.x + r.w - 1 && y > r.y + 1 && y < r.y + r.h - 1;
            for (let t = 0; t <= 20; t++) {
              const x = p.x + ((q.x - p.x) * t) / 20;
              const y = p.y + ((q.y - p.y) * t) / 20;
              assert.ok(!inside(x, y), `${name}@${width}: ${link.id} crosses ${id}`);
            }
          }
        }
    }
});

test("every room after ENTRÉE has a drawn belt segment coming in, with its words", () => {
  for (const name of ["watchdog", "justicia"])
    for (const width of [800, 1040, 1400]) {
      const floor = buildFloor(load(name));
      const plan = placeFloor(floor, width);
      for (const id of floor.belt) {
        const incoming = plan.belt.find((r) => r.link.to === id);
        assert.ok(incoming && incoming.label && incoming.link.verb, `${name}@${width}: nothing feeds ${id}`);
      }
    }
});
