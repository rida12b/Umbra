import type { ArchBlock, Journey, JourneyStep, ProjectModel } from "../api";

const FALLBACK_WORDS = 5;

/** Models studied before the short `action` existed: the first words of the step, clearly cut. */
export function stepLabel(step: JourneyStep): string {
  if (step.action) return step.action;
  const words = step.texte.split(/\s+/);
  return words.length > FALLBACK_WORDS ? `${words.slice(0, FALLBACK_WORDS).join(" ")}…` : step.texte;
}

/** One step as one row: who acts, on whom (none when it stays inside one block), and what. */
export interface SequenceRow {
  number: number;
  from: string | null;
  to: string | null;
  label: string;
}

export interface Sequence {
  lanes: ArchBlock[]; // the blocks the journey goes through, in the order it meets them
  rows: SequenceRow[];
}

/**
 * A journey as a sequence diagram: one column per block, one row per step, time going down. The
 * order of the steps is the order of the rows, so a step number can never sit in the wrong place.
 */
export function journeySequence(model: ProjectModel, journey: Journey): Sequence {
  const blocks = new Map(model.blocs.map((b) => [b.id, b]));
  const blockOf = new Map(model.composants.map((c) => [c.id, c.bloc]));
  const lanes: ArchBlock[] = [];
  const meet = (id: string | null) => {
    const block = id ? blocks.get(id) : undefined;
    if (block && !lanes.includes(block)) lanes.push(block);
  };

  let previous: string | null = null;
  const rows = journey.etapes.map((step, index): SequenceRow => {
    const owner = blockOf.get(step.composant) ?? step.composant;
    const here = blocks.has(owner) ? owner : null;
    const reached = step.touche.find((id) => blocks.has(id) && id !== here) ?? null;
    let from = here ?? previous;
    let to = reached;
    // A person who acts (a command, a click) starts the arrow; otherwise the block at work does.
    if (to && step.manuel && blocks.get(to)?.type === "user") [from, to] = [to, from];
    if (!from) [from, to] = [to, null];
    meet(from);
    meet(to);
    if (here) previous = here;
    return { number: index + 1, from, to, label: stepLabel(step) };
  });
  return { lanes, rows };
}
