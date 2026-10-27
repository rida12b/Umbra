import type { SystemBox, SystemLink, SystemMap, SystemOutput } from "../api";

// Pixel geometry of the Level 0 map (mock `docs/design/2026-10-27-project-map/prototype.html`), from the cells the
// engine stored: column 0 = who comes in, then the parts left → right, outside services under their caller;
// ◉ outputs in one column on the right; « + N autour » bottom left. Pure: same map, same drawing.

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Label {
  x: number;
  y: number;
  anchor: "start" | "middle" | "end";
  text: string;
}

export interface DrawnBox {
  box: SystemBox;
  rect: Rect;
}

export interface DrawnArrow {
  key: string;
  link: SystemLink;
  path: string;
  label: Label;
  back: boolean; // the way back of a two-way link (« répond »)
}

export interface DrawnOutput {
  output: SystemOutput;
  path: string;
  at: [number, number];
}

export interface Geometry {
  viewBox: string;
  boxes: DrawnBox[];
  arrows: DrawnArrow[];
  outputs: DrawnOutput[];
  entries: { y: number; arrowEnd: number }[]; // one ENTRÉE per person coming in
  sorties: { x: number; y: number } | null;
  around: { x: number; y: number; w: number } | null;
}

const TOP = 100;
const ROW_Y = 150;
const ROW_STEP = 200;
const OUTSIDE_STEP = 270; // a row of outside services only, hung under their caller: a longer arrow (mock)
const BOX_H = 110;
const OUTSIDE_H = 90;
const OUT_MIN_X = 1048;
const OUT_LABEL_W = 152;
const LANE_GAP = 38;
const CHIP_H = 36;
const MIN_VIEW_H = 480; // the mock's view: a small map sits where a big one would, not lower

export function aroundText(map: SystemMap): string {
  const named = map.around.map((a) => a.short).filter(Boolean).slice(0, 2);
  return `+ ${map.around.length} outils autour${named.length ? ` (${named.join(", ")}…)` : ""}`;
}

export function geometry(map: SystemMap): Geometry {
  const columns = Math.max(1, ...map.boxes.filter((b) => b.kind !== "actor").map((b) => b.col));
  const narrow = columns <= 2; // few columns: wider boxes, more air between them (mock p-sqlite)
  const start = narrow ? 300 : 250;
  const step = narrow ? 390 : 280;
  const width = narrow ? 220 : 200;
  const actorWidth = narrow ? 150 : 120;
  const actorX = narrow ? 70 : 80;
  const rects = new Map<string, Rect>();
  const sources = new Set(map.links.map((l) => l.source));
  const rowY = rowTops(map.boxes, narrow ? ROW_Y - 5 : ROW_Y); // mock p-sqlite: 145
  for (const box of map.boxes) {
    const y = rowY[box.row] ?? ROW_Y;
    const store = box.kind === "box" && !sources.has(box.id); // where data ends (a base, a file): a bit narrower, as the mock
    const rect =
      box.kind === "actor"
        ? { x: actorX, y, w: actorWidth, h: BOX_H }
        : { x: start + (box.col - 1) * step, y, w: store ? width - 20 : width, h: box.kind === "external" ? OUTSIDE_H : BOX_H };
    rects.set(box.id, rect);
  }
  const lastRight = Math.max(start + width, ...[...rects.values()].map((r) => r.x + r.w));
  const outX = Math.max(OUT_MIN_X, lastRight + 38);
  const bottom = Math.max((rowY[0] ?? ROW_Y) + BOX_H, ...[...rects.values()].map((r) => r.y + r.h));

  const outside = new Set(map.boxes.filter((b) => b.kind === "external").map((b) => b.id));
  const arrows = map.links.flatMap((link) => arrowsOf(link, rects, outside));
  let lanes = 0;
  const outputs = map.outputs.flatMap((output): DrawnOutput[] => {
    const box = map.boxes.find((b) => b.id === output.box);
    const rect = rects.get(output.box);
    if (!box || !rect) return [];
    const blocked = map.boxes.some((b) => b.row === box.row && b.col > box.col);
    if (!blocked) {
      const y = rect.y + Math.min(55, rect.h / 2);
      return [{ output, path: `M${rect.x + rect.w},${y} L${outX - 8},${y}`, at: [outX, y] }];
    }
    // Something stands on its right: down under every box, then right (mock: « écran mis à jour »).
    const y = bottom + LANE_GAP + lanes++ * 34;
    const x = rect.x + 50;
    return [{ output, path: `M${x},${rect.y + rect.h} L${x},${y} L${outX - 8},${y}`, at: [outX, y] }];
  });

  const firstLane = bottom + LANE_GAP;
  const chipY = lanes > 0 ? firstLane - CHIP_H / 2 - 10 : bottom + 45;
  const around = map.around.length ? { x: 24, y: chipY, w: Math.max(220, aroundText(map).length * 7.4 + 34) } : null;
  const lowest = Math.max(around ? chipY + CHIP_H : 0, bottom + (lanes ? LANE_GAP + (lanes - 1) * 34 + 12 : 0));
  const actors = map.boxes.filter((b) => b.kind === "actor").map((b) => rects.get(b.id) as Rect);
  return {
    viewBox: `0 ${TOP} ${outX + OUT_LABEL_W} ${Math.max(MIN_VIEW_H, lowest + 24 - TOP)}`,
    boxes: map.boxes.map((box) => ({ box, rect: rects.get(box.id) as Rect })),
    arrows,
    outputs,
    entries: actors.map((r) => ({ y: r.y, arrowEnd: narrow ? r.x : r.x - 4 })),
    sorties: outputs.length ? { x: outX - 12, y: 128 } : null,
    around,
  };
}

