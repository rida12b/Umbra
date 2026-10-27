import type { InsideMap, InsidePart, SystemLink, SystemOutput } from "../../api";
import type { Label, Rect } from "../geometry";

// Pixel geometry of Level 1, the inside of a box (mocks p-serveur.png, p-web.png in
// docs/design/2026-10-27-project-map): stubs of the neighbours that come in on the left edge, the parts
// that carry the flow on the top row left → right, the other parts on the lower row, the neighbours it
// reaches as stubs on the right edge. Pure: the engine's stored cells in, the same drawing out.

export interface DrawnPart {
  part: InsidePart;
  rect: Rect;
  chips: { rect: Rect; file: string; label: string }[];
}

export interface DrawnInsideArrow {
  key: string;
  link: SystemLink;
  path: string;
  label: Label;
}

export interface DrawnInsideOutput {
  output: SystemOutput;
  path: string;
  at: [number, number];
}

export interface InsideGeometry {
  viewBox: string;
  parts: DrawnPart[];
  arrows: DrawnInsideArrow[];
  outputs: DrawnInsideOutput[];
  entry: { x: number; y: number } | null; // ENTRÉE above the first stub on the left
  sorties: { x: number; y: number } | null;
  around: { x: number; y: number; w: number } | null;
}

const MID = 195; // centre line of the top row
const LOWER_Y = 340;
const LOWER_H = 92;
const LOWER_GAP = 36;
const STUB_H = 90;
const ABOVE_Y = 40;
const ABOVE_H = 70;
const MIN_W = 1240;
const VIEW_H = 540;
const AROUND_Y = 495;
const CHIP_H = 28;
const CHIP_GAP = 8;
const CHIPS_PER_ROW = 3;

const textWidth = (text: string, perChar: number) => text.length * perChar;

/** « + 2 autour (réglages, migrations) »: the count and what it holds, named by their short words. */
export function insideAroundText(inside: InsideMap): string {
  const named = inside.around.map((a) => a.short).filter(Boolean).slice(0, 3);
  return `+ ${inside.around.length} autour${named.length ? ` (${named.join(", ")})` : ""}`;
}

export function chipLabel(file: string): string {
  return file.slice(file.lastIndexOf("/") + 1);
}

function chipRows(part: InsidePart): string[][] {
  // Shortest names first: the long one goes to the second row, which keeps the box narrow (mock: private.py).
  const labels = part.chips.map((c) => chipLabel(c.file)).sort((a, b) => a.length - b.length || a.localeCompare(b));
  const rows: string[][] = [];
  for (let i = 0; i < labels.length; i += CHIPS_PER_ROW) rows.push(labels.slice(i, i + CHIPS_PER_ROW));
  return rows;
}

const chipWidth = (label: string) => label.length * 7.5 + 14;
const rowWidth = (row: string[]) => row.reduce((sum, label) => sum + chipWidth(label), 0) + (row.length - 1) * CHIP_GAP;

function partSize(part: InsidePart, lower: boolean): { w: number; h: number } {
  const texts = Math.max(textWidth(part.title, 8.8), textWidth(part.detail, 6.6), ...part.folders.map((f) => textWidth(f, 7.6)));
  if (part.kind === "stub") return { w: Math.max(130, Math.round(texts + 40)), h: STUB_H };
  const rows = chipRows(part);
  if (rows.length) return { w: Math.max(texts + 40, ...rows.map((r) => rowWidth(r) + 32)), h: 70 + rows.length * 38 + 4 };
  if (lower) return { w: Math.max(160, Math.round(texts + 36)), h: LOWER_H };
  return { w: Math.max(140, Math.round(texts + 36)), h: part.detail ? 110 : 100 };
}

