import { createContext, useContext, useEffect, useState } from "react";
import { api, type Journey, type ModelState, type ProjectModel } from "./api";
import { useLive } from "./live";

const POLL_MS = 4000;

export const ModelContext = createContext<ModelState | null>(null);
export const useModel = () => useContext(ModelContext);

/**
 * The Project model: asks for a study when there is none (or an update when the code changed),
 * follows the session, and reads it again when the live stream says something changed.
 */
export function useProjectModel(projectId: string | null): ModelState | null {
  const [state, setState] = useState<ModelState | null>(null);
  const { revision } = useLive();

  useEffect(() => {
    if (!projectId) return;
    let current = true;
    let timer: number | undefined;
    const follow = (found: ModelState) => {
      if (!current) return;
      setState(found);
      if (found.state === "queued" || found.state === "working") {
        timer = window.setTimeout(() => api.model(projectId).then(follow, () => undefined), POLL_MS);
      }
    };
    api
      .model(projectId)
      .then((found) => (found.state === "missing" || found.state === "stale" ? api.study(projectId) : found))
      .then(follow, (error: Error) =>
        current && setState({ state: "error", model: null, created_at: null, changed: [], message: error.message }),
      );
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [projectId, revision]);

  useEffect(() => setState(null), [projectId]);
  return state;
}

/** The journeys, and their step numbers, that cite this file (or a file under this folder). */
export function journeysThrough(model: ProjectModel, path: string): { journey: Journey; steps: number[] }[] {
  return model.parcours
    .map((journey) => ({
      journey,
      steps: journey.etapes
        .map((step, index) => ({ step, index }))
        .filter(({ step }) => step.fichier !== null && (step.fichier === path || step.fichier.startsWith(`${path}/`)))
        .map(({ index }) => index + 1),
    }))
    .filter(({ steps }) => steps.length > 0);
}

/** One-sentence role of a map element from the model: a file, a folder, or a service's code folder. */
export function roleOf(model: ProjectModel | null | undefined, key: string, path: string | null): string | undefined {
  if (!model) return undefined;
  if (path !== null && model.modules[path]) return model.modules[path];
  if (key.startsWith("dir:")) return model.dossiers[key.slice(4)];
  return undefined;
}
