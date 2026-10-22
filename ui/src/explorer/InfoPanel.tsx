import { ChevronRight, Play } from "lucide-react";
import type { ReactNode } from "react";
import type { Journey, ProjectModel } from "../api";
import { CitedCode } from "../arch/CitedCode";
import { stepLabel } from "../arch/story";
import { steps, Tag } from "../ui";
import type { Box, Level } from "./levels";

interface Props {
  projectId: string;
  model: ProjectModel;
  level: Level;
  box: Box | null;
  playing: { journey: Journey; step: number } | null;
  onEnter: (box: Box) => void;
  onPlay: (journeyId: string, step: number) => void;
  onStep: (step: number) => void;
}

/** The fixed panel: what the selected box is, or the step being played, or where you are. */
export function InfoPanel({ projectId, model, level, box, playing, onEnter, onPlay, onStep }: Props) {
  if (box) return <BoxInfo projectId={projectId} model={model} box={box} onEnter={onEnter} onPlay={onPlay} />;
  if (playing) return <StepInfo projectId={projectId} journey={playing.journey} number={playing.step} onStep={onStep} />;
  return (
    <Panel>
      <p className="text-[13px] font-semibold text-faint">Vous êtes ici</p>
      <h2 className="mt-1 text-[22px] leading-tight font-semibold">{level.title}</h2>
      <p className="mt-2 text-[15px] leading-relaxed text-muted">{level.hint}</p>
      {(level.key === "context" || level.key === "parts") && (
        <p className="mt-4 text-[16px] leading-relaxed">{model.pitch || model.resume}</p>
      )}
      <Journeys model={model} onPlay={onPlay} />
      <p className="mt-6 text-[13.5px] leading-relaxed text-faint">
        Cliquez une boîte pour savoir ce qu'elle fait. « Entrer dedans » montre ce qu'elle contient, jusqu'au code.
      </p>
      {model.incertitudes.length > 0 && (
        <details className="mt-5 text-[14px]">
          <summary className="cursor-pointer text-muted hover:text-ink">Ce que Claude n'a pas pu vérifier ({model.incertitudes.length})</summary>
          <ul className="mt-2 list-disc space-y-1.5 pl-5 text-muted">
            {model.incertitudes.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </details>
      )}
    </Panel>
  );
}

function Panel({ children }: { children: ReactNode }) {
  return <div className="px-6 pt-6 pb-10">{children}</div>;
}

function Journeys({ model, onPlay, only }: { model: ProjectModel; onPlay: (id: string, step: number) => void; only?: Map<string, number> }) {
  const list = model.parcours.filter((j) => !only || only.has(j.id));
  if (list.length === 0) return null;
  return (
    <section className="mt-7">
      <h3 className="text-[15px] font-semibold">{only ? "Les chemins qui passent par ici" : "Suivre un chemin de données"}</h3>
      <ul className="mt-2 flex flex-col gap-2">
        {list.map((journey) => (
          <li key={journey.id}>
            <button
              type="button"
              onClick={() => onPlay(journey.id, only?.get(journey.id) ?? 1)}
              className="flex w-full items-start gap-3 rounded-xl border border-line bg-panel px-4 py-3 text-left hover:border-lamp-line"
            >
              <Play size={16} className="mt-1 shrink-0 text-lamp-ink" aria-hidden="true" />
              <span>
                <span className="block text-[15px] font-semibold leading-snug">{journey.nom}</span>
                <span className="block text-[13.5px] text-muted">
                  {only ? `À partir de l'étape ${only.get(journey.id)}` : `${journey.depart || journey.declencheur}`}
                </span>
                <span className="block text-[12.5px] text-faint">
                  {steps(journey.etapes.length)}
                  {journey.branches?.length ? ` · ${otherCases(journey.branches.length)}` : ""}
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function BoxInfo({ projectId, model, box, onEnter, onPlay }: {
  projectId: string; model: ProjectModel; box: Box; onEnter: (box: Box) => void; onPlay: (id: string, step: number) => void;
}) {
  const target = box.target;
  const block = target.kind === "block" ? model.blocs.find((b) => b.id === target.id) : undefined;
  const component = target.kind === "component" ? model.composants.find((c) => c.id === target.id) : undefined;
  const ownComponent = (id: string) => model.composants.some((c) => c.id === id && c.bloc === block?.id);
  // The journeys that go through this box, and their first step here.
  const through = new Map<string, number>();
  for (const journey of model.parcours)
    journey.etapes.forEach((step, index) => {
      const here = component
        ? step.composant === component.id
        : block !== undefined && (step.touche.includes(block.id) || ownComponent(step.composant));
      if (here && !through.has(journey.id)) through.set(journey.id, index + 1);
    });
  const incoming = block ? model.flux.filter((f) => f.vers === block.id) : [];
  const outgoing = block ? model.flux.filter((f) => f.de === block.id) : [];
  const name = (id: string) => model.blocs.find((b) => b.id === id)?.nom ?? id;
  const entre = block?.entre?.length ? block.entre : incoming.map((f) => `${name(f.de)} : ${f.quoi}`);
  const sort = block?.sort?.length ? block.sort : outgoing.map((f) => `vers ${name(f.vers)} : ${f.quoi}`);
  const files = component?.fichiers ?? block?.code.map((c) => c.chemin).filter(Boolean) ?? [];

  return (
    <Panel>
      <p className="text-[13px] font-semibold text-faint">{box.kind}</p>
      <h2 className="mt-1 text-[22px] leading-tight font-semibold">{box.title}</h2>
      <p className="mt-2 text-[16px] leading-relaxed">{box.words}</p>
      {box.inside > 0 && (
        <button
          type="button"
          onClick={() => onEnter(box)}
          className="mt-4 flex items-center gap-1.5 rounded-lg bg-ink px-4 py-2 text-[15px] font-medium text-bg hover:opacity-90"
        >
          Entrer dedans <ChevronRight size={16} aria-hidden="true" />
        </button>
      )}
      {entre.length > 0 && <List title="Ce qui entre" items={entre} />}
      {sort.length > 0 && <List title="Ce qui sort" items={sort} />}
      {through.size > 0 && <Journeys model={model} onPlay={onPlay} only={through} />}
      {files.length > 0 && <Files title="Pour la modifier : ses fichiers" paths={files} />}
      {(block || component) && (
        <details className="mt-7 border-t border-line-soft pt-3 text-[14px]">
          <summary className="cursor-pointer text-muted hover:text-ink">Détails pour développeur</summary>
          <div className="mt-3 space-y-3 text-muted">
            <p className="leading-relaxed">{block?.role ?? component?.role}</p>
            {block?.techno && <p>Technologies : {block.techno}</p>}
            {component?.expose.map((item, index) => (
              <div key={index}>
                {item.quoi}
                <CitedCode projectId={projectId} cited={item} />
              </div>
            ))}
          </div>
        </details>
      )}
    </Panel>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="mt-6">
      <h3 className="text-[15px] font-semibold">{title}</h3>
      <ul className="mt-1.5 list-disc space-y-1 pl-5 text-[15px] leading-relaxed text-muted">
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function Files({ title, paths }: { title: string; paths: string[] }) {
  return (
    <section className="mt-6">
      <h3 className="text-[15px] font-semibold">{title}</h3>
      <ul className="mt-1.5 space-y-1 font-mono text-[13px] break-all text-muted">
        {paths.map((path) => (
          <li key={path}>{path}</li>
        ))}
      </ul>
    </section>
  );
}

const otherCases = (n: number) => (n === 1 ? "1 cas particulier" : `${n} cas particuliers`);

function StepInfo({ projectId, journey, number, onStep }: {
  projectId: string; journey: Journey; number: number; onStep: (n: number) => void;
}) {
  const current = journey.etapes[number - 1];
  if (!current) return null;
  // The sentence of the step is in the bar under the map; here: where it sits in the whole path.
  return (
    <Panel>
      <p className="text-[13px] font-semibold text-faint">Chemin de données</p>
      <h2 className="mt-1 text-[20px] leading-snug font-semibold">{journey.nom}</h2>
      <p className="mt-2 text-[14.5px] leading-relaxed text-muted">
        <span className="font-medium text-ink">Point de départ : </span>
        {journey.depart || journey.declencheur}
      </p>
      <ol className="mt-5 flex flex-col gap-1">
        {journey.etapes.map((step, index) => {
          const on = index + 1 === number;
          return (
            <li key={index}>
              <button
                type="button"
                onClick={() => onStep(index + 1)}
                aria-current={on ? "step" : undefined}
                className={`flex w-full items-center gap-3 rounded-lg px-2.5 py-1.5 text-left text-[15px] ${on ? "bg-lamp-soft font-semibold" : "text-muted hover:bg-raised"}`}
              >
                <span className={`flex size-6 shrink-0 items-center justify-center rounded-full text-[12.5px] font-bold ${on ? "bg-lamp text-on-lamp" : "border border-line"}`}>
                  {index + 1}
                </span>
                {stepLabel(step)}
                {step.manuel && (
                  <span className="ml-auto shrink-0 text-[12px] font-normal text-ok" title="Fait par une personne (un clic, une commande), pas par le programme">
                    par une personne
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ol>
      {(journey.fin || journey.resultat) && (
        <section className="mt-5 rounded-xl bg-raised px-4 py-3">
          <p className="text-[13px] font-semibold text-lamp-ink">À la fin</p>
          <p className="mt-1 text-[15px] leading-relaxed">{journey.fin || journey.resultat}</p>
        </section>
      )}
      {(journey.branches ?? []).length > 0 && (
        <section className="mt-6">
          <h3 className="text-[15px] font-semibold">Quand ça ne se passe pas comme prévu (sur tout le chemin)</h3>
          <ul className="mt-2 space-y-2.5">
            {(journey.branches ?? []).map((branch, index) => (
              <li key={index} className="rounded-lg border border-line-soft px-3.5 py-2.5 text-[14.5px] leading-relaxed">
                <span className="font-medium">Si {lowerFirst(branch.quand)}</span>
                <span className="block text-muted">{branch.alors}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
      {current.fichier && <Files title={`Pour changer l'étape ${number}`} paths={[current.fichier]} />}
      <details className="mt-6 border-t border-line-soft pt-3 text-[14px]">
        <summary className="cursor-pointer text-muted hover:text-ink">Détails pour développeur (étape {number})</summary>
        <div className="mt-3 space-y-2 text-muted">
          {(current.conditions ?? []).length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {(current.conditions ?? []).map((condition) => (
                <Tag key={condition} tone="condition">
                  {condition.replace(/^seulement si\s*/i, "")}
                </Tag>
              ))}
            </div>
          )}
          <p className="leading-relaxed">{current.texte}</p>
          <CitedCode key={number} projectId={projectId} cited={current} />
        </div>
      </details>
    </Panel>
  );
}

/** « Le serveur… », « L'en-tête… » → « le serveur… », « l'en-tête… »; a name (« WeasyPrint », « API ») keeps its capitals. */
function lowerFirst(text: string): string {
  const word = text.split(/[\s'’]/)[0] ?? "";
  return /[A-Z]/.test(word.slice(1)) ? text : text.charAt(0).toLowerCase() + text.slice(1);
}
