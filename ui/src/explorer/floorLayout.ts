import type { Floor, FloorItem, FloorLink } from "./floor.ts";

// Where each piece of the floor sits. The belt reads left to right like a line of text and wraps to a
// new line when the screen is too narrow (a long belt never makes the page scroll sideways). Above
// each room hang what it calls (suppliers), below it what joins from the side; the strip of things
// that never run is the last line. Pure and measured: floorLayout.test.ts checks nothing overlaps.

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}
export interface Point {
  x: number;
  y: number;
}
export interface Route {
  link: FloorLink;
  points: Point[];
  label: Point | null; // where its words go; null: words only in the panel
}
export interface FloorPlan {
  rects: Map<string, Rect>;
  routes: Route[];
  wraps: { from: string; to: string; gapY: number }[]; // the belt going on to the next line: last room → first room, back left at gapY
  strip: Rect | null; // the band « Autour du projet »
  orphans: Rect | null; // the band « Pièces sans trajet connu »
  size: { width: number; height: number };
}

export const ROOM = { w: 200, h: 156 };
export const TAG = { w: 200, h: 76 };
const GAP = 88; // between two rooms: room for the arrow's words on three short lines (three rooms fit a laptop)
const STACK = 44; // between a room and its tags, and between two tags: room for the reply line and a short verb
const LINE_GAP = 52; // between two lines of the belt
const BAND = 44; // band titles and margins
const LANE = 10; // a link that must pass a room runs in the gutter right of the column

export function placeFloor(floor: Floor, available: number): FloorPlan {
  const byId = new Map(floor.items.map((i) => [i.id, i]));
  const row = [...(floor.entree ? [floor.entree] : []), ...floor.belt];
  const perLine = Math.max(1, Math.floor((available - LANE * 2 + GAP) / (ROOM.w + GAP)));
  const lines: string[][] = [];
  for (let i = 0; i < row.length; i += perLine) lines.push(row.slice(i, i + perLine));

  // Tags are stacked in the column of the belt room they belong to (through any number of hangs).
  const column = (item: FloorItem): string | null => {
    if (row.includes(item.id)) return item.id;
    const anchor = item.attach ? byId.get(item.attach) : undefined;
    return anchor ? column(anchor) : null;
  };
  const above = new Map<string, string[]>();
  const below = new Map<string, string[]>();
  for (const item of floor.items) {
    if (item.role !== "supplier" && item.role !== "side") continue;
    const col = column(item);
    if (!col) continue;
    const side = item.role === "supplier" ? above : below;
    side.set(col, [...(side.get(col) ?? []), item.id]);
  }

  const rects = new Map<string, Rect>();
  const wraps: { from: string; to: string; gapY: number }[] = [];
  let y = 0;
  let width = 0;
  lines.forEach((line, n) => {
    const up = Math.max(0, ...line.map((id) => above.get(id)?.length ?? 0));
    const down = Math.max(0, ...line.map((id) => below.get(id)?.length ?? 0));
    const beltY = y + up * (TAG.h + STACK);
    line.forEach((id, i) => {
      const x = i * (ROOM.w + GAP);
      rects.set(id, { x, y: beltY, w: ROOM.w, h: ROOM.h });
      (above.get(id) ?? []).forEach((tag, k) => rects.set(tag, { x, y: beltY - (k + 1) * (TAG.h + STACK), w: TAG.w, h: TAG.h }));
      (below.get(id) ?? []).forEach((tag, k) => rects.set(tag, { x, y: beltY + ROOM.h + STACK + k * (TAG.h + STACK), w: TAG.w, h: TAG.h }));
      width = Math.max(width, x + ROOM.w + LANE * 2);
    });
    y = beltY + ROOM.h + down * (TAG.h + STACK) + (down ? 0 : 24) + LINE_GAP;
    const last = line.at(-1);
    const next = lines[n + 1]?.[0];
    if (last && next) wraps.push({ from: last, to: next, gapY: y - LINE_GAP / 2 });
  });

  const band = (ids: string[]): Rect | null => {
    if (ids.length === 0) return null;
    const perRow = Math.max(1, Math.floor((Math.max(width, available) + 16) / (TAG.w + 16)));
    const top = y + BAND;
    ids.forEach((id, i) => rects.set(id, { x: (i % perRow) * (TAG.w + 16), y: top + Math.floor(i / perRow) * (TAG.h + 16), w: TAG.w, h: TAG.h }));
    const rowsUsed = Math.ceil(ids.length / perRow);
    const rect = { x: -12, y: y + 8, w: Math.min(ids.length, perRow) * (TAG.w + 16) + 8, h: BAND - 8 + rowsUsed * (TAG.h + 16) };
    width = Math.max(width, rect.w);
    y = rect.y + rect.h + 16;
    return rect;
  };
  const orphans = band(floor.items.filter((i) => i.role === "orphan").map((i) => i.id));
  const strip = band(floor.strip);

  const lanes = new Map<number, number>(); // gutter routes already in each column: each gets its own lane
  const routes = floor.links.flatMap((link) => {
    const route = routeOf(link, rects, row, byId, lanes);
    return route ? [route] : [];
  });
  return { rects, routes, wraps, strip, orphans, size: { width, height: y } };
}