/** The top of each row: one step down, longer when the row holds only outside services (mock: Courriel). */
function rowTops(boxes: SystemBox[], first: number): number[] {
  const rows = Math.max(0, ...boxes.map((b) => b.row));
  const tops = [first];
  for (let row = 1; row <= rows; row++) {
    const inRow = boxes.filter((b) => b.row === row);
    const outsideOnly = inRow.length > 0 && inRow.every((b) => b.kind === "external");
    tops.push((tops[row - 1] ?? first) + (outsideOnly ? OUTSIDE_STEP : ROW_STEP));
  }
  return tops;
}

function arrowsOf(link: SystemLink, rects: Map<string, Rect>, outside: Set<string>): DrawnArrow[] {
  const s = rects.get(link.source);
  const t = rects.get(link.target);
  if (!s || !t) return [];
  const drawn = (path: string, label: Label, back = false): DrawnArrow => ({ key: `${link.id}${back ? "<" : ""}`, link, path, label, back });
  const sameRow = s.y === t.y;
  if (sameRow && t.x > s.x) {
    const [x1, x2] = [s.x + s.w, t.x];
    const mid = (x1 + x2) / 2;
    if (!link.back) return [drawn(`M${x1},${s.y + 55} L${x2},${s.y + 55}`, { x: mid, y: s.y + 45, anchor: "middle", text: link.verb })];
    return [
      drawn(`M${x1},${s.y + 40} L${x2},${s.y + 40}`, { x: mid, y: s.y + 30, anchor: "middle", text: link.verb }),
      drawn(`M${x2},${s.y + 78} L${x1},${s.y + 78}`, { x: mid, y: s.y + 100, anchor: "middle", text: link.back }, true),
    ];
  }
  if (s.x === t.x && t.y > s.y) {
    const x = s.x + s.w / 2;
    const [y1, y2] = [s.y + s.h, t.y];
    // Down to an outside service: the verb sits just above it (mock « envoie »); otherwise mid-way.
    const labelY = outside.has(link.target) ? y2 - 10 : (y1 + y2) / 2 + 4;
    const label = (dx: number, text: string): Label => ({ x: x + dx + 10, y: labelY, anchor: "start", text });
    if (!link.back) return [drawn(`M${x},${y1} L${x},${y2}`, label(0, link.verb))];
    return [
      drawn(`M${x - 14},${y1} L${x - 14},${y2}`, { ...label(-14, link.verb), x: x - 24, anchor: "end" }),
      drawn(`M${x + 14},${y2} L${x + 14},${y1}`, label(14, link.back), true),
    ];
  }
  // Anywhere else: right, then down or up, then right again, on right angles.
  const [sy, ty] = [s.y + s.h / 2, t.y + t.h / 2];
  const forward = t.x > s.x;
  const x1 = forward ? s.x + s.w : s.x;
  const x2 = forward ? t.x : t.x + t.w;
  const mid = (x1 + x2) / 2;
  return [drawn(`M${x1},${sy} L${mid},${sy} L${mid},${ty} L${x2},${ty}`, { x: mid + 8, y: (sy + ty) / 2 + 4, anchor: "start", text: link.verb })];
}

/** « 2026-04-16 » → « 16/04/2026 ». */
export function frenchDate(day: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(day);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : day;
}

/** « backend/app/utils.py:7 », « .github/workflows/ » files without lines. */
export function where(proof: { file: string; start: number; end: number }): string {
  if (proof.start <= 0) return proof.file;
  return proof.end > proof.start ? `${proof.file}:${proof.start}-${proof.end}` : `${proof.file}:${proof.start}`;
}
