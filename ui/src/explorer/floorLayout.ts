import type { Floor, FloorItem, FloorLink } from "./floor.ts";

// Where each piece of the floor sits, as in the validated mockup (inventaire.md V8-V18). The belt reads
// left to right like a line of text and wraps when the screen is too narrow (never a sideways scroll).
// A person or tool that joins from the side stands above its room; what a room calls hangs below it;
// the strip of things that never run is the last line. Pure and measured: floorLayout.test.ts.

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

// Widths by kind, as in the mockup: a person at the entry is narrow, a working room lists its machines.
const WIDTH = { person: 180, room: 280, store: 220, outside: 190, tool: 190 } as const;
const HEIGHT = 190; // a belt line; a room listing many machines makes its line taller (roomHeight)
const TAG = { w: 230, h: 96 }; // a 2-line name and a 2-line link to its room
const SIDE = { w: 280, h: 84 }; // a person or supplier hung on a room: as wide and low as the mockup's card (V8)
const GAP = 120; // between two rooms: the action words above the belt, the data words below it (112 px chips)
const STACK = 44; // between a room and its tags, and between two tags: room for the reply line and a short verb
const LINE_GAP = 52; // between two lines of the belt
const BAND = 44; // band titles and margins
const LANE = 10; // right of the last room of a line: the lane the belt takes down to the next line

/** `machines`: how many machines each room lists on its card (the mockup previews them, V14). */
export function placeFloor(floor: Floor, available: number, machines: Record<string, number> = {}, settings = false): FloorPlan {
  const byId = new Map(floor.items.map((i) => [i.id, i]));
  const row = [...(floor.entree ? [floor.entree] : []), ...floor.belt];
  const widthOf = (id: string) => WIDTH[byId.get(id)?.shape ?? "room"];
  const roomHeight = (id: string) => Math.max(HEIGHT, 100 + 26 * Math.min(machines[id] ?? 0, 5) + (machines[id] ? 24 : 0));
  const lines: string[][] = [];
  let used = 0;
  for (const id of row) {
    const w = widthOf(id);
    const line = lines.at(-1);
    if (line && used + GAP + w <= available - LANE * 2) {
      line.push(id);
      used += GAP + w;
    } else {
      lines.push([id]);
      used = w;
    }
  }

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
    // Above: a person, or a part that sends to its room (the mockup's installer who starts it, V8). Below: what the room
    // calls (a service, a store), so a second belt line is not pushed down by everything the first one uses.
    const sends = floor.links.some((l) => l.from === item.id && l.to === item.attach);
    const side = item.role === "side" && (item.shape === "person" || sends) ? above : below;
    side.set(col, [...(side.get(col) ?? []), item.id]);
  }

  const rects = new Map<string, Rect>();
  const gapBelow = new Map<string, number>(); // last room of a line → the middle of the gap under that line
  let y = 0;
  let width = 0;
  lines.forEach((line, n) => {
    const up = Math.max(0, ...line.map((id) => above.get(id)?.length ?? 0));
    const down = Math.max(0, ...line.map((id) => below.get(id)?.length ?? 0));
    const beltY = y + up * (SIDE.h + STACK);
    const h = Math.max(...line.map(roomHeight));
    let x = 0;
    line.forEach((id) => {
      const w = widthOf(id);
      // A store keeps its own height, centred on the belt (it lists no machines); rooms and people take the line's height.
      const own = byId.get(id)?.shape === "store" ? Math.min(h, HEIGHT) : h;
      rects.set(id, { x, y: beltY + (h - own) / 2, w, h: own });
      // Tags are centred on their room, never wider than the room and its two half-gaps.
      const tw = Math.min(SIDE.w, w + GAP - 16);
      const tx = x + (w - tw) / 2;
      (above.get(id) ?? []).forEach((tag, k) => rects.set(tag, { x: tx, y: beltY - (k + 1) * (SIDE.h + STACK), w: tw, h: SIDE.h }));
      (below.get(id) ?? []).forEach((tag, k) => rects.set(tag, { x: tx, y: beltY + h + STACK + 40 + k * (SIDE.h + STACK), w: tw, h: SIDE.h }));
      width = Math.max(width, x + w + LANE * 2);
      x += w + GAP;
    });
    y = beltY + h + down * (SIDE.h + STACK) + (down ? 40 : 70) + LINE_GAP; // room for the reply path and its words
    const last = line.at(-1);
    if (last && n < lines.length - 1) gapBelow.set(last, y - LINE_GAP / 2);
  });

  const band = (ids: string[]): Rect | null => {
    if (ids.length === 0) return null;
    const perRow = Math.max(1, Math.floor((available - 8) / (TAG.w + 16))); // n tags take n × (w + 16) + 8 px
    const top = y + BAND;
    ids.forEach((id, i) => rects.set(id, { x: (i % perRow) * (TAG.w + 16), y: top + Math.floor(i / perRow) * (TAG.h + 16), w: TAG.w, h: TAG.h }));
    const rowsUsed = Math.ceil(ids.length / perRow);
    const tags = Math.min(ids.length, perRow) * (TAG.w + 16) + 8;
    // As wide as the floor (V18): the band's frame reaches into the padding, the floor's width does not grow for it.
    const rect = { x: -12, y: y + 8, w: Math.max(width + 24, tags), h: BAND - 8 + rowsUsed * (TAG.h + 16) };
    width = Math.max(width, tags);
    y = rect.y + rect.h + 16;
    return rect;
  };
  const orphans = band(floor.items.filter((i) => i.role === "orphan").map((i) => i.id));
  const strip = band([...floor.strip, ...(settings ? ["settings"] : [])]); // the project's settings card sits in the strip (V18)

  // Same belt line: by membership, never by y (a store is centred on the belt, so its top is lower than a room's).
  const lineOf = new Map(lines.flatMap((line, n) => line.map((id) => [id, n] as const)));
  const sameLine = (p: string, q: string) => lineOf.has(p) && lineOf.get(p) === lineOf.get(q);
  const belt = floor.beltLinks.flatMap((link): Route[] => {
    const a = rects.get(link.from);
    const b = rects.get(link.to);
    if (!a || !b) return [];
    const y = a.y + a.h / 2;
    if (sameLine(link.from, link.to)) return [{ link, points: [{ x: a.x + a.w, y }, { x: b.x, y }], label: { x: (a.x + a.w + b.x) / 2, y: y - 30 } }];
    // Like a line of text: out to the right, down, back left between the lines, into the next line's first room.
    const gap = gapBelow.get(link.from) ?? a.y + a.h + LINE_GAP / 2;
    const lane = a.x + a.w + 20;
    const into = b.y + b.h / 2;
    const points = [{ x: a.x + a.w, y }, { x: lane, y }, { x: lane, y: gap }, { x: -18, y: gap }, { x: -18, y: into }, { x: b.x, y: into }];
    return [{ link, points, label: { x: Math.min(lane, available) / 2, y: gap - 14 } }];
  });
  const routes = floor.links.flatMap((link) => {
    const route = routeOf(link, rects, row, byId, sameLine);
    return route ? [route] : [];
  });
  return { rects, routes, belt, strip, orphans, size: { width, height: y } };
}