const mid = (r: Rect): Point => ({ x: r.x + r.w / 2, y: r.y + r.h / 2 });

function routeOf(link: FloorLink, rects: Map<string, Rect>, row: string[], byId: Map<string, FloorItem>, lanes: Map<number, number>): Route | null {
  const a = rects.get(link.from);
  const b = rects.get(link.to);
  if (!a || !b) return null;
  const onBelt = row.includes(link.from) && row.includes(link.to);
  if (onBelt && a.y === b.y) {
    const [left, right] = a.x < b.x ? [a, b] : [b, a];
    if (link.style === "reply") {
      // The answer runs back under the rooms, dashed.
      const under = Math.max(a.y + a.h, b.y + b.h) + 14;
      // Its words sit near its arrow head, clear of the lines that come up from the tags below the rooms.
      return { link, points: [{ x: a.x + 24, y: a.y + a.h }, { x: a.x + 24, y: under }, { x: b.x + b.w - 24, y: under }, { x: b.x + b.w - 24, y: b.y + b.h }], label: { x: b.x + b.w + 30, y: under + 24 } };
    }
    const next = Math.abs(row.indexOf(link.from) - row.indexOf(link.to)) === 1;
    if (!next && link.style !== "data") return null; // a jump over rooms is drawn for the data only
    const y = left.y + left.h / 2 + (next ? 0 : -left.h / 2 - 12); // a jump over a room goes over its top edge
    const from = a.x < b.x ? { x: a.x + a.w, y } : { x: a.x, y };
    const to = a.x < b.x ? { x: b.x, y } : { x: b.x + b.w, y };
    if (next) return { link, points: [from, to], label: { x: (left.x + left.w + right.x) / 2, y: y - 34 } };
    return { link, points: [{ x: mid(a).x, y: a.y }, { x: mid(a).x, y }, { x: mid(b).x, y }, { x: mid(b).x, y: b.y }], label: null };
  }
  // A tag and what it hangs on share a column: a straight line between their facing edges, words beside it.
  // Only that one link of a tag is drawn; its others would cross the floor.
  const hangs = byId.get(link.from)?.attach === link.to || byId.get(link.to)?.attach === link.from;
  if (hangs && a.x === b.x) {
    const [top, bottom] = a.y < b.y ? [a, b] : [b, a];
    const between = () => [...rects.entries()].some(([other, r]) => other !== link.from && other !== link.to && r.x === a.x && r.y > top.y && r.y < bottom.y);
    if (!between()) {
      const x = a.x + 40;
      return { link, points: [{ x, y: a.y < b.y ? a.y + a.h : a.y }, { x, y: a.y < b.y ? b.y : b.y + b.h }], label: { x: x + 52, y: (top.y + top.h + bottom.y) / 2 + 6 } };
    }
    // Something sits in between (a side door of a supplier): go round by the gutter on the right, one lane each.
    const lane = lanes.get(a.x) ?? 0;
    lanes.set(a.x, lane + 1);
    const x = a.x + a.w + 8 + lane * 7;
    return { link, points: [{ x: a.x + a.w, y: mid(a).y }, { x, y: mid(a).y }, { x, y: mid(b).y }, { x: b.x + b.w, y: mid(b).y }], label: null };
  }
  // Anything else would cross rooms: not drawn. The panel tells it when one of its ends is selected.
  return null;
}
