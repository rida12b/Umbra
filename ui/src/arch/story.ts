import type { ArchBlock, Journey, JourneyStep, ProjectModel } from "../api";

const FALLBACK_WORDS = 5;

/** The step's title: its short action, or (models studied before v1.3) its first words, clearly cut. */
export function stepLabel(step: JourneyStep): string {
  if (step.action) return step.action;
  const words = step.texte.split(/\s+/);
  return words.length > FALLBACK_WORDS ? `${words.slice(0, FALLBACK_WORDS).join(" ")}…` : step.texte;
}

/** Who takes part in a step: the block at work, then the block it acts on (if another one). */
export function stepActors(model: ProjectModel, step: JourneyStep): ArchBlock[] {
  const blocks = new Map(model.blocs.map((b) => [b.id, b]));
  const owner = model.composants.find((c) => c.id === step.composant)?.bloc ?? step.composant;
  let here = blocks.get(owner) ?? null;
  let reached = step.touche.map((id) => blocks.get(id)).find((b) => b && b !== here) ?? null;
  // A person who acts (a command, a click) comes first: « Utilisateur agit sur Commande du moteur ».
  if (reached?.type === "user" && step.manuel) [here, reached] = [reached, here];
  return [here, reached].filter((b): b is ArchBlock => b !== null);
}

/** Every block a journey goes through, in the order the story meets them. */
export function journeyCast(model: ProjectModel, journey: Journey): ArchBlock[] {
  const cast: ArchBlock[] = [];
  for (const step of journey.etapes) for (const block of stepActors(model, step)) if (!cast.includes(block)) cast.push(block);
  return cast;
}

/** The journeys a block takes part in, and at which steps. */
export function journeysOf(model: ProjectModel, block: ArchBlock): { journey: Journey; steps: number[] }[] {
  return model.parcours
    .map((journey) => ({
      journey,
      steps: journey.etapes.flatMap((step, index) => (stepActors(model, step).includes(block) ? [index + 1] : [])),
    }))
    .filter(({ steps }) => steps.length > 0);
}

/** « envoie les demandes à » when the model has a verb; the longer description otherwise. */
export function flowWords(flow: { verbe?: string; quoi: string }): string {
  return flow.verbe || flow.quoi;
}
