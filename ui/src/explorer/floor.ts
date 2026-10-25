import type { ArchBlock, BlockType, Journey, ProjectModel } from "../api";

// The factory floor (ADR-0006): the project read as a conveyor belt that carries the data from ▶ ENTRÉE
// to SORTIE ■ through the parts that do the work. What those parts call (a database they search, a
// language model) hangs above them; what joins from the side (a person who starts the service, a tool
// that fills the database) hangs below; what never runs (docs, lint tools) leaves the floor for the
// strip. Built from the model only: pure functions, tested on real models (floor.test.ts).

export type Shape = "person" | "room" | "store" | "outside" | "tool";
export type FloorRole = "entree" | "belt" | "supplier" | "side" | "orphan" | "strip";
export type LinkStyle = "data" | "reply" | "lookup" | "control";

export interface FloorItem {
  id: string;
  role: FloorRole;
  attach: string | null; // the floor item a supplier or side door hangs on
  shape: Shape;
}

export interface FloorLink {
  id: string; // `${from}>${to}`, the same ids as the level's links
  from: string;
  to: string;
  verb: string;
  full: string;
  style: LinkStyle;
}

export type Sortie = { kind: "store"; id: string } | { kind: "reply"; to: string };

export interface Floor {
  journey: Journey | null; // the journey the belt follows
  equivalents: number; // how many journeys tied for that place (1: no tie)
  entree: string | null;
  belt: string[]; // left to right after ENTRÉE; a store SORTIE is its last room
  sortie: Sortie | null;
  limit: string | null; // what the SORTIE cannot do (« Tout est perdu au redémarrage. »)
  items: FloorItem[]; // every bloc shown, in reading order
  links: FloorLink[]; // the arrows drawn (none touches the strip)
  stripLinks: FloorLink[]; // links to or from the strip: told in the panel, not drawn
  strip: string[];
  overflow: string[]; // folded into « +N » past MAX_ON_FLOOR
  skipped: number; // steps whose part the model does not know
  shapes: Shape[]; // the key: every shape drawn, nothing else
}

const MAX_ON_FLOOR = 16; // rooms plus the small tags hung on them: more and nobody reads the floor
const SHAPE: Record<BlockType, Shape> = {
  user: "person",
  device: "person",
  frontend: "room",
  backend: "room",
  worker: "room",
  cli: "room",
  database: "store",
  storage: "store",
  queue: "store",
  external: "outside",
  ml_model: "outside",
  docs: "tool",
  tests: "tool",
  infra: "tool",
  library: "tool",
};
// Verbs are the model's plain words (« cherche dans », « démarre »): their first word says the kind.
const READ = /^(cherche|lit|lis|lire|télécharge|telecharge|récupère|recupere|demande|consulte|interroge)/i;
const CONTROL = /^(démarre|demarre|lance|vérifie|verifie|configure|teste|déploie|deploie|surveille)/i;
const LIMIT = /perdu|au plus|seulement|pas encore|limite/i;

export const shapeOf = (block: ArchBlock): Shape => SHAPE[block.type] ?? "room";

/** The part a step happens in: its component's bloc, or a bloc named directly (older models). */
function stepBloc(model: ProjectModel, composant: string): string | null {
  const owner = model.composants.find((c) => c.id === composant)?.bloc ?? composant;
  return model.blocs.some((b) => b.id === owner) ? owner : null;
}

/** The journey the belt follows: through the most components, then the most steps, then model order. */
export function mainJourney(model: ProjectModel): { journey: Journey | null; equivalents: number } {
  const score = (j: Journey) => [new Set(j.etapes.map((s) => s.composant).filter((c) => stepBloc(model, c))).size, j.etapes.length] as const;
  let best: Journey | null = null;
  let equivalents = 0;
  for (const journey of model.parcours) {
    const [parts, steps] = score(journey);
    const [bestParts, bestSteps] = best ? score(best) : [-1, -1];
    if (parts > bestParts || (parts === bestParts && steps > bestSteps)) {
      best = journey;
      equivalents = 1;
    } else if (parts === bestParts && steps === bestSteps) equivalents++;
  }
  return { journey: best, equivalents };
}

