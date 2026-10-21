import { useCallback } from "react";
import type { Project } from "../api";
import { useModel } from "../model";
import { ARCHITECTURE_VIEW, MAP_VIEW, navigate, type Route } from "../route";
import type { Theme } from "../theme";
import { StateMessage } from "../ui";
import { BlockPage } from "./BlockPage";
import { HomePage } from "./HomePage";
import { JourneyPage } from "./JourneyPage";
import { MapPage } from "./MapPage";
import { ModelPending } from "./ModelStatus";

interface Props {
  project: Project;
  route: Route;
  theme: Theme;
  narrow: boolean;
}

/**
 * Everything the model says, as pages to read: the project home, one page per journey (its story),
 * one page per part, and the map of every part. Which page shows is in the URL.
 */
export function ArchitectureView({ project, route, theme, narrow }: Props) {
  const state = useModel();
  const model = state?.model ?? null;
  const go = useCallback(
    (change: Partial<Route>) =>
      navigate({ projectId: project.id, node: ARCHITECTURE_VIEW, expand: false, journey: null, step: null, select: null, ...change }),
    [project.id],
  );
  const journeyId = route.journey ?? null;
  const onStep = useCallback((step: number) => go({ journey: journeyId, step }), [go, journeyId]);
  const onJourney = useCallback((id: string, step = 1) => go({ journey: id, step }), [go]);
  const onBlock = useCallback((id: string) => go({ select: id }), [go]);

  if (!model) return <ModelPending state={state} />;
  const block = route.select ? model.blocs.find((b) => b.id === route.select) : undefined;
  const journey = journeyId ? model.parcours.find((j) => j.id === journeyId) : undefined;

  if ((route.select && !block) || (journeyId && !journey))
    return (
      <StateMessage title={route.select ? "Cette pièce n'existe plus" : "Cette histoire n'existe plus"}>
        <p>Le projet a changé depuis ce lien.</p>
        <button type="button" className="mt-3 text-ink underline underline-offset-[3px]" onClick={() => go({})}>
          Revenir à l'accueil du projet
        </button>
      </StateMessage>
    );
  if (block)
    return (
      <BlockPage
        key={block.id}
        project={project}
        model={model}
        block={block}
        onBack={() => go({})}
        onJourney={onJourney}
        onBlock={onBlock}
      />
    );
  if (route.node === MAP_VIEW) return <MapPage model={model} theme={theme} onBlock={onBlock} />;
  if (journey) {
    if (journey.etapes.length === 0)
      return <StateMessage title="Cette histoire n'a pas d'étape">Claude n'en a décrit aucune. Choisissez une autre histoire.</StateMessage>;
    const step = Math.min(route.step ?? 1, journey.etapes.length);
    return (
      <JourneyPage
        key={journey.id}
        projectId={project.id}
        model={model}
        journey={journey}
        activeStep={step}
        narrow={narrow}
        onStep={onStep}
        onBlock={onBlock}
      />
    );
  }
  return <HomePage project={project} model={model} theme={theme} narrow={narrow} onJourney={onJourney} onBlock={onBlock} />;
}
