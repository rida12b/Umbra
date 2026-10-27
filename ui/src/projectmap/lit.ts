import type { Highlight, LitStep, SystemLink } from "../api.ts";
import type { Geometry, Rect } from "./geometry.ts";

// A path lit by Claude Code (`show`, #104; mock p-question.png): the lit boxes stay, the rest is dimmed, and
// under each lit box a callout lists its numbered steps (« 3 models.py — ajouter le champ »). Pure.

export interface CalloutRow {
  step: LitStep;
  y: number; // top of the row
}

export interface Callout {
  box: string;
  x: number;
  y: number;
  w: number;
  h: number;
  rows: CalloutRow[];
  connector: [number, number, number, number]; // from the box's bottom to the callout's top
  under: boolean; // under its box (mock); false: on its right
}

export const ROW_H = 32;
const PAD = 8;
const GAP_UNDER_BOX = 28; // mock: box bottom 260 → callout top 288
const GAP_BETWEEN = 16;
const MONO_CHAR = 8.7; // 14.5 px monospace
const SANS_CHAR = 6.9; // 14 px sans, French words
const MIN_W = 220;
const LEFT_EDGE = 16;
const CLEARANCE = 16; // mock: the Serveur callout ends 23 px above Courriel
const CHIP_H = 36; // the « + N outils autour » pill
const LABEL_H = 13; // an arrow label (13 px)

interface Lit {
  revision: number;
  connected: boolean;
  highlight: Highlight | null;
}

/** What one `data:` line of the live stream does to the page: a `show` lights, `cleared` dims nothing any
 * more, anything else is a change of the project (read again). */
export function applyEvent<T extends Lit>(live: T, data: string): T {
  let event: { type?: string; highlight?: Highlight } = {};
  try {
    event = JSON.parse(data) as typeof event;
  } catch {
    // not JSON: still a sign that something changed
  }
  if (event.type === "show" && event.highlight) return { ...live, connected: true, highlight: newer(live.highlight, event.highlight) };
  if (event.type === "cleared") return { ...live, connected: true, highlight: null };
  return { ...live, connected: true, revision: live.revision + 1 };
}

/** The later of two highlights: an answer that arrives late never covers a newer one. */
export function newer(shown: Highlight | null, coming: Highlight | null): Highlight | null {
  if (shown && coming && shown.serial > coming.serial) return shown;
  return coming;
}

/** One callout under each lit box that holds steps, side by side when they would overlap (mock); on the box's
 * right when another box stands right under it (a command above its library: sqlite-utils). */
export function callouts(drawn: Geometry, highlight: Highlight): Callout[] {
  const rects = new Map(drawn.boxes.map((b) => [b.box.id, b.rect]));
  const under: Callout[] = [];
  const beside: Callout[] = [];
  for (const id of highlight.boxes) {
    const rect = rects.get(id);
    const steps = highlight.steps.filter((s) => s.box === id);
    if (!rect || steps.length === 0) continue;
    const w = Math.max(MIN_W, ...steps.map(widthOf));
    const h = steps.length * ROW_H + 2 * PAD;
    const below = { x: rect.x + rect.w / 2 - w / 2, y: rect.y + rect.h + GAP_UNDER_BOX, w, h };
    const clearance = { ...below, h: below.h + CLEARANCE }; // a callout never touches the box under it
    const blocked = drawn.boxes.some((b) => b.box.id !== id && overlaps(clearance, b.rect));
    // Beside its box, the callout starts just under mid-height so the box's own line out (at mid-height) passes
    // above it.
    // A long one that would then reach another box stays centred on its box, as before.
    const low = { x: rect.x + rect.w + GAP_UNDER_BOX, y: rect.y + rect.h / 2 + PAD + 2, w, h };
    const lowFits = !drawn.boxes.some((b) => b.box.id !== id && overlaps({ ...low, h: low.h + CLEARANCE }, b.rect));
    const centred = { ...low, y: Math.max(rect.y, rect.y + rect.h / 2 - h / 2) };
    const at = blocked ? (lowFits ? low : centred) : below;
    const rows = steps.map((step, i) => ({ step, y: at.y + PAD + i * ROW_H }));
    (blocked ? beside : under).push({ box: id, ...at, rows, connector: [0, 0, 0, 0], under: !blocked });
  }
  under.sort((a, b) => a.x - b.x);
  for (let i = 1; i < under.length; i++) {
    const [left, right] = [under[i - 1] as Callout, under[i] as Callout];
    const overlap = left.x + left.w + GAP_BETWEEN - right.x;
    if (overlap > 0 && left.y < right.y + right.h && right.y < left.y + left.h) {
      left.x -= overlap / 2;
      right.x += overlap / 2;
    }
  }
  const chip = drawn.around ? { ...drawn.around, w: drawn.around.w + GAP_BETWEEN, h: CHIP_H } : null;
  for (const callout of under) {
    callout.x = Math.max(LEFT_EDGE, callout.x);
    if (chip && overlaps(callout, chip)) callout.x = chip.x + chip.w; // never on the « outils autour » pill
    const rect = rects.get(callout.box) as Rect;
    const cx = Math.min(Math.max(rect.x + rect.w / 2, callout.x + 20), callout.x + callout.w - 20);
    callout.connector = [cx, rect.y + rect.h, cx, callout.y];
  }
  for (const callout of beside) {
    const rect = rects.get(callout.box) as Rect;
    const cy = Math.min(Math.max(rect.y + rect.h / 2, callout.y + 16), callout.y + callout.h - 16);
    callout.connector = [rect.x + rect.w, cy, callout.x, cy];
  }
  return [...under, ...beside];
}

