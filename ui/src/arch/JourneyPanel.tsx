import { ChevronRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Journey, JourneyStep } from "../api";
import { SectionTitle, Tag } from "../ui";
import { CitedCode } from "./CitedCode";
import { stepLabel } from "./sequence";

interface Props {
  projectId: string;
  journey: Journey;
  activeStep: number | null;
  onStep: (number: number) => void;
}

/** One journey as a list of steps, in plain words first. The active step is the one lit on the map. */
export function JourneyPanel({ projectId, journey, activeStep, onStep }: Props) {
  const active = useRef<HTMLLIElement | null>(null);
  useEffect(() => {
    // Recent browsers return a Promise from scrollIntoView: an effect must return nothing but a clean-up.
    active.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [journey.id, activeStep]);

  const manual = journey.etapes.filter((step) => step.manuel).length;
  const branches = journey.branches ?? [];

  return (
    <article className="px-6 pt-5 pb-10">
      <h1 className="max-w-[34ch] text-[20px] leading-snug font-semibold tracking-[-0.01em]">{journey.nom}</h1>
      {journey.declencheur && (
        <p className="mt-2 text-[14px] leading-relaxed text-muted">
          <span className="font-medium text-ink">Point de départ : </span>
          {journey.declencheur}
        </p>
      )}
      <p className="mt-2 text-[13px] text-faint">
        {journey.etapes.length} étapes
        {manual > 0 && (manual === 1 ? ", dont 1 à faire soi-même" : `, dont ${manual} à faire soi-même`)}
      </p>

      <ol className="mt-5 flex flex-col gap-1">
        {journey.etapes.map((step, index) => {
          const number = index + 1;
          const on = number === activeStep;
          return (
            <li
              key={number}
              ref={on ? active : undefined}
              className={`rounded-lg border px-3 py-2.5 ${on ? "border-lamp-line bg-lamp-soft" : "border-transparent hover:bg-raised"}`}
            >
              <Step projectId={projectId} step={step} number={number} on={on} onStep={onStep} />
            </li>
          );
        })}
      </ol>

      {branches.length > 0 && (
        <>
          <SectionTitle>Si les choses se passent autrement</SectionTitle>
          <ul className="flex flex-col gap-2">
            {branches.map((branch, index) => (
              <li key={index} className="text-[14px] leading-relaxed text-muted">
                <span className="font-medium text-ink">Si {branch.quand} : </span>
                {branch.alors}
              </li>
            ))}
          </ul>
        </>
      )}

      {journey.resultat && (
        <>
          <SectionTitle>À la fin</SectionTitle>
          <p className="rounded-lg bg-raised px-3 py-2.5 text-[14px] leading-relaxed">{journey.resultat}</p>
        </>
      )}
    </article>
  );
}

function Step({ projectId, step, number, on, onStep }: {
  projectId: string; step: JourneyStep; number: number; on: boolean; onStep: (number: number) => void;
}) {
  const [technical, setTechnical] = useState(false);
  const plain = step.simple || step.texte; // models studied before v1.4 have only the technical text
  return (
    <>
      <button
        type="button"
        className="flex w-full items-start gap-3 text-left"
        onClick={() => onStep(number)}
        aria-label={`Étape ${number}`}
        aria-current={on ? "step" : undefined}
      >
        <span className="step-number mt-0.5" data-on={on} data-muted={!on}>
          {number}
        </span>
        <span className="min-w-0">
          <span className={`block text-[14.5px] font-semibold ${on ? "text-ink" : "text-ink/85"}`}>{stepLabel(step)}</span>
          <span className="mt-0.5 block text-[14px] leading-relaxed text-muted">{plain}</span>
        </span>
      </button>
      {(step.manuel || (step.conditions ?? []).length > 0) && (
        <div className="mt-2 ml-[34px] flex flex-wrap gap-1.5">
          {step.manuel && <Tag tone="manual">À faire soi-même</Tag>}
          {(step.conditions ?? []).map((condition) => (
            <Tag key={condition} tone="condition">
              {condition}
            </Tag>
          ))}
        </div>
      )}
      {on && (step.simple || step.fichier) && (
        <div className="mt-2 ml-[34px]">
          <button
            type="button"
            className="flex items-center gap-1 text-[13px] text-muted hover:text-ink"
            aria-expanded={technical}
            onClick={() => setTechnical(!technical)}
          >
            <ChevronRight size={14} className={technical ? "rotate-90" : ""} aria-hidden="true" />
            Détail technique et code
          </button>
          {technical && (
            <div className="mt-1.5">
              {step.simple && <p className="text-[13px] leading-relaxed text-muted">{step.texte}</p>}
              <CitedCode projectId={projectId} cited={step} />
            </div>
          )}
        </div>
      )}
    </>
  );
}