export function buildFloor(model: ProjectModel): Floor {
  const blocks = new Map(model.blocs.map((b) => [b.id, b]));
  const isTool = (id: string) => blocks.has(id) && shapeOf(blocks.get(id)!) === "tool";
  const { journey, equivalents } = mainJourney(model);
  const steps = journey?.etapes ?? [];
  const skipped = steps.filter((s) => !stepBloc(model, s.composant)).length;

  // In step order: the parts that do the work, and every part a step reaches.
  const workers: string[] = [];
  const reached: { id: string; from: string }[] = [];
  for (const step of steps) {
    const here = stepBloc(model, step.composant);
    if (!here) continue;
    if (!workers.includes(here)) workers.push(here);
    for (const id of step.touche) if (blocks.has(id) && id !== here) reached.push({ id, from: here });
  }
  const inJourney = [...workers, ...reached.map((r) => r.id)];
  const entree =
    inJourney.find((id) => shapeOf(blocks.get(id)!) === "person") ??
    model.flux.find((f) => f.vers === workers[0] && blocks.has(f.de) && !isTool(f.de) && !workers.includes(f.de))?.de ??
    null;

  // SORTIE: the store the journey writes to last. A store it only searches is not where data ends up.
  const writes = (id: string) => model.flux.some((f) => f.vers === id && inJourney.includes(f.de) && !READ.test(f.verbe ?? ""));
  const stores = [...workers, ...reached.map((r) => r.id)].filter((id) => shapeOf(blocks.get(id)!) === "store" && writes(id));
  let lastStore: string | null = null;
  let lastAt = -1;
  steps.forEach((step, index) => {
    const ids = [stepBloc(model, step.composant), ...step.touche];
    for (const id of ids) if (id && stores.includes(id) && index >= lastAt) [lastStore, lastAt] = [id, index];
  });
  const belt = workers.filter((id) => id !== entree && id !== lastStore && !isTool(id));
  if (lastStore) belt.push(lastStore);
  const sortie: Sortie | null = lastStore ? { kind: "store", id: lastStore } : entree && belt.length ? { kind: "reply", to: entree } : null;
  const limit = lastStore ? (blocks.get(lastStore)!.role.split(/(?<=[.!?])\s+/).find((s) => LIMIT.test(s)) ?? null) : null;

  const items = new Map<string, FloorItem>();
  const put = (id: string, role: FloorRole, attach: string | null = null) => {
    if (!items.has(id)) items.set(id, { id, role, attach, shape: shapeOf(blocks.get(id)!) });
  };
  if (entree) put(entree, "entree");
  for (const id of belt) put(id, "belt");
  for (const { id, from } of reached) if (!isTool(id)) put(id, "supplier", items.has(from) ? from : (belt[0] ?? entree));

  // Side doors: linked by a flow to something already on the floor; twice, so one may hang on another.
  const rank: Record<FloorRole, number> = { belt: 0, entree: 0, supplier: 1, side: 2, orphan: 9, strip: 9 };
  for (let pass = 0; pass < 2; pass++)
    for (const block of model.blocs) {
      if (items.has(block.id) || isTool(block.id)) continue;
      const anchors = model.flux
        .flatMap((f) => (f.de === block.id ? [f.vers] : f.vers === block.id ? [f.de] : []))
        .filter((id) => items.has(id) && items.get(id)!.role !== "orphan");
      // A store it fills says more than a model it calls: stores first, then the belt, then the rest.
      anchors.sort((a, b) => Number(items.get(b)!.shape === "store") - Number(items.get(a)!.shape === "store") || rank[items.get(a)!.role] - rank[items.get(b)!.role]);
      if (anchors[0]) put(block.id, "side", anchors[0]);
    }

  const strip: string[] = [];
  for (const block of model.blocs) {
    if (items.has(block.id)) continue;
    if (isTool(block.id) || (block.importance ?? "coeur") !== "coeur") strip.push(block.id);
    else put(block.id, "orphan");
  }

  // Past MAX_ON_FLOOR, fold side doors (last first), then suppliers; ENTRÉE and the belt always stay.
  const overflow: string[] = [];
  const onFloor = () => [...items.values()].filter((i) => i.role !== "orphan").length;
  for (const role of ["side", "supplier"] as const)
    for (const item of [...items.values()].reverse())
      if (onFloor() > MAX_ON_FLOOR && item.role === role && ![...items.values()].some((i) => i.attach === item.id)) {
        items.delete(item.id);
        overflow.push(item.id);
      }

  const order = new Map<string, number>([...(entree ? [entree] : []), ...belt].map((id, i) => [id, i]));
  const position = (id: string): number => {
    const item = items.get(id);
    return order.get(id) ?? (item?.attach ? position(item.attach) : Number.MAX_SAFE_INTEGER);
  };
  const links: FloorLink[] = [];
  const stripLinks: FloorLink[] = [];
  const seen = new Set<string>();
  for (const flow of model.flux) {
    const id = `${flow.de}>${flow.vers}`;
    if (seen.has(id) || !blocks.has(flow.de) || !blocks.has(flow.vers) || flow.de === flow.vers) continue;
    seen.add(id);
    const verb = flow.verbe ?? "";
    const back = model.flux.some((f) => f.de === flow.vers && f.vers === flow.de) && position(flow.vers) < position(flow.de);
    const style: LinkStyle = back ? "reply" : READ.test(verb) ? "lookup" : CONTROL.test(verb) ? "control" : "data";
    const link = { id, from: flow.de, to: flow.vers, verb, full: flow.quoi, style };
    if (strip.includes(flow.de) || strip.includes(flow.vers)) stripLinks.push(link);
    else if (items.has(flow.de) && items.has(flow.vers)) links.push(link);
  }

  for (const id of strip) put(id, "strip");
  const all = [...items.values()];
  return {
    journey,
    equivalents,
    entree,
    belt,
    sortie,
    limit,
    items: all,
    links,
    stripLinks,
    strip,
    overflow,
    skipped,
    shapes: [...new Set(all.map((i) => i.shape))],
  };
}
