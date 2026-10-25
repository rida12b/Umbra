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
interface Route {
  link: FloorLink;
  points: Point[];
  label: Point | null; // where its words go; null: words only in the panel
}
export interface FloorPlan {
  rects: Map<string, Rect>;
  routes: Route[];
  belt: Route[]; // the conveyor, segment by segment; a segment that wraps runs back left between the lines
  strip: Rect | null; // the band « Autour du projet »
  orphans: Rect | null; // the band « Pièces sans chemin connu »
  size: { width: number; height: number };
}

const ROOM = { w: 200, h: 212 }; // a 3-line title, 2 lines of words, the SORTIE's limit and a 2-line footer
const TAG = { w: 200, h: 114 }; // a 2-line name and a 3-line link to its room
const GAP = 88; // between two rooms: room for the arrow's words on three short lines (three rooms fit a laptop)
const STACK = 44; // between a room and its tags, and between two tags: room for the reply line and a short verb
const LINE_GAP = 52; // between two lines of the belt
const BAND = 44; // band titles and margins
const LANE = 10; // right of the last room of a line: the lane the belt takes down to the next line

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
  const gapBelow = new Map<string, number>(); // last room of a line → the middle of the gap under that line
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
    if (last && n < lines.length - 1) gapBelow.set(last, y - LINE_GAP / 2);
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

  const belt = floor.beltLinks.flatMap((link): Route[] => {
    const a = rects.get(link.from);
    const b = rects.get(link.to);
    if (!a || !b) return [];
    const y = a.y + a.h / 2;
    if (a.y === b.y) return [{ link, points: [{ x: a.x + a.w, y }, { x: b.x, y }], label: { x: (a.x + a.w + b.x) / 2, y: y - 34 } }];
    // Like a line of text: out to the right, down, back left between the lines, into the next line's first room.
    const gap = gapBelow.get(link.from) ?? a.y + a.h + LINE_GAP / 2;
    const lane = a.x + a.w + 20;
    const into = b.y + b.h / 2;
    const points = [{ x: a.x + a.w, y }, { x: lane, y }, { x: lane, y: gap }, { x: -18, y: gap }, { x: -18, y: into }, { x: b.x, y: into }];
    return [{ link, points, label: { x: Math.min(lane, available) / 2, y: gap - 14 } }];
  });
  const routes = floor.links.flatMap((link) => {
    const route = routeOf(link, rects, row, byId);
    return route ? [route] : [];
  });
  return { rects, routes, belt, strip, orphans, size: { width, height: y } };
}

function routeOf(link: FloorLink, rects: Map<string, Rect>, row: string[], byId: Map<string, FloorItem>): Route | null {
  const a = rects.get(link.from);
  const b = rects.get(link.to);
  if (!a || !b) return null;
  if (row.includes(link.from) && row.includes(link.to)) {
    // The belt draws how data goes forward; only an answer going back gets its own line, under the rooms.
    if (link.style !== "reply" || a.y !== b.y) return null;
    const under = Math.max(a.y + a.h, b.y + b.h) + 14;
    // Its words sit near its arrow head, clear of the lines that come up from the tags below the rooms.
    return { link, points: [{ x: a.x + 24, y: a.y + a.h }, { x: a.x + 24, y: under }, { x: b.x + b.w - 24, y: under }, { x: b.x + b.w - 24, y: b.y + b.h }], label: { x: b.x + b.w + 30, y: under + 24 } };
  }
  // A tag and what it hangs on, face to face in one column: a short line (the tag says the link in words).
  // Any other line would cross the floor: not drawn, the panel tells it when one of its ends is selected.
  const hangs = byId.get(link.from)?.attach === link.to || byId.get(link.to)?.attach === link.from;
  if (!hangs || a.x !== b.x) return null;
  const [top, bottom] = a.y < b.y ? [a, b] : [b, a];
  if ([...rects.entries()].some(([id, r]) => id !== link.from && id !== link.to && r.x === a.x && r.y > top.y && r.y < bottom.y)) return null;
  const x = a.x + 40;
  return { link, points: [{ x, y: a.y < b.y ? a.y + a.h : a.y }, { x, y: a.y < b.y ? b.y : b.y + b.h }], label: null };
}
