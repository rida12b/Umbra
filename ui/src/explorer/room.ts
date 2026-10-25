import type { Branch, Journey, JourneyStep, ProjectModel } from "../api";
import { buildFloor, mainJourney } from "./floor.ts";

// A part opened in place (#76, ADR-0006): its machines (components) on a belt in the order the data
// visits them, the doors to the parts the data comes from and goes to, what each machine searches or
// calls hung under it, and the refusals under the one machine whose files hold them. Pure, tested on
// the real models (room.test.ts).

export interface Crossing {
  step: number; // 1-based, in the driving journey
  dir: "in" | "out";
  machine: string; // the machine the step happens on (here, or in the neighbour)
}
export interface Door {
  bloc: string;
  side: "left" | "right"; // left: where data comes from; right: where it goes
  verb: string;
  crossings: Crossing[];
}
export interface Chute {
  quand: string;
  alors: string;
  technical: boolean; // the model's own words, written for a developer
  fichier: string | null;
}
export interface Machine {
  id: string;
  nom: string;
  words: string;
  steps: number[];
  hung: { bloc: string; steps: number[] }[];
  chutes: Chute[];
}
export interface Room {
  bloc: string;
  journey: Journey | null;
  belt: Machine[];
  band: string[]; // start-up wiring: not on the belt
  doors: Door[];
  unplaced: (Branch & { journey: string })[]; // the driving journey's refusals no single machine holds
  elsewhere: (Branch & { journey: string })[]; // refusals of the other journeys that pass here
}

const WIRING_FILES = /(^|\/)(main|app)\.py$/;

const ownerOf = (model: ProjectModel) => {
  const blocs = new Set(model.blocs.map((b) => b.id));
  const bloc = new Map(model.composants.map((c) => [c.id, c.bloc]));
  return (step: JourneyStep): string | null => {
    if (!step.composant) return null;
    const owner = bloc.get(step.composant) ?? step.composant;
    return blocs.has(owner) ? owner : null;
  };
};

export const enterable = (model: ProjectModel) => new Set(model.composants.map((c) => c.bloc));

/** The main journey when it passes here, else the journey with the most steps here (model order on ties). */
export function drivingJourney(model: ProjectModel, bloc: string): Journey | null {
  const owner = ownerOf(model);
  const here = (j: Journey) => j.etapes.filter((s) => owner(s) === bloc).length;
  const main = mainJourney(model).journey;
  if (main && here(main) > 0) return main;
  return model.parcours.reduce<Journey | null>((best, j) => (here(j) > (best ? here(best) : 0) ? j : best), null);
}

export function buildRoom(model: ProjectModel, bloc: string): Room | null {
  const components = model.composants.filter((c) => c.bloc === bloc);
  if (components.length === 0) return null;
  const owner = ownerOf(model);
  const journey = drivingJourney(model, bloc);
  const steps = journey?.etapes ?? [];
  const stepsOf = (id: string, j: Journey) => j.etapes.flatMap((s, i) => (s.composant === id ? [i + 1] : []));
  const anyStep = (id: string) => model.parcours.some((j) => stepsOf(id, j).length > 0);
  const wiring = components.filter(
    (c) => (!journey || stepsOf(c.id, journey).length === 0) && (!anyStep(c.id) || (c.fichiers.length > 0 && c.fichiers.every((f) => WIRING_FILES.test(f)))),
  );
  const firstSeen = (id: string) => {
    const driving = journey ? stepsOf(id, journey)[0] : undefined;
    if (driving !== undefined) return driving;
    const other = model.parcours.findIndex((j) => stepsOf(id, j).length > 0);
    return other < 0 ? Number.MAX_SAFE_INTEGER : 10_000 * (other + 1) + stepsOf(id, model.parcours[other]!)[0]!;
  };
  const onBelt = components.filter((c) => !wiring.includes(c)).sort((a, b) => firstSeen(a.id) - firstSeen(b.id));

  const doors = roomDoors(model, bloc, steps, owner);
  const doorBlocs = new Set(doors.map((d) => d.bloc));
  const floor = buildFloor(model);
  const aside = new Set(floor.strip);
  const { placed, unplaced } = placeChutes(model, journey);

  const belt: Machine[] = onBelt.map((c) => {
    const mine = journey ? stepsOf(c.id, journey) : [];
    const hung = new Map<string, number[]>();
    for (const n of mine)
      for (const id of steps[n - 1]!.touche)
        if (id !== bloc && !doorBlocs.has(id) && !aside.has(id)) hung.set(id, [...(hung.get(id) ?? []), n]);
    return {
      id: c.id,
      nom: c.nom,
      words: c.en_bref || c.role,
      steps: mine,
      hung: [...hung].map(([id, at]) => ({ bloc: id, steps: at })),
      chutes: (placed.get(c.id) ?? []).map((b) => ({
        quand: b.quand_simple || b.quand,
        alors: b.alors_simple || b.alors,
        technical: !b.quand_simple,
        fichier: b.fichier,
      })),
    };
  });
  const elsewhere = model.parcours
    .filter((j) => j !== journey && j.etapes.some((s) => owner(s) === bloc))
    .flatMap((j) => (j.branches ?? []).map((b) => ({ ...b, journey: j.id })));
  return { bloc, journey, belt, band: wiring.map((c) => c.id), doors, unplaced, elsewhere };
}

