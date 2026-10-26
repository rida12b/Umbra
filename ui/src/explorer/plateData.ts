import type { Cited, ProjectModel, Setting } from "../api";
import { stepLabel } from "../arch/story.ts";

// The plate of a machine, of a room, of the project (#79): fixed slots in a fixed order, so a reader always finds
// « what it does, takes in, gives back, which settings, where in the code, in which journeys » at the same place.
// Filled from the model only: a slot the study has no data for is null, and the page says so. Pure, tested on the
// real models (plateData.test.ts).

export interface Item {
  text: string;
  refusal: boolean; // in Rend only: what comes back when it says no (« ou un refus… », « un échec si… »), red on the plate
}
export interface Seen {
  journey: string;
  nom: string; // the journey's name
  step: number; // 1-based
  action: string;
  where: string; // the machine the step happens on; "" when the step only reaches this part (a room plate)
}
export interface MachinePlate {
  title: string;
  room: string; // the part it is in
  fait: string;
  detail: string; // the model's longer description
  recoit: Item[] | null; // null: not in the model (studied before v1.7)
  rend: Item[] | null;
  reglages: Setting[] | null;
  ou: (Cited & { quoi: string })[];
  fichiers: string[];
  vuDans: Seen[];
  mots: { simple: string; code: string }[];
}
export interface RoomPlate {
  title: string;
  fait: string;
  detail: string;
  recoit: Item[] | null;
  rend: Item[] | null;
  machines: { id: string; nom: string; words: string }[];
  vuDans: Seen[];
}
export interface ProjectSettingRow extends Cited {
  nom: string;
  code: string;
  valeur: string;
  notRead: boolean; // the study found no code that reads it (« lu par le code : non »)
}

// The study writes a refusal as an alternative outcome of what a machine gives back: « ou un refus si … »,
// « un échec si … », « une erreur 401 ». Only Rend is read that way: an input about errors (Sentry) is not a refusal.
const REFUSAL = /^(ou|sinon)\s|(^|[\s'’(])(refus|échec|erreur|arrêt|rejet)|\b[45]\d\d\b/iu; // « é » is not a \b word letter without /u
const items = (list: string[] | undefined, outcomes = false): Item[] | null =>
  list?.length ? list.map((text) => ({ text, refusal: outcomes && REFUSAL.test(text) })) : null;

/** Every step done on these machines, or (a room) that reaches the part, in model order:
 * « Recevoir… · étape 2 — Vérifie le nom du client ». */
function seenIn(model: ProjectModel, machines: Set<string>, part: string | null = null): Seen[] {
  const names = new Map(model.composants.map((c) => [c.id, c.nom]));
  return model.parcours.flatMap((j) =>
    j.etapes.flatMap((s, i) => {
      const on = !!s.composant && machines.has(s.composant);
      if (!on && !(part && s.touche.includes(part))) return [];
      return [{ journey: j.id, nom: j.nom, step: i + 1, action: stepLabel(s), where: on ? (names.get(s.composant!) ?? "") : "" }];
    }),
  );
}

export function machinePlate(model: ProjectModel, id: string): MachinePlate | null {
  const c = model.composants.find((x) => x.id === id);
  if (!c) return null;
  return {
    title: c.nom,
    room: model.blocs.find((b) => b.id === c.bloc)?.nom ?? c.bloc,
    fait: c.en_bref || c.role,
    detail: c.en_bref && c.role !== c.en_bref ? c.role : "",
    recoit: items(c.entre),
    rend: items(c.sort, true),
    reglages: c.reglages?.length ? c.reglages : null,
    ou: c.expose,
    // Every file the plate cites, not only the machine's own: a setting may live in the project's config file.
    fichiers: [...new Set([...c.fichiers, ...(c.reglages ?? []).flatMap((r) => (r.fichier ? [r.fichier] : [])), ...c.expose.flatMap((e) => (e.fichier ? [e.fichier] : []))])],
    vuDans: seenIn(model, new Set([c.id])),
    mots: c.termes ?? [],
  };
}

export function roomPlate(model: ProjectModel, bloc: string): RoomPlate | null {
  const b = model.blocs.find((x) => x.id === bloc);
  if (!b) return null;
  const machines = model.composants.filter((c) => c.bloc === bloc);
  return {
    title: b.nom,
    fait: b.en_bref || b.role,
    detail: b.en_bref && b.role !== b.en_bref ? b.role : "",
    recoit: items(b.entre),
    rend: items(b.sort, true),
    machines: machines.map((m) => ({ id: m.id, nom: m.nom, words: m.en_bref || m.role })),
    vuDans: seenIn(model, new Set(machines.map((m) => m.id)), bloc),
  };
}

export function projectPlate(model: ProjectModel): ProjectSettingRow[] {
  return (model.reglages_projet ?? []).map((r) => ({ ...r, notRead: r.lu_par_le_code === "non" }));
}
