import type { Journey, ProjectModel } from "../api";
import { stepActors, stepLabel } from "../arch/story";
import { zoneOf, type Level, type Target } from "./levels";

/** Where one step of a journey shows on the current level. */
export interface StepOnMap {
  boxes: string[]; // the boxes lit: where it happens, what it acts on, and anything else it reaches
  link: string | null; // the arrow it runs along, if the level has one between those boxes
  elsewhere: { id: string; title: string } | null; // the step happens inside this box: « entrer pour la voir »
  words: string; // the step's short action, on its arrow
  arrow: boolean; // false: the step works on what came in (a check, a reply being built), no data moves yet
}

/**
 * Each step of a journey, placed on a level: the step's parts (see stepActors) are mapped to the
 * boxes that contain them at this zoom (the whole system, a part, a component).
 */
export function trackJourney(model: ProjectModel, journey: Journey, level: Level): StepOnMap[] {
  const boxOf = (kind: Target["kind"], id?: string) =>
    level.boxes.find((b) => b.target.kind === kind && (id === undefined || ("id" in b.target && b.target.id === id)))?.id ?? null;
  const componentBlock = new Map(model.composants.map((c) => [c.id, c.bloc]));
  // A grouped part shows as the group of its zone.
  const groupOf = (blockId: string) => {
    const block = model.blocs.find((b) => b.id === blockId);
    return block ? (level.boxes.find((b) => b.target.kind === "around" && b.zone === zoneOf(block))?.id ?? null) : null;
  };
  const atThisLevel = (blockId: string, componentId: string | null): string | null =>
    (componentId ? boxOf("component", componentId) : null) ?? // inside the part being looked at
    boxOf("block", blockId) ??
    boxOf("system") ??
    groupOf(blockId);

  const last = journey.etapes.length - 1;
  const zoneOfBlock = new Map(model.blocs.map((b) => [b.id, zoneOf(b)]));
  return journey.etapes.map((step, index) => {
    const [doer, target] = stepActors(model, step);
    // The step's component belongs to one of the two (the target when the step is done by hand).
    const componentOf = (blockId: string | undefined) => (componentBlock.get(step.composant) === blockId ? step.composant : null);
    const from = doer ? atThisLevel(doer.id, componentOf(doer.id)) : null;
    const to = target ? atThisLevel(target.id, componentOf(target.id)) : null;
    const also = step.touche.filter((id) => id !== doer?.id && id !== target?.id).map((id) => atThisLevel(id, null));
    const boxes = [...new Set([from, to, ...also].filter((id): id is string => id !== null))];
    // Mid-path, a step that « reaches » the person who asked is working on their request (checking
    // it, reading their history): the answer only travels back to them at the end.
    const arrow = !(target && zoneOfBlock.get(target.id) === "utilise" && !step.manuel && index < last);
    const link =
      arrow && from && to && from !== to
        ? (level.links.find((l) => l.from === from && l.to === to)?.id ?? null) // an answer going back gets its own arrow
        : null;
    const single = boxes.length === 1 ? level.boxes.find((b) => b.id === boxes[0]) : undefined;
    const elsewhere = single && single.inside > 0 ? { id: single.id, title: single.title } : null;
    return { boxes, link, elsewhere, words: stepLabel(step), arrow };
  });
}
