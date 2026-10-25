import type { ArchBlock, JourneyStep, ProjectModel } from "../api";

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
  const owner = model.composants.find((c) => c.id === step.composant)?.bloc ?? step.composant ?? "";
  let here = blocks.get(owner) ?? null;
  let reached = step.touche.map((id) => blocks.get(id)).find((b) => b && b !== here) ?? null;
  // A step done by hand is done by the part it reaches (a person, whatever type Claude gave it):
  // « Personne qui lance le service → Serveur de réception », not the other way round.
  if (reached && step.manuel) [here, reached] = [reached, here];
  return [here, reached].filter((b): b is ArchBlock => b !== null);
}

/** « Le serveur… », « L'en-tête… » → « le serveur… », « l'en-tête… »; a name (« WeasyPrint », « API ») keeps its capitals. */
export function lowerFirst(text: string): string {
  const word = text.split(/[\s'’]/)[0] ?? "";
  return /[A-Z]/.test(word.slice(1)) ? text : text.charAt(0).toLowerCase() + text.slice(1);
}