export function insideGeometry(inside: InsideMap): InsideGeometry {
  const parts = inside.parts.filter((p) => p.kind !== "stub");
  const top = parts.filter((p) => p.row === 0).sort((a, b) => a.col - b.col);
  const lower = parts.filter((p) => p.row !== 0).sort((a, b) => a.row - b.row || a.col - b.col);
  const ins = inside.parts.filter((p) => p.kind === "stub" && p.side === "in");
  const lastTop = top[top.length - 1]?.id;
  const outs = inside.parts
    .filter((p) => p.kind === "stub" && p.side === "out")
    .sort((a, b) => rankOut(inside, a, lastTop) - rankOut(inside, b, lastTop));
  const rects = new Map<string, Rect>();
  const gap = top.length > 3 ? 60 : 70;

  const inWidth = Math.max(0, ...ins.map((s) => partSize(s, false).w));
  ins.forEach((stub, i) => rects.set(stub.id, { x: 20, y: MID - STUB_H / 2 + i * 125, w: inWidth, h: STUB_H }));
  let x = ins.length ? 20 + inWidth + gap : 40;
  for (const part of top) {
    const { w, h } = partSize(part, false);
    rects.set(part.id, { x, y: MID - h / 2, w, h });
    x += w + gap;
  }
  const topRight = x - gap;

  // The lower row sits under what it is joined to, as one block, never under the left stubs.
  const sizes = lower.map((p) => partSize(p, true));
  const lowerWidth = sizes.reduce((sum, s) => sum + s.w, 0) + Math.max(0, lower.length - 1) * LOWER_GAP;
  const outW = Math.max(0, ...outs.map((s) => partSize(s, false).w), outs.some((s) => s.detail.startsWith("◉")) ? 200 : 150);
  const centres = lower.flatMap((p) => joinedCentres(inside, p.id, rects));
  const wanted = centres.length ? centres.reduce((a, b) => a + b, 0) / centres.length : topRight / 2;
  let lx = Math.max(ins.length ? 40 + inWidth : 40, wanted - lowerWidth / 2);
  // The first one hangs under the part that reaches it, so its arrow drops straight (mock: Contrôle d'accès).
  const firstFrom = lower[0] && inside.links.find((l) => l.target === lower[0]?.id && top.some((t) => t.id === l.source));
  const above = firstFrom && rects.get(firstFrom.source);
  if (above && sizes[0]) lx = Math.max(lx, above.x + 25 - sizes[0].w / 2);
  const outX = Math.max(topRight + gap, lx + lowerWidth + 40, MIN_W - 20 - outW);
  lower.forEach((part, i) => {
    const size = sizes[i] as { w: number; h: number };
    rects.set(part.id, { x: lx, y: LOWER_Y, w: size.w, h: size.h });
    lx += size.w + LOWER_GAP;
  });
  const slots = [{ y: MID - STUB_H / 2, h: STUB_H }, { y: ABOVE_Y, h: ABOVE_H }, { y: LOWER_Y + 10, h: STUB_H }];
  outs.forEach((stub, i) => {
    const slot = slots[Math.min(i, slots.length - 1)] as { y: number; h: number };
    rects.set(stub.id, { x: outX, y: slot.y + Math.max(0, i - 2) * 100, w: outW, h: slot.h });
  });
  const width = outX + outW + 20;

  const rowOf = new Map(inside.parts.map((p) => [p.id, p.kind === "stub" ? -1 : p.row]));
  const arrivals = new Map<string, number>();
  const arrows = inside.links.flatMap((link): DrawnInsideArrow[] => {
    const s = rects.get(link.source);
    const t = rects.get(link.target);
    if (!s || !t) return [];
    const from = rowOf.get(link.source) ?? 0;
    const seen = from === 1 ? (arrivals.get(link.target) ?? 0) : 0;
    if (from === 1) arrivals.set(link.target, seen + 1);
    const route = routeOf(s, t, from, rowOf.get(link.target) ?? 0, seen, [...rects.values()]);
    return [{ key: link.id, link, path: route.path, label: { ...route.label, text: link.verb } }];
  });

  const stubAbove = outs.length > 1;
  const outputs = inside.outputs.flatMap((output): DrawnInsideOutput[] => {
    const r = rects.get(output.box);
    if (!r) return [];
    const cx = r.x + r.w / 2;
    if (!stubAbove) return [{ output, path: `M${cx},${r.y} L${cx},70 L${outX + 20},70`, at: [outX + 28, 70] }];
    const y = r.y + r.h + 40;
    return [{ output, path: `M${cx},${r.y + r.h} L${cx},${y} L${outX + 20},${y}`, at: [outX + 28, y] }];
  });

  const drawn = inside.parts.map((part): DrawnPart => {
    const rect = rects.get(part.id) ?? { x: 0, y: 0, w: 0, h: 0 };
    const chips = chipRows(part).flatMap((row, r) => {
      let cx = rect.x + rect.w / 2 - rowWidth(row) / 2;
      return row.map((label) => {
        const chip = { rect: { x: cx, y: rect.y + 70 + r * 38, w: chipWidth(label), h: CHIP_H }, file: part.chips.find((c) => chipLabel(c.file) === label)?.file ?? label, label };
        cx += chipWidth(label) + CHIP_GAP;
        return chip;
      });
    });
    return { part, rect, chips };
  });
  const firstIn = ins[0] && rects.get(ins[0].id);
  const highest = Math.min(...outs.map((s) => rects.get(s.id)?.y ?? MID), outputs.length ? 70 - 10 : MID);
  return {
    viewBox: `0 0 ${Math.round(width)} ${VIEW_H}`,
    parts: drawn,
    arrows,
    outputs,
    entry: firstIn ? { x: 20, y: firstIn.y - 14 } : null,
    sorties: outs.some((s) => s.detail.startsWith("◉")) || outputs.length ? { x: outX, y: highest - 18 } : null,
    around: inside.around.length ? { x: 20, y: AROUND_Y, w: Math.max(240, insideAroundText(inside).length * 7.6 + 40) } : null,
  };
}

/** The stub on the top row is the one the last top part reaches; a mail service never takes it. */
function rankOut(inside: InsideMap, stub: InsidePart, lastTop: string | undefined): number {
  const fromLast = inside.links.some((l) => l.target === stub.id && l.source === lastTop);
  return (fromLast ? 0 : 2) + (stub.neighbour === "mail" ? 1 : 0);
}