/** Each branch of the driving journey under the single component whose files hold it; never guessed. */
function placeChutes(model: ProjectModel, journey: Journey | null) {
  const placed = new Map<string, Branch[]>();
  const unplaced: (Branch & { journey: string })[] = [];
  for (const branch of journey?.branches ?? []) {
    const holders = model.composants.filter((c) => branch.fichier && (c.fichiers.includes(branch.fichier) || c.expose.some((e) => e.fichier === branch.fichier)));
    if (holders.length === 1) placed.set(holders[0]!.id, [...(placed.get(holders[0]!.id) ?? []), branch]);
    else unplaced.push({ ...branch, journey: journey!.id });
  }
  return { placed, unplaced };
}

/**
 * The doors of a room, one per neighbour: the parts the driving journey crosses into or out of, and the
 * parts that send data in. Each lists the steps that cross it. Start-up and checks (control flows) and
 * things that never run are not doors; what a machine only searches hangs under it instead.
 */
function roomDoors(model: ProjectModel, bloc: string, steps: JourneyStep[], owner: (s: JourneyStep) => string | null): Door[] {
  const floor = buildFloor(model);
  const aside = new Set(floor.strip);
  const links = floor.links.filter((l) => l.style !== "control" && !aside.has(l.from) && !aside.has(l.to));
  const machine = (s: JourneyStep) => model.composants.find((c) => c.id === s.composant)?.nom ?? "";
  const doors = new Map<string, Door>();
  const door = (id: string, side: Door["side"]) => {
    if (!doors.has(id)) {
      const flow = links.find((l) => side === "left" ? l.from === id && l.to === bloc : l.from === bloc && l.to === id) ?? links.find((l) => (l.from === id && l.to === bloc) || (l.from === bloc && l.to === id));
      doors.set(id, { bloc: id, side, verb: flow?.verb ?? "", crossings: [] });
    }
    return doors.get(id)!;
  };
  const feeds = (id: string) => links.some((l) => l.from === id && l.to === bloc && l.style !== "reply");
  // The journey moving from one part to the next: into this room, or out of it.
  steps.forEach((step, i) => {
    const before = i > 0 ? owner(steps[i - 1]!) : null;
    const here = owner(step);
    if (!before || !here || before === here) return;
    const side = (id: string) => (feeds(id) ? "left" : "right");
    if (here === bloc && !aside.has(before)) door(before, side(before)).crossings.push({ step: i + 1, dir: "in", machine: machine(step) });
    else if (before === bloc && !aside.has(here)) door(here, side(here)).crossings.push({ step: i + 1, dir: "out", machine: machine(step) });
  });
  // Parts that send data in but take no step (a person, an outside caller): their door, crossed when a step here touches them.
  for (const link of links) {
    if (link.to !== bloc || link.style === "reply" || doors.has(link.from)) continue;
    const touches = steps.flatMap((s, i) => (owner(s) === bloc && s.touche.includes(link.from) ? [i] : []));
    const d = door(link.from, "left");
    touches.forEach((i, k) => d.crossings.push({ step: i + 1, dir: k === 0 ? "in" : "out", machine: machine(steps[i]!) }));
  }
  // Parts it sends data to that no step only touches (those hang under the machine): doors on the right.
  const touched = new Set(steps.flatMap((s) => (owner(s) === bloc ? s.touche : [])));
  for (const link of links)
    if (link.from === bloc && link.style !== "reply" && !doors.has(link.to) && !touched.has(link.to)) door(link.to, "right");
  const first = (d: Door) => d.crossings[0]?.step ?? Number.MAX_SAFE_INTEGER;
  const order = (d: Door) => model.blocs.findIndex((b) => b.id === d.bloc);
  return [...doors.values()].sort((a, b) => (a.side === b.side ? first(a) - first(b) || order(a) - order(b) : a.side === "left" ? -1 : 1));
}

/** A journey's steps cut into runs in the same part; the last run is « Retour à l'expéditeur » when it
 * comes back to a part seen before and a step there answers the part the journey started from. */
export function stepRuns(model: ProjectModel, journey: Journey): { title: string; bloc: string; from: number; to: number }[] {
  const owner = ownerOf(model);
  const people = new Set(model.blocs.filter((b) => b.type === "user" || b.type === "device").map((b) => b.id));
  const entry = journey.entree ?? journey.etapes.flatMap((s) => s.touche).find((id) => people.has(id)) ?? null;
  const runs: { title: string; bloc: string; from: number; to: number }[] = [];
  journey.etapes.forEach((step, i) => {
    const bloc = owner(step) ?? runs.at(-1)?.bloc ?? "";
    const last = runs.at(-1);
    if (last && last.bloc === bloc) last.to = i + 1;
    else runs.push({ title: model.blocs.find((b) => b.id === bloc)?.nom ?? bloc, bloc, from: i + 1, to: i + 1 });
  });
  const last = runs.at(-1);
  if (last && runs.slice(0, -1).some((r) => r.bloc === last.bloc) && entry) {
    const answers = journey.etapes.slice(last.from - 1, last.to).some((s) => !s.manuel && s.touche.includes(entry));
    if (answers) last.title = "Retour à l'expéditeur";
  }
  return runs;
}