/** Where a dimmed line would show between a lit box and its callout: covered, so the only line there is the
 * blue connector (mock: « écran mis à jour » leaves from under the callout, not beside the connector). */
export function gapsUnder(placed: Callout[]): Rect[] {
  return placed.filter((c) => c.under).map((c) => ({ x: c.x, y: c.connector[1] + 2, w: c.w, h: c.y - c.connector[1] - 2 }));
}

/** An arrow label a callout would cover moves just under it (mock: « envoie » under the Serveur callout). */
export function labelY(x: number, y: number, placed: Callout[]): number {
  const over = placed.find((c) => x >= c.x - 4 && x <= c.x + c.w + 4 && y > c.y && y - LABEL_H < c.y + c.h);
  return over ? over.y + over.h + LABEL_H : y;
}

function overlaps(a: Rect, b: Rect): boolean {
  return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
}

function widthOf(step: LitStep): number {
  return Math.ceil(44 + step.label.length * MONO_CHAR + (step.note ? 18 + step.note.length * SANS_CHAR : 0) + 14);
}

/** « copier pour Claude »: the question (or the action) and the files, ready to paste for an agent (mock copyFiles). */
export function copyText(highlight: Highlight): string {
  const files = highlight.files.map((f) => `- ${f}`).join("\n");
  const title = highlight.kind === "path" ? `Chemin : ${highlight.caption}${highlight.detail ? ` (${highlight.detail})` : ""}` : `Tâche : ${highlight.caption}`;
  return `${title}\nFichiers (${highlight.files.length}) :\n${files}`;
}

export type LitState = "cur" | "on" | "pass";

/** A path drawn inside a box (#107, mock p-chemin.png): each numbered part with its badge, the parts it
 * goes through unnumbered, and the arrows between two steps in a row (through a passed part when they have
 * no arrow of their own). The current step is strong, the others half lit; with no current step (a
 * question from Claude Code) every step is strong. */
export interface InsideLit {
  parts: Map<string, LitState>;
  badges: Map<string, { n: number; cur: boolean }>;
  guesses: Set<string>; // parts whose step is only supposed: drawn dashed
  arrows: Map<string, LitState>; // by link id
  chips: Set<string>; // files whose chip lights
}

export function insideLit(highlight: Highlight, links: SystemLink[], step: number | null): InsideLit {
  const state = (n: number): LitState => (step === null || n === step ? "cur" : "on");
  const lit: InsideLit = { parts: new Map(), badges: new Map(), guesses: new Set(), arrows: new Map(), chips: new Set() };
  for (const passed of highlight.passed) lit.parts.set(passed, "pass");
  const between = (source: string, target: string) => links.filter((x) => x.source === source && x.target === target);
  highlight.steps.forEach((s, i) => {
    lit.parts.set(s.part, state(s.n));
    lit.badges.set(s.part, { n: s.n, cur: step === s.n });
    if (s.guess) lit.guesses.add(s.part);
    if (s.chip) lit.chips.add(s.chip);
    // The arrow in comes from the latest step before it that has one (Routes → Modèles after Contrôle
    // d'accès), else through a passed part (Application web → Porte d'entrée → Routes).
    const earlier = highlight.steps.slice(0, i).reverse();
    const direct = earlier.map((e) => between(e.part, s.part)).find((found) => found.length) ?? [];
    const before = highlight.steps[i - 1];
    const through =
      direct.length || !before ? [] : highlight.passed.flatMap((p) => (between(before.part, p).length && between(p, s.part).length ? [...between(before.part, p), ...between(p, s.part)] : []));
    for (const link of [...direct, ...through]) lit.arrows.set(link.id, state(s.n));
  });
  return lit;
}

/** ← and → along the numbered steps: from nothing chosen, → starts at 1 and ← at the last. */
export function nextStep(current: number | null, count: number, forward: boolean): number | null {
  if (!count) return null;
  if (current === null) return forward ? 1 : count;
  return Math.min(count, Math.max(1, current + (forward ? 1 : -1)));
}

/** The view box grown downwards when a callout would leave it; the same box otherwise (the map never moves). */
export function viewBoxWith(viewBox: string, placed: Callout[]): string {
  const [x, y, w, h] = viewBox.split(" ").map(Number) as [number, number, number, number];
  const bottom = Math.max(y + h, ...placed.map((c) => c.y + c.h + 12));
  const right = Math.max(x + w, ...placed.map((c) => c.x + c.w + 12));
  return `${x} ${y} ${right - x} ${bottom - y}`;
}
