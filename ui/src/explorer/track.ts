import type { Journey, ProjectModel } from "../api";
import { stepActors } from "../arch/story";
import type { Level } from "./levels";

/** Where one step of a journey shows on the current level. */
export interface StepOnMap {
  boxes: string[]; // the boxes lit: one (it happens inside) or two (from → to)
  link: string | null; // the arrow it runs along, if the level has one between those boxes
  elsewhere: { id: string; title: string } | null; // the step happens inside this box: « entrer pour la voir »
}

/**
 * Each step of a journey, placed on a level: the step's parts (see stepActors) are mapped to the
 * boxes that contain them at this zoom (the whole system, a part, a component).
 */
export function trackJourney(model: ProjectModel, journey: Journey, level: Level): StepOnMap[] {
  const boxIds = new Set(level.boxes.map((b) => b.id));
  const componentBlock = new Map(model.composants.map((c) => [c.id, c.bloc]));
  const atThisLevel = (blockId: string, componentId: string | null): string | null => {
    if (componentId && boxIds.has(componentId)) return componentId; // inside the part being looked at
    if (boxIds.has(blockId)) return blockId;
    if (boxIds.has("system") && level.key === "context") return "system";
    if (boxIds.has("around")) return "around";
    return null;
  };

  return journey.etapes.map((step) => {
    const [doer, target] = stepActors(model, step);
    const ownComponent = componentBlock.get(step.composant) === doer?.id ? step.composant : null;
    const from = doer ? atThisLevel(doer.id, ownComponent) : null;
    const to = target ? atThisLevel(target.id, null) : null;
    const boxes = [...new Set([from, to].filter((id): id is string => id !== null))];
    const link =
      from && to && from !== to
        ? (level.links.find((l) => (l.from === from && l.to === to) || (l.from === to && l.to === from))?.id ?? null)
        : null;
    const single = boxes.length === 1 ? level.boxes.find((b) => b.id === boxes[0]) : undefined;
    return { boxes, link, elsewhere: single && single.inside > 0 ? { id: single.id, title: single.title } : null };
  });
}
