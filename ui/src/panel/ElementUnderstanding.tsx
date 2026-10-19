import type { MapNode } from "../api";
import { journeysThrough, roleOf, useModel } from "../model";
import { JOURNEYS_VIEW, navigate } from "../route";
import { ExplanationCard } from "./ExplanationCard";
import { useExplanation } from "./useExplanation";

/**
 * What the Project model says about one element — its role, and the journeys it takes part in —
 * then, on demand, Claude's deeper card on it.
 */
export function ElementUnderstanding({ projectId, node }: { projectId: string; node: MapNode }) {
  const state = useModel();
  const model = state?.model ?? null;
  const [card, request] = useExplanation(projectId, node.key);
  const path = node.key === "app:" ? null : node.path;
  const role = node.key === "app:" ? model?.resume : roleOf(model, node.key, path);
  const through = model && path !== null ? journeysThrough(model, path) : [];
  const deepState = card?.state;

  return (
    <section className="understanding">
      {role ? <p className="card-role">{role}</p> : model ? null : <p className="writing">Claude Code étudie le projet…</p>}
      {through.length > 0 && (
        <>
          <h3 className="card-title">Intervient dans</h3>
          <ul className="journey-links">
            {through.map(({ journey, steps }) => (
              <li key={journey.id}>
                <button
                  className="link-button"
                  onClick={() =>
                    navigate({ projectId, node: JOURNEYS_VIEW, expand: false, journey: journey.id, step: steps[0] })
                  }
                >
                  {journey.nom}
                </button>
                <span className="muted"> — étape{steps.length > 1 ? "s" : ""} {steps.join(", ")}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      {card?.card || deepState === "queued" || deepState === "working" ? (
        <ExplanationCard projectId={projectId} explanation={card} defaultFile={node.path} />
      ) : (
        node.kind !== "application" && (
          <button className="deepen" onClick={request}>
            Approfondir avec Claude : entrées, sorties, étapes
          </button>
        )
      )}
      {deepState === "stale" && card?.card && (
        <button className="link-button" onClick={request}>Le code a changé : réécrire cette fiche</button>
      )}
    </section>
  );
}
