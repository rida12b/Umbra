import { useEffect, useRef } from "react";
import type { Journey, Project, ProjectModel } from "../api";
import { useModel } from "../model";
import { ARCHITECTURE_VIEW, JOURNEYS_VIEW, navigate, type Route } from "../route";
import { BLOCK_LABEL, BlockIcon } from "./BlockNode";
import { CitedCode } from "./CitedCode";
import { ModelPending, ModelStatusLine } from "./ModelStatus";

/** What the system does, from end to end: each journey as the steps it takes through the code. */
export function JourneysView({ project, route }: { project: Project; route: Route }) {
  const state = useModel();
  const model = state?.model ?? null;
  if (!model) return <ModelPending state={state} />;
  const journey = model.parcours.find((j) => j.id === route.journey) ?? model.parcours[0];
  const show = (id: string) => navigate({ projectId: project.id, node: JOURNEYS_VIEW, expand: false, journey: id });

  return (
    <div className="journeys">
      <nav className="journey-list" aria-label="Parcours">
        <p className="panel-kind">Parcours de bout en bout</p>
        {model.parcours.map((item) => (
          <button
            key={item.id}
            className={`journey-item${item.id === journey?.id ? " active" : ""}`}
            onClick={() => show(item.id)}
          >
            <span className="journey-name">{item.nom}</span>
            <span className="muted">{item.etapes.length} étapes</span>
          </button>
        ))}
        <ModelStatusLine />
      </nav>
      {journey ? (
        <JourneyDetail journey={journey} model={model} project={project} focus={route.step ?? null} />
      ) : (
        <div className="state">Aucun parcours trouvé dans ce projet.</div>
      )}
    </div>
  );
}

function JourneyDetail({ journey, model, project, focus }: {
  journey: Journey; model: ProjectModel; project: Project; focus: number | null;
}) {
  const components = new Map(model.composants.map((c) => [c.id, c]));
  const blocks = new Map(model.blocs.map((b) => [b.id, b]));
  const focused = useRef<HTMLLIElement | null>(null);
  useEffect(() => focused.current?.scrollIntoView({ block: "center" }), [journey.id, focus]);

  return (
    <article className="journey">
      <header>
        <h1>{journey.nom}</h1>
        <p><strong>Déclencheur :</strong> {journey.declencheur}</p>
        <button
          className="link-button"
          onClick={() => navigate({ projectId: project.id, node: ARCHITECTURE_VIEW, expand: false, journey: journey.id })}
        >
          Voir ce parcours sur le schéma →
        </button>
      </header>
      <ol className="timeline">
        {journey.etapes.map((step, index) => {
          const component = components.get(step.composant);
          const block = component ? blocks.get(component.bloc) : blocks.get(step.composant);
          return (
            <li
              key={index}
              ref={focus === index + 1 ? focused : undefined}
              className={`step tone-${block?.type ?? "library"}${focus === index + 1 ? " focused" : ""}`}
            >
              <span className="step-number">{index + 1}</span>
              <div className="step-body">
                <span className="step-where">
                  {block && <BlockIcon type={block.type} />}
                  {component?.nom ?? step.composant}
                  {block && <span className="muted"> · {block.nom} ({BLOCK_LABEL[block.type]})</span>}
                </span>
                <p>{step.texte}</p>
                {step.touche.length > 0 && (
                  <p className="step-reaches">
                    → {step.touche.map((id) => blocks.get(id)?.nom ?? id).join(", ")}
                  </p>
                )}
                <CitedCode projectId={project.id} cited={step} />
              </div>
            </li>
          );
        })}
      </ol>
      <footer>
        <strong>Résultat :</strong> {journey.resultat}
      </footer>
    </article>
  );
}

/** The blocks a journey goes through (where each step runs, and what it reaches), and the flows
between them, for the diagram. The journey starts with the user when the Project has one. */
export function journeyHighlight(model: ProjectModel, journeyId: string): { blocks: Set<string>; flows: Set<string> } | null {
  const journey = model.parcours.find((j) => j.id === journeyId);
  if (!journey) return null;
  const known = new Set(model.blocs.map((b) => b.id));
  const blockOf = new Map(model.composants.map((c) => [c.id, c.bloc]));
  const blocks = new Set<string>();
  const flows = new Set<string>();
  const link = (a: string, b: string) => {
    flows.add(`${a}>${b}`);
    flows.add(`${b}>${a}`);
  };
  let previous: string | null = model.blocs.find((b) => b.type === "user")?.id ?? null;
  if (previous) blocks.add(previous);
  for (const step of journey.etapes) {
    const here = blockOf.get(step.composant) ?? step.composant;
    if (!known.has(here)) continue;
    blocks.add(here);
    if (previous && previous !== here) link(previous, here);
    for (const reached of step.touche) {
      blocks.add(reached);
      link(here, reached);
    }
    previous = here;
  }
  return { blocks, flows };
}
