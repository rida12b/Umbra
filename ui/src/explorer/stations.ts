import type { Journey, ProjectModel } from "../api";
import { stepRuns } from "./room.ts";

// A journey played on the floor (#77): each step is a station, the machine (component) where it happens,
// not the parts it reaches. The camera follows the station's room; the parts reached are a faint ring.
// A step that stays on the same station says why, so no « Suivante » is a silent no-move. Pure, tested
// on the real models (stations.test.ts).

export type Move = "start" | "machine" | "room" | "same" | "back";

export interface Station {
  n: number; // 1-based step number
  machine: string | null; // the component the step happens on
  room: string | null; // its part: the room the camera opens; null for a step done by hand outside the code
  person: string | null; // a step done by hand without a machine: the person who does it, if the model says
  manual: boolean;
  touches: string[]; // the other parts the step reaches: a faint ring, never the station
  move: Move; // compared with the step before
  note: string | null; // the move in words, under the step's sentence; always set when the station stays
}

/** Two steps on the same station have the same key. */
export const stationKey = (s: Station) => s.machine ?? (s.room ? `room:${s.room}` : s.person ? `person:${s.person}` : "hand");

export function journeyStations(model: ProjectModel, journey: Journey): Station[] {
  const components = new Map(model.composants.map((c) => [c.id, c]));
  const blocks = new Map(model.blocs.map((b) => [b.id, b]));
  const people = new Set(model.blocs.filter((b) => b.type === "user" || b.type === "device").map((b) => b.id));
  const nameOf = (s: Station) =>
    (s.machine && components.get(s.machine)?.nom) || (s.room && blocks.get(s.room)?.nom) || (s.person && blocks.get(s.person)?.nom) || "la personne";
  const stations: Station[] = [];
  journey.etapes.forEach((step, i) => {
    const component = step.composant ? components.get(step.composant) : undefined;
    // Before v1.7 a step may name a part instead of a component: the part is the station.
    const room = component?.bloc ?? (step.composant && blocks.has(step.composant) ? step.composant : null);
    const person = component || room ? null : (step.touche.find((id) => people.has(id)) ?? null);
    const station: Station = {
      n: i + 1,
      machine: component?.id ?? null,
      room,
      person,
      manual: !!step.manuel || (!component && !room),
      touches: step.touche.filter((id) => id !== room && id !== person && blocks.has(id)),
      move: "start",
      note: null,
    };
    const before = stations.at(-1);
    const key = stationKey(station);
    const seen = [...stations].reverse().find((s) => stationKey(s) === key);
    if (!before) station.move = "start";
    else if (stationKey(before) === key) station.move = "same";
    else if (seen && station.machine) station.move = "back";
    else station.move = before.room === station.room ? "machine" : "room";

    const name = nameOf(station);
    if (!station.machine && !station.room)
      station.note = station.person ? `Étape faite à la main par « ${name} », hors du code.` : "Étape faite à la main par une personne, hors du code.";
    else if (station.move === "same") station.note = `Même machine qu'à l'étape ${before!.n} : « ${name} » continue son travail.`;
    else if (station.move === "back")
      station.note =
        before!.room && before!.room !== room
          ? `Revient de « ${blocks.get(before!.room)?.nom ?? before!.room} » à « ${name} », la machine de l'étape ${seen!.n}.`
          : `Retour à « ${name} », la machine de l'étape ${seen!.n}.`;
    else if (station.move === "room" && room) station.note = `Passage dans « ${blocks.get(room)?.nom ?? room} ».`;
    stations.push(station);
  });
  return stations;
}

export interface StepGroup {
  title: string;
  from: number; // 1-based, inclusive
  to: number;
}

const LONG_JOURNEY = 9; // past this many steps, a journey without phases is grouped by room

/** The model's phases (v1.7), with any step they leave out grouped by room; else rooms past 9 steps; else none. */
export function stepGroups(model: ProjectModel, journey: Journey): StepGroup[] | null {
  const last = journey.etapes.length;
  const runs = stepRuns(model, journey).map((r) => ({
    title: r.title.startsWith("Retour") || r.title === "Fait à la main" ? r.title : `Dans « ${r.title} »`,
    from: r.from,
    to: r.to,
  }));
  const phases = (journey.phases ?? [])
    .filter((p) => p.nom && p.de >= 1 && p.a >= p.de && p.de <= last)
    .map((p) => ({ title: p.nom, from: p.de, to: Math.min(p.a, last) }))
    .sort((a, b) => a.from - b.from);
  if (phases.length === 0) return last > LONG_JOURNEY ? runs : null;
  const groups: StepGroup[] = [];
  // The room runs that cover the steps from..to, cut to fit.
  const fill = (from: number, to: number) => {
    for (const r of runs) if (r.to >= from && r.from <= to) groups.push({ title: r.title, from: Math.max(r.from, from), to: Math.min(r.to, to) });
  };
  let next = 1;
  for (const phase of phases) {
    if (phase.to < next) continue; // overlaps the phase before: the earlier one keeps its steps
    if (phase.from > next) fill(next, phase.from - 1);
    groups.push({ ...phase, from: Math.max(phase.from, next) });
    next = phase.to + 1;
  }
  if (next <= last) fill(next, last);
  return groups;
}

/** The group a step is in, for the player bar: « Dans « Serveur » · étapes 3–7 ». */
export function groupOf(groups: StepGroup[] | null, n: number): StepGroup | null {
  return groups?.find((g) => n >= g.from && n <= g.to) ?? null;
}
