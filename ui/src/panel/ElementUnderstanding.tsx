import type { MapNode } from "../api";
import { journeysThrough, roleOf, useModel } from "../model";
import { ARCHITECTURE_VIEW, navigate } from "../route";
import { Button, SectionTitle } from "../ui";
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
    <section>
      {role ? (
        <p className="mt-2.5 text-[14px] leading-relaxed text-muted">{role}</p>
      ) : (
        !model && <p className="mt-2.5 text-[13px] text-faint">Claude Code étudie le projet…</p>
      )}
      {through.length > 0 && (
        <>
          <SectionTitle>Intervient dans</SectionTitle>
          <ul className="space-y-1">
            {through.map(({ journey, steps }) => (
              <li key={journey.id} className="text-[13px]">
                <Button
                  variant="link"
                  onClick={() => navigate({ projectId, node: ARCHITECTURE_VIEW, expand: false, journey: journey.id, step: steps[0] })}
                >
                  {journey.nom}
                </Button>
                <span className="text-faint">
                  {" "}
                  — étape{steps.length > 1 ? "s" : ""} {steps.join(", ")}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
      {card?.card || deepState === "queued" || deepState === "working" ? (
        <ExplanationCard projectId={projectId} explanation={card} defaultFile={node.path} />
      ) : (
        node.kind !== "application" && (
          <Button className="mt-5" onClick={request}>
            Approfondir avec Claude : entrées, sorties, étapes
          </Button>
        )
      )}
      {deepState === "stale" && card?.card && (
        <Button variant="link" className="mt-2 text-[13px]" onClick={request}>
          Le code a changé : réécrire cette fiche
        </Button>
      )}
    </section>
  );
}
