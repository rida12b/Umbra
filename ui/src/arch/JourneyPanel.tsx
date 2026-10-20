import { useEffect, useRef } from "react";
import type { Journey } from "../api";
import { SectionTitle, Tag } from "../ui";
import { CitedCode } from "./CitedCode";

interface Props {
  projectId: string;
  journey: Journey;
  activeStep: number | null;
  onStep: (number: number) => void;
}

/** One journey as a timeline. The active step is the one lit on the map, with its code open. */
export function JourneyPanel({ projectId, journey, activeStep, onStep }: Props) {
  const active = useRef<HTMLLIElement | null>(null);
  useEffect(() => {
    // Recent browsers return a Promise from scrollIntoView: an effect must return nothing but a clean-up.
    active.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [journey.id, activeStep]);

  const manual = journey.etapes.filter((step) => step.manuel).length;
  const branches = journey.branches ?? [];
  const cited = journey.etapes.filter((step) => step.fichier);
  const verified = cited.filter((step) => step.verifie).length;

  return (
    <article className="px-6 pt-5 pb-10">
      <h1 className="max-w-[34ch] text-[19px] leading-snug font-semibold tracking-[-0.01em]">{journey.nom}</h1>
      {journey.declencheur && (
        <p className="mt-2.5 text-[13.5px] text-muted">
          <span className="font-medium text-ink">Point de départ : </span>
          {journey.declencheur}
        </p>
      )}
      <p className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[12.5px] text-faint">
        <span>{journey.etapes.length} étapes</span>
        {manual > 0 && <span>{manual === 1 ? "1 action manuelle" : `${manual} actions manuelles`}</span>}
        {branches.length > 0 && <span>{branches.length === 1 ? "1 autre chemin" : `${branches.length} autres chemins`}</span>}
        {cited.length > 0 && (
          <span className={verified === cited.length ? "text-ok" : ""}>
            Code vérifié {verified}/{cited.length}
          </span>
        )}
      </p>

      <ol className="relative mt-5 before:absolute before:top-2 before:bottom-2 before:left-[11px] before:w-px before:bg-line">
        {journey.etapes.map((step, index) => {
          const number = index + 1;
          const on = number === activeStep;
          return (
            <li key={number} ref={on ? active : undefined} className="relative pb-4 pl-[38px]">
              <button
                type="button"
                className="absolute top-0 left-0"
                onClick={() => onStep(number)}
                aria-label={`Étape ${number}`}
                aria-current={on ? "step" : undefined}
              >
                <span className="step-number" data-on={on} data-muted={!on}>
                  {number}
                </span>
              </button>
              <button
                type="button"
                className={`block text-left text-[13.5px] ${on ? "text-ink" : "text-muted hover:text-ink"}`}
                onClick={() => onStep(number)}
              >
                {step.texte}
              </button>
              {(step.manuel || (step.conditions ?? []).length > 0) && (
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {step.manuel && <Tag tone="manual">Action manuelle</Tag>}
                  {(step.conditions ?? []).map((condition) => (
                    <Tag key={condition} tone="condition">
                      {condition}
                    </Tag>
                  ))}
                </div>
              )}
              <CitedCode key={`${number}-${on}`} projectId={projectId} cited={step} open={on} />
            </li>
          );
        })}
      </ol>

      {branches.length > 0 && (
        <>
          <SectionTitle>Autres chemins</SectionTitle>
          {branches.map((branch, index) => (
            <div key={index} className="border-t border-line-soft py-2 text-[13px] text-muted">
              <span className="font-medium text-ink">Si {branch.quand}, </span>
              {branch.alors}
              <CitedCode projectId={projectId} cited={branch} />
            </div>
          ))}
        </>
      )}

      {journey.resultat && (
        <>
          <SectionTitle>Résultat</SectionTitle>
          <p className="rounded-md bg-raised px-3 py-2.5 text-[13.5px]">{journey.resultat}</p>
        </>
      )}
    </article>
  );
}