function routeOf(link: FloorLink, rects: Map<string, Rect>, row: string[], byId: Map<string, FloorItem>, sameLine: (p: string, q: string) => boolean): Route | null {
  const a = rects.get(link.from);
  const b = rects.get(link.to);
  if (!a || !b) return null;
  if (row.includes(link.from) && row.includes(link.to)) {
    // The belt draws how data goes forward; only an answer going back gets its own line, under the rooms.
    if (link.style !== "reply" || !sameLine(link.from, link.to)) return null;
    // The answer runs back under the belt, dashed, and climbs into the sender (V16); its words sit under it (V17).
    const under = Math.max(a.y + a.h, b.y + b.h) + 22;
    return { link, points: [{ x: a.x + a.w / 2, y: a.y + a.h }, { x: a.x + a.w / 2, y: under }, { x: b.x + b.w / 2, y: under }, { x: b.x + b.w / 2, y: b.y + b.h }], label: { x: (a.x + a.w / 2 + b.x + b.w / 2) / 2, y: under + 26 } };
  }
  // A tag and what it hangs on, face to face in one column: a short line (the tag says the link in words).
  // Any other line would cross the floor: not drawn, the panel tells it when one of its ends is selected.
  const hangs = byId.get(link.from)?.attach === link.to || byId.get(link.to)?.attach === link.from;
  // Tags and rooms have their own widths (V8): face to face means their columns overlap, not that they start at the same x.
  const left = Math.max(a.x, b.x);
  const right = Math.min(a.x + a.w, b.x + b.w);
  if (!hangs || right - left < 24) return null;
  const [top, bottom] = a.y < b.y ? [a, b] : [b, a];
  const between = (r: Rect) => r.x < right && r.x + r.w > left && r.y > top.y && r.y < bottom.y;
  if ([...rects.entries()].some(([id, r]) => id !== link.from && id !== link.to && between(r))) return null;
  // Near the right edge: the answer's words sit under the room's middle (V17) and must not be crossed.
  const x = right - 32;
  return { link, points: [{ x, y: a.y < b.y ? a.y + a.h : a.y }, { x, y: a.y < b.y ? b.y : b.y + b.h }], label: null };
}
