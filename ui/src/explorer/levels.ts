import type { ArchBlock, BlockType, ProjectModel } from "../api";
import { buildFloor, type Floor } from "./floor";
import { buildRoom, type Room } from "./room";

// What the explorer shows at each zoom level, built from the Project model only (no API call):
// the factory floor (parts) → one part opened in place (its machines) → the files of one machine.
// The level below files is the code itself, read from the index (see CodeLevel).

export const KIND: Record<BlockType, string> = {
  user: "Personne",
  frontend: "Interface",
  backend: "Serveur",
  worker: "Tâche de fond",
  database: "Base de données",
  storage: "Stockage",
  queue: "File d'attente",
  external: "Service externe",
  ml_model: "Modèle d'IA",
  device: "Appareil",
  cli: "Commande",
  library: "Bibliothèque",
  docs: "Documentation",
  tests: "Tests",
  infra: "Infrastructure",
};

export const PROJECT_SETTINGS = "reglages-projet"; // `select` of the floor's « Réglages du projet » card: its plate (#79)

export type LevelKey = "parts" | `part:${string}` | `component:${string}`;

/** What a box stands for: entering it shows the next level down (or the code). */
export type Target =
  | { kind: "block"; id: string }
  | { kind: "component"; id: string }
  | { kind: "file"; path: string };

export interface Box {
  id: string;
  kind: string; // « Serveur », « Composant », « Fichier »
  title: string;
  words: string; // a few plain words under the title
  faded: boolean; // legacy, or outside the part being looked at
  target: Target;
  inside: number; // how many things « Entrer » shows (0: nothing below)
}

export interface Link {
  id: string;
  from: string;
  to: string;
  verb: string; // short, on the arrow
  full: string; // the whole description, in the panel
}

export interface Level {
  key: LevelKey;
  title: string;
  hint: string; // one sentence: what this level shows
  boxes: Box[];
  links: Link[];
  floor: Floor | null; // the top level is drawn as a factory floor (ADR-0006)
  room?: Room | null; // a part opened in place (#76); null: a part without machines
}

function blockBox(model: ProjectModel, block: ArchBlock, faded = false): Box {
  const components = model.composants.filter((c) => c.bloc === block.id).length;
  return {
    id: block.id,
    kind: KIND[block.type],
    title: block.nom,
    words: block.en_bref || block.role,
    faded: faded || block.importance === "ancien",
    target: { kind: "block", id: block.id },
    inside: components, // only a part with machines can be entered (a person opens its explanation)
  };
}

export function buildLevel(model: ProjectModel, key: LevelKey, projectName: string): Level | null {
  if (key === "parts") {
    const floor = buildFloor(model);
    const shown = new Set(floor.items.map((i) => i.id));
    return {
      key,
      title: "L'usine",
      hint: `${projectName} vu comme une usine : la donnée entre à gauche, passe par les pièces qui travaillent, et ressort à droite.`,
      boxes: model.blocs.filter((b) => shown.has(b.id)).map((b) => blockBox(model, b, floor.strip.includes(b.id))),
      links: floor.links.map(({ id, from, to, verb, full }) => ({ id, from, to, verb, full })),
      floor,
    };
  }

  if (key.startsWith("part:")) {
    const block = model.blocs.find((b) => b.id === key.slice(5));
    if (!block) return null;
    const room = buildRoom(model, block.id); // null: a part without machines (a person, a store, a service)
    const component = (id: string): Box => {
      const c = model.composants.find((x) => x.id === id)!;
      return { id, kind: "Composant", title: c.nom, words: c.en_bref || c.role, faded: false, target: { kind: "component", id }, inside: c.fichiers.length };
    };
    const around = room ? [...room.doors.map((d) => d.bloc), ...room.belt.flatMap((m) => m.hung.map((h) => h.bloc))] : [];
    const boxes: Box[] = room
      ? [
          ...[...room.belt.map((m) => m.id), ...room.band].map(component),
          ...[...new Set(around)].flatMap((id) => {
            const other = model.blocs.find((b) => b.id === id);
            return other ? [blockBox(model, other, true)] : [];
          }),
        ]
      : [];
    return {
      key,
      title: block.nom,
      hint: room
        ? `Ce qui se passe dans « ${block.nom} », machine par machine, dans l'ordre où la donnée les traverse.`
        : `« ${block.nom} » n'a pas de machine à montrer : c'est ${block.type === "user" ? "une personne" : "une pièce sans code étudié"}.`,
      boxes,
      links: [],
      floor: null,
      room,
    };
  }

  if (key.startsWith("component:")) {
    const component = model.composants.find((c) => c.id === key.slice(10));
    if (!component) return null;
    return {
      key,
      title: component.nom,
      hint: `Les fichiers de « ${component.nom} ». Entrez dans un fichier pour voir ses fonctions.`,
      boxes: component.fichiers.map((path) => ({
        id: `file:${path}`,
        kind: "Fichier",
        title: path.split("/").pop() || path,
        words: model.modules[path] ?? path,
        faded: false,
        target: { kind: "file", path },
        inside: 1,
      })),
      links: [],
      floor: null,
    };
  }
  return null;
}

/** The levels above a level, for the breadcrumb: « L'usine › Serveur › Composant ». */
export function trail(model: ProjectModel, key: LevelKey): { key: LevelKey; title: string }[] {
  const top: { key: LevelKey; title: string }[] = [{ key: "parts", title: "L'usine" }];
  if (key === "parts") return top;
  if (key.startsWith("part:")) {
    const block = model.blocs.find((b) => b.id === key.slice(5));
    return [...top, { key, title: block?.nom ?? "Pièce" }];
  }
  const component = model.composants.find((c) => c.id === key.slice(10));
  const block = model.blocs.find((b) => b.id === component?.bloc);
  return [
    ...top,
    ...(block ? [{ key: `part:${block.id}` as LevelKey, title: block.nom }] : []),
    { key, title: component?.nom ?? "Composant" },
  ];
}

/** The level a box opens. */
export function levelOf(target: Target): LevelKey | null {
  if (target.kind === "block") return `part:${target.id}`;
  if (target.kind === "component") return `component:${target.id}`;
  return null; // a file opens the code itself
}
