import { ArrowRight, ChevronRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { ArchBlock, Journey, JourneyStep, ProjectModel } from "../api";
import { Tag } from "../ui";
import { CitedCode } from "./CitedCode";
import { journeyCast, stepActors, stepLabel } from "./story";

interface Props {
  projectId: string;
  model: ProjectModel;
  journey: Journey;
  activeStep: number; // 1-based
  narrow: boolean;
  onStep: (number: number) => void;
  onBlock: (id: string) => void;
}

/**
 * One journey told as a story: the steps in order, in plain words, in the main column. Beside it, the
 * parts of the project that take part; the step being read lights the parts it involves.
 */
export function JourneyPage({ projectId, model, journey, activeStep, narrow, onStep, onBlock }: Props) {
  const cast = journeyCast(model, journey);
  const step = journey.etapes[activeStep - 1];
  const actors = step ? stepActors(model, step) : [];
  const activeRef = useRef<HTMLLIElement | null>(null);

  useEffect(() => {
    // Recent browsers return a Promise from scrollIntoView: an effect must return nothing but a clean-up.
    activeRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [activeStep]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      const typing = "input, textarea, select, [contenteditable], [role=listbox], [cmdk-root]";
      if (event.target instanceof HTMLElement && event.target.closest(typing)) return;
      if (event.key === "ArrowDown" && activeStep < journey.etapes.length) onStep(activeStep + 1);
      else if (event.key === "ArrowUp" && activeStep > 1) onStep(activeStep - 1);
      else return;
      event.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [activeStep, journey.etapes.length, onStep]);

  const castPanel = (
    <CastPanel model={model} cast={cast} actors={actors} number={activeStep} narrow={narrow} onBlock={onBlock} />
  );

  return (
    <div className={`h-full overflow-y-auto ${narrow ? "" : "grid grid-cols-[minmax(0,1fr)_340px]"}`}>
      <article className="mx-auto w-full max-w-[720px] px-6 pt-10 pb-[40vh]">
        <h1 className="text-[28px] leading-tight font-semibold tracking-[-0.01em]">{journey.nom}</h1>
        <div className={`mt-5 grid gap-3 ${narrow ? "grid-cols-1" : "grid-cols-2"}`}>
          <Bookend title="Ça commence quand">{journey.depart || journey.declencheur}</Bookend>
          <Bookend title="À la fin">{journey.fin || journey.resultat}</Bookend>
        </div>
        {narrow && <div className="sticky top-0 z-10 -mx-6 mt-6 bg-bg px-6 py-2">{castPanel}</div>}

        <ol className="mt-8 flex flex-col gap-1" aria-label="Les étapes">
          {journey.etapes.map((item, index) => (
            <li key={index + 1} ref={index + 1 === activeStep ? activeRef : undefined}>
              <Step projectId={projectId} step={item} number={index + 1} on={index + 1 === activeStep} onStep={onStep} />
            </li>
          ))}
        </ol>

        {(journey.branches ?? []).length > 0 && (
          <details className="mt-10">
            <summary className="cursor-pointer text-[18px] font-semibold">
              Si les choses se passent autrement ({(journey.branches ?? []).length})
            </summary>
            <ul className="mt-3 flex flex-col gap-2.5">
              {(journey.branches ?? []).map((branch, index) => (
                <li key={index} className="text-[16px] leading-relaxed text-muted">
                  <span className="font-medium text-ink">Si {lowerFirst(branch.quand)} : </span>
                  {branch.alors}
                </li>
              ))}
            </ul>
          </details>
        )}
      </article>
      {!narrow && (
        <aside className="border-l border-line-soft" aria-label="Qui intervient">
          <div className="sticky top-0 px-5 pt-10">{castPanel}</div>
        </aside>
      )}
    </div>
  );
}

function Bookend({ title, children }: { title: string; children: string }) {
  return (
    <div className="rounded-xl bg-raised px-5 py-4">
      <p className="text-[13px] font-semibold text-lamp-ink">{title}</p>
      <p className="mt-1 text-[16px] leading-relaxed">{children}</p>
    </div>
  );
}

function Step({ projectId, step, number, on, onStep }: {
  projectId: string; step: JourneyStep; number: number; on: boolean; onStep: (number: number) => void;
}) {
  const [details, setDetails] = useState(false);
  const conditions = step.conditions ?? [];
  const hasDetails = conditions.length > 0 || Boolean(step.fichier) || Boolean(step.simple && step.texte);
  return (
    <div className={`rounded-2xl px-4 py-4 ${on ? "bg-lamp-soft" : ""}`}>
      <button
        type="button"
        onClick={() => onStep(number)}
        aria-current={on ? "step" : undefined}
        aria-label={`Étape ${number} : ${stepLabel(step)}`}
        className="grid w-full grid-cols-[44px_1fr] gap-4 text-left"
      >
        <span
          className={`flex size-10 items-center justify-center rounded-full text-[17px] font-bold ${
            on ? "bg-lamp text-on-lamp" : "border-2 border-line text-muted"
          }`}
        >
          {number}
        </span>
        <span>
          <span className="flex flex-wrap items-center gap-2 text-[20px] leading-snug font-semibold">
            {stepLabel(step)}
            {step.manuel && (
              <span className="rounded-full bg-ok px-2.5 py-0.5 text-[12px] font-semibold text-bg">À faire vous-même</span>
            )}
          </span>
          <span className="mt-1 block text-[17px] leading-relaxed text-muted">{step.simple || step.texte}</span>
        </span>
      </button>
      {on && hasDetails && ( // details only under the step being read: the list stays plain
        <div className="mt-2 ml-[60px]">
          <button
            type="button"
            className="flex items-center gap-1 text-[14px] text-faint hover:text-ink"
            aria-expanded={details}
            onClick={() => setDetails(!details)}
          >
            <ChevronRight size={15} className={details ? "rotate-90" : ""} aria-hidden="true" />
            Détails pour développeur
          </button>
          {details && (
            <div className="mt-2 space-y-2 text-[14px] text-muted">
              {conditions.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {conditions.map((condition) => (
                    <Tag key={condition} tone="condition">
                      {condition}
                    </Tag>
                  ))}
                </div>
              )}
              {step.simple && <p className="leading-relaxed">{step.texte}</p>}
              <CitedCode projectId={projectId} cited={step} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CastPanel({ model, cast, actors, number, narrow, onBlock }: {
  model: ProjectModel; cast: ArchBlock[]; actors: ArchBlock[]; number: number; narrow: boolean;
  onBlock: (id: string) => void;
}) {
  const [doer, target] = actors;
  // « Moteur local lit et surveille Dossier du projet étudié »: the verb of the flow between them, if any.
  const flow = doer && target ? model.flux.find((f) => f.de === doer.id && f.vers === target.id) : undefined;
  const line = (
    <p className="flex min-h-12 flex-wrap items-center gap-x-1.5 text-[15px] leading-snug">
      <span className="text-muted">Étape {number} :</span>
      <b>{doer?.nom ?? "aucune pièce précise"}</b>
      {target &&
        (flow?.verbe ? (
          <span className="text-muted">{flow.verbe}</span>
        ) : (
          <ArrowRight size={15} className="text-lamp-ink" aria-label="agit sur" />
        ))}
      {target && <b>{target.nom}</b>}
    </p>
  );
  if (narrow) return <div className="rounded-xl bg-raised px-4 py-3">{line}</div>;
  return (
    <div>
      <h2 className="text-[14px] font-semibold text-faint">Qui intervient</h2>
      <div className="mt-2">{line}</div>
      <ul className="mt-3 flex flex-col gap-2">
        {cast.map((block) => {
          const lit = actors.includes(block);
          return (
            <li key={block.id}>
              <button
                type="button"
                onClick={() => onBlock(block.id)}
                className={`w-full rounded-xl border px-4 py-3 text-left ${
                  lit ? "border-lamp-line bg-panel" : "border-line-soft opacity-50 hover:opacity-80"
                }`}
              >
                <span className="block text-[15px] font-semibold">{block.nom}</span>
                <span className="block text-[13.5px] leading-snug text-muted">{block.en_bref || block.role}</span>
              </button>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-[13px] leading-snug text-faint">
        Encadrées : les pièces de cette étape. Grisées : les autres pièces de l'histoire.
      </p>
    </div>
  );
}

/** « Si une page… », not « Si Une page… »; an acronym (« API indisponible ») keeps its capitals. */
function lowerFirst(text: string): string {
  const [first = "", second = ""] = text;
  return second === second.toUpperCase() && second !== second.toLowerCase() ? text : first.toLowerCase() + text.slice(1);
}
