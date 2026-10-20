import type { Journey, JourneyStep, ProjectModel } from "../api";

/** One step as the map shows it: its number and a few words saying what happens. */
export interface StepMark {
  number: number;
  label: string;
  manual: boolean;
}

/**
 * Where each step of a journey goes on the map. A step that moves something from one block to
 * another is written on that arrow; a step that stays inside one block is written in the block.
 * Arrow keys are `f<index>` for the model's flows, `j:<from>><to>` for journey moves the model
 * has no flow for (drawn only while the journey is shown).
 */
export interface JourneyPath {
  blocks: Set<string>;
  edges: Set<string>;
  onEdges: Map<string, StepMark[]>;
  inBlocks: Map<string, StepMark[]>;
  extraEdges: { key: string; source: string; target: string }[];
  unplaced: number[]; // steps the model ties to no block of the map
}

const FALLBACK_WORDS = 5;

/** Models studied before the short `action` existed: the first words of the step, clearly cut. */
export function stepLabel(step: JourneyStep): string {
  if (step.action) return step.action;
  const words = step.texte.split(/\s+/);
  return words.length > FALLBACK_WORDS ? `${words.slice(0, FALLBACK_WORDS).join(" ")}…` : step.texte;
}

export function journeyPath(model: ProjectModel, journey: Journey): JourneyPath {
  const known = new Set(model.blocs.map((b) => b.id));
  const blockOf = new Map(model.composants.map((c) => [c.id, c.bloc]));
  const flowKey = new Map<string, string>();
  model.flux.forEach((flow, index) => {
    flowKey.set(`${flow.de}>${flow.vers}`, `f${index}`);
    if (!flowKey.has(`${flow.vers}>${flow.de}`)) flowKey.set(`${flow.vers}>${flow.de}`, `f${index}`);
  });
  const path: JourneyPath = { blocks: new Set(), edges: new Set(), onEdges: new Map(), inBlocks: new Map(), extraEdges: [], unplaced: [] };
  const add = <K>(map: Map<K, StepMark[]>, key: K, mark: StepMark) => map.set(key, [...(map.get(key) ?? []), mark]);

  const arrow = (from: string, to: string): string => {
    const key = flowKey.get(`${from}>${to}`);
    if (key) return key;
    const extra = `j:${from}>${to}`;
    if (!path.extraEdges.some((edge) => edge.key === extra)) path.extraEdges.push({ key: extra, source: from, target: to });
    return extra;
  };

  let previous: string | null = null;
  journey.etapes.forEach((step, index) => {
    const mark = { number: index + 1, label: stepLabel(step), manual: step.manuel === true };
    const owner = blockOf.get(step.composant) ?? step.composant;
    const here = known.has(owner) ? owner : null;
    const reached = step.touche.filter((id) => known.has(id) && id !== here);
    if (here) path.blocks.add(here);
    reached.forEach((id) => path.blocks.add(id));

    const [first, ...others] = reached;
    if (here && first) {
      const key = arrow(here, first);
      path.edges.add(key);
      add(path.onEdges, key, mark);
      others.forEach((id) => path.edges.add(arrow(here, id)));
    } else {
      const inside = here ?? first ?? previous; // no known block: it goes on where the last step was
      if (inside) add(path.inBlocks, inside, mark);
      else path.unplaced.push(mark.number);
    }
    // The hand-over between two steps in different blocks is lit too, when the model has that flow.
    if (here && previous && previous !== here) {
      const between = flowKey.get(`${previous}>${here}`);
      if (between) path.edges.add(between);
    }
    if (here) previous = here;
  });
  return path;
}
