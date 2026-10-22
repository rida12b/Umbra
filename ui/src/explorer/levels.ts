import type { ArchBlock, BlockType, ProjectModel } from "../api";

// What the explorer shows at each zoom level, built from the Project model only (no API call):
// context (who uses it, what it calls) → parts → the components of one part → the files of one component.
// The level below files is the code itself, read from the index (see CodeLevel).

export type Zone = "utilise" | "recoit" | "traite" | "range" | "exterieur";
export const ZONES: Zone[] = ["utilise", "recoit", "traite", "range", "exterieur"];
export const ZONE_TITLE: Record<Zone, string> = {
  utilise: "Qui l'utilise",
  recoit: "Ce qui reçoit",
  traite: "Ce qui traite",
  range: "Où c'est rangé",
  exterieur: "Services extérieurs",
};

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

const ZONE_OF_TYPE: Record<BlockType, Zone> = {
  user: "utilise",
  device: "utilise",
  frontend: "recoit",
  cli: "recoit",
  backend: "traite",
  worker: "traite",
  library: "traite",
  queue: "range",
  database: "range",
  storage: "range",
  external: "exterieur",
  ml_model: "exterieur",
  docs: "utilise",
  tests: "utilise",
  infra: "utilise",
};

export function zoneOf(block: ArchBlock): Zone {
  return block.zone || ZONE_OF_TYPE[block.type];
}

export type LevelKey = "context" | "parts" | "around" | `part:${string}` | `component:${string}`;

/** What a box stands for: entering it shows the next level down (or the code). */
export type Target =
  | { kind: "system" }
  | { kind: "block"; id: string }
  | { kind: "around" }
  | { kind: "component"; id: string }
  | { kind: "file"; path: string };

export interface Box {
  id: string;
  kind: string; // « Serveur », « Composant », « Fichier »
  title: string;
  words: string; // a few plain words under the title
  zone: Zone | null; // its column; null on levels without zones
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
  zoned: boolean;
}

const MAX_BOXES = 9; // more than this and nobody reads the map: the rest goes in a group

const isMain = (b: ArchBlock) => (b.importance ?? "coeur") === "coeur";
const isOutside = (b: ArchBlock) => zoneOf(b) === "utilise" || zoneOf(b) === "exterieur";

function blockBox(model: ProjectModel, block: ArchBlock, faded = false): Box {
  const components = model.composants.filter((c) => c.bloc === block.id).length;
  return {
    id: block.id,
    kind: KIND[block.type],
    title: block.nom,
    words: block.en_bref || block.role,
    zone: zoneOf(block),
    faded: faded || block.importance === "ancien",
    target: { kind: "block", id: block.id },
    inside: components || block.code.length,
  };
}

/** The model's flows, re-pointed to the boxes of a level, one arrow per pair of boxes. */
function linksBetween(model: ProjectModel, boxOf: (blockId: string) => string | null): Link[] {
  const links = new Map<string, Link>();
  for (const flow of model.flux) {
    const from = boxOf(flow.de);
    const to = boxOf(flow.vers);
    if (!from || !to || from === to) continue;
    const id = `${from}>${to}`;
    if (!links.has(id)) links.set(id, { id, from, to, verb: flow.verbe || "", full: flow.quoi });
  }
  return [...links.values()];
}

export function buildLevel(model: ProjectModel, key: LevelKey, projectName: string): Level | null {
  if (key === "context") {
    const outside = model.blocs.filter((b) => isMain(b) && isOutside(b));
    const system: Box = {
      id: "system",
      kind: "Le logiciel",
      title: projectName,
      words: model.pitch || model.resume,
      zone: "traite",
      faded: false,
      target: { kind: "system" },
      inside: model.blocs.length,
    };
    const shown = new Set(outside.map((b) => b.id));
    return {
      key,
      title: "Vue d'ensemble",
      hint: "Le logiciel, qui l'utilise et les services extérieurs qu'il appelle.",
      boxes: [system, ...outside.map((b) => blockBox(model, b))],
      links: linksBetween(model, (id) => (shown.has(id) ? id : model.blocs.some((b) => b.id === id && isMain(b)) ? "system" : null)),
      zoned: true,
    };
  }

  if (key === "parts" || key === "around") {
    // The most connected core parts are shown; past nine boxes, the rest joins the group.
    const degree = (b: ArchBlock) => model.flux.filter((f) => f.de === b.id || f.vers === b.id).length;
    const core = model.blocs.filter(isMain).sort((x, y) => degree(y) - degree(x));
    const rest = model.blocs.filter((b) => !isMain(b));
    const room = rest.length > 0 || core.length > MAX_BOXES ? MAX_BOXES - 1 : MAX_BOXES;
    const main = core.slice(0, room);
    const others = [...core.slice(room), ...rest];
    const shown = key === "around" ? others : main;
    const group: Box[] =
      key === "parts" && others.length > 0
        ? [
            {
              id: "around",
              kind: "Groupe",
              title: "Autour du projet",
              words: others.map((b) => b.nom).join(", "),
              zone: "utilise",
              faded: true,
              target: { kind: "around" },
              inside: others.length,
            },
          ]
        : [];
    const ids = new Set(shown.map((b) => b.id));
    return {
      key,
      title: key === "around" ? "Autour du projet" : "Les pièces",
      hint:
        key === "around"
          ? "Ce qui accompagne le projet sans en être le cœur : tests, documentation, ancien outil."
          : "Les pièces du projet, de qui l'utilise jusqu'aux services extérieurs.",
      boxes: [...group, ...shown.map((b) => blockBox(model, b))],
      links: linksBetween(model, (id) => (ids.has(id) ? id : key === "parts" && others.some((b) => b.id === id) ? "around" : null)),
      zoned: true,
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
      zone: null,
      faded: false,
      target: { kind: "component", id: c.id },
      inside: c.fichiers.length,
    }));
    if (boxes.length === 0)
      for (const code of block.code)
        boxes.push({
          id: `file:${code.chemin}`,
          kind: code.element.startsWith("dir:") ? "Dossier" : "Fichier",
          title: code.chemin.split("/").pop() || code.chemin,
          words: model.modules[code.chemin] ?? model.dossiers[code.chemin] ?? code.chemin,
          zone: null,
          faded: false,
          target: { kind: "file", path: code.element },
          inside: 1,
        });
    const links = new Map<string, Link>();
    const neighbour = (id: string) => {
      const other = model.blocs.find((b) => b.id === id);
      if (!other || other.id === block.id) return null;
      if (!boxes.some((b) => b.id === other.id)) boxes.push(blockBox(model, other, true));
      return other.id;
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
      zoned: false,
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
        zone: null,
        faded: false,
        target: { kind: "file", path },
        inside: 1,
      })),
      links: [],
      zoned: false,
    };
  }
  return null;
}

/** The levels above a level, for the breadcrumb: « Vue d'ensemble › Les pièces › Serveur ». */
export function trail(model: ProjectModel, key: LevelKey): { key: LevelKey; title: string }[] {
  const top: { key: LevelKey; title: string }[] = [
    { key: "context", title: "Vue d'ensemble" },
    { key: "parts", title: "Les pièces" },
  ];
  if (key === "context") return top.slice(0, 1);
  if (key === "parts") return top;
  if (key === "around") return [...top, { key, title: "Autour du projet" }];
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
  if (target.kind === "system") return "parts";
  if (target.kind === "around") return "around";
  if (target.kind === "block") return `part:${target.id}`;
  if (target.kind === "component") return `component:${target.id}`;
  return null; // a file opens the code itself
}