function joinedCentres(inside: InsideMap, id: string, rects: Map<string, Rect>): number[] {
  const centre = (other: string) => {
    const r = rects.get(other);
    return r ? [r.x + r.w / 2] : [];
  };
  return inside.links.flatMap((l) => (l.target === id ? centre(l.source) : l.source === id ? centre(l.target) : []));
}

function crosses(x1: number, x2: number, y: number, boxes: Rect[], skip: Rect[]): boolean {
  const [a, b] = x1 < x2 ? [x1, x2] : [x2, x1];
  return boxes.some((r) => !skip.includes(r) && y > r.y && y < r.y + r.h && b > r.x && a < r.x + r.w);
}

/** Right angles only, in the mock's shapes; `seen` arrows already reach the same target (spread apart). */
function routeOf(s: Rect, t: Rect, from: number, to: number, seen: number, boxes: Rect[]): { path: string; label: Label } {
  const [scx, tcx] = [s.x + s.w / 2, t.x + t.w / 2];
  const sameLine = Math.abs(s.y + s.h / 2 - (t.y + t.h / 2)) < 1;
  if (sameLine) {
    const forward = t.x >= s.x + s.w;
    const [x1, x2] = forward ? [s.x + s.w, t.x] : [s.x, t.x + t.w];
    const y = s.y + s.h / 2;
    return { path: `M${x1},${y} L${x2},${y}`, label: { x: (x1 + x2) / 2, y: y - 10, anchor: "middle", text: "" } };
  }
  if (from === -1) {
    // A second stub on the left, lower than the top row: across, then up into the side of its part.
    const sy = s.y + s.h / 2;
    const mx = t.x - 14; // the verb fits on the first stretch, left of the turn
    const ty = t.y + t.h - 20;
    return { path: `M${s.x + s.w},${sy} L${mx},${sy} L${mx},${ty} L${t.x},${ty}`, label: { x: s.x + s.w + 4, y: sy - 8, anchor: "start", text: "" } };
  }
  const goesUp = t.y + t.h <= s.y;
  if (from !== 1 && to === 1) {
    // Down to the lower row: straight when it stands under, else along the side, then down.
    if (tcx > s.x + 10 && tcx < s.x + s.w - 10) {
      return { path: `M${tcx},${s.y + s.h} L${tcx},${t.y}`, label: { x: tcx + 10, y: (s.y + s.h + t.y) / 2 + 12, anchor: "start", text: "" } };
    }
    const right = tcx > scx;
    const sx = right ? s.x + s.w : s.x;
    const y = s.y + s.h - 20;
    if (!crosses(sx, tcx, y, boxes, [s, t])) {
      return { path: `M${sx},${y} L${tcx},${y} L${tcx},${t.y}`, label: { x: tcx + 10, y: (y + t.y) / 2 + 6, anchor: "start", text: "" } };
    }
    const ty = t.y + t.h / 2;
    const tx = right ? t.x : t.x + t.w;
    if (!crosses(scx, tx, ty, boxes, [s, t])) {
      return { path: `M${scx},${s.y + s.h} L${scx},${ty} L${tx},${ty}`, label: { x: scx + 10, y: (s.y + s.h + ty) / 2 + 4, anchor: "start", text: "" } };
    }
    // Neither way is free: down to the lane between the rows, across, then down into it.
    const lane = (s.y + s.h + t.y) / 2;
    const sx2 = Math.min(Math.max(tcx, s.x + 16), s.x + s.w - 16);
    return { path: `M${sx2},${s.y + s.h} L${sx2},${lane} L${tcx},${lane} L${tcx},${t.y}`, label: { x: tcx + 8, y: t.y - 8, anchor: "start", text: "" } };
  }
  if (from === 1 && goesUp) {
    // Up from the lower row: along to under the target, then up (mock « joint la preuve », « écrit (comptes) »).
    const right = tcx >= s.x + s.w;
    const sx = right ? s.x + s.w : s.x;
    const sy = s.y + s.h / 2;
    const ux = tcx + seen * 24;
    return { path: `M${sx},${sy} L${ux},${sy} L${ux},${t.y + t.h}`, label: { x: ux + 10, y: (sy + t.y + t.h) / 2 + 4, anchor: "start", text: "" } };
  }
  if (goesUp || t.y > s.y + s.h) {
    // A top part to a stub above or below it: out of its top (or bottom), then across.
    const ox = s.x + s.w * 0.67;
    const ty = t.y + t.h / 2;
    const sy = goesUp ? s.y : s.y + s.h;
    return { path: `M${ox},${sy} L${ox},${ty} L${t.x},${ty}`, label: { x: (ox + t.x) / 2, y: ty - 10, anchor: "middle", text: "" } };
  }
  // Anywhere else: across to half-way, up or down, across again.
  const [sy, ty] = [s.y + s.h / 2, t.y + t.h / 2];
  const forward = t.x > s.x;
  const [x1, x2] = forward ? [s.x + s.w, t.x] : [s.x, t.x + t.w];
  const mid = (x1 + x2) / 2;
  return { path: `M${x1},${sy} L${mid},${sy} L${mid},${ty} L${x2},${ty}`, label: { x: mid + 8, y: (sy + ty) / 2 + 4, anchor: "start", text: "" } };
}
