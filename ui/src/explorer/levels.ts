import type { ArchBlock, BlockType, ProjectModel } from "../api";
import { buildFloor, type Floor } from "./floor";

// What the explorer shows at each zoom level, built from the Project model only (no API call):
// the factory floor (parts) → the components of one part → the files of one component.
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
    inside: components || block.code.length,
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
    const components = model.composants.filter((c) => c.bloc === block.id);
    const own = new Set(components.map((c) => c.id));
    const boxes: Box[] = components.map((c) => ({
      id: c.id,
      kind: "Composant",
      title: c.nom,
      words: c.en_bref || c.role,
      faded: false,
      target: { kind: "component", id: c.id },
      inside: c.fichiers.length,
    }));
    if (boxes.length === 0)
      for (const code of block.code)
        boxes.push({
          id: `file:${code.chemin}`,
          kind: code.element.startsWith("dir:") || code.element === "app:" ? "Dossier" : "Fichier",
          title: code.chemin.split("/").pop() || block.nom, // « app: » is the whole project folder
          words: model.modules[code.chemin] ?? model.dossiers[code.chemin] ?? code.chemin,
          faded: false,
          target: { kind: "file", path: code.element },
          inside: 1,
        });
    const links = new Map<string, Link>();
    const neighbour = (id: string) => {
      const other = model.blocs.find((b) => b.id === id);
      if (!other || other.id === block.id) return null;
      const shown = boxes.find((b) => b.target.kind === "block" && b.target.id === other.id);
      if (shown) return shown.id;
      const box = blockBox(model, other, true);
      if (own.has(box.id)) box.id = `@bloc:${box.id}`; // a component may share a neighbour's id
      boxes.push(box);
      return box.id;
    };
    const add = (from: string | null, to: string | null, verb: string, full: string) => {
      if (!from || !to || from === to) return;
      const id = `${from}>${to}`;
      if (!links.has(id)) links.set(id, { id, from, to, verb, full });
    };
    for (const c of components)
      for (const used of c.utilise) add(c.id, own.has(used) ? used : neighbour(used), "utilise", `${c.nom} utilise ${used}`);
    // The journeys say which component reaches which outside part, and in what words.
    for (const journey of model.parcours)
      for (const step of journey.etapes)
        if (own.has(step.composant))
          for (const reached of step.touche) {
            const other = neighbour(reached);
            // A step done by hand is done by the part it reaches (a person): the arrow starts there.
            if (step.manuel) add(other, step.composant, step.action || "", step.simple || step.texte);
            else add(step.composant, other, step.action || "", step.simple || step.texte);
          }
    return {
      key,
      title: block.nom,
      hint: `Ce qu'il y a dans « ${block.nom} »${boxes.some((b) => b.faded) ? ", et les pièces voisines (estompées)" : ""}.`,
      boxes,
      links: [...links.values()],
      floor: null,
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
