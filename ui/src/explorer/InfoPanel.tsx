import { ChevronRight, Play } from "lucide-react";
import type { ReactNode } from "react";
import type { Journey, ProjectModel } from "../api";
import { CitedCode } from "../arch/CitedCode";
import { lowerFirst, stepLabel } from "../arch/story";
import { steps, Tag } from "../ui";
import type { Box, Level } from "./levels";
import { stepRuns } from "./room";

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
  if (level.room) return <RoomInfo model={model} level={level} onPlay={onPlay} />;
  return (
    <Panel>
      <p className="text-[13px] font-semibold text-faint">Vous êtes ici</p>
      <h2 className="mt-1 text-[22px] leading-tight font-semibold">{level.title}</h2>
      <p className="mt-2 text-[15px] leading-relaxed text-muted">{level.hint}</p>
      {level.floor && level.floor.stripLinks.length > 0 && (
        <p className="mt-4 text-[14px] leading-relaxed text-muted">
          Autour du projet :{" "}
          {level.floor.stripLinks.map((l) => `${model.blocs.find((b) => b.id === l.from)?.nom ?? l.from} ${l.verb || "→"} ${model.blocs.find((b) => b.id === l.to)?.nom ?? l.to}`).join(" ; ")}.
        </p>
      )}
      <Journeys model={model} onPlay={onPlay} />
      <p className="mt-6 text-[13.5px] leading-relaxed text-faint">
        Cliquez une pièce pour savoir ce qu'elle fait. « Entrer » montre ce qu'elle contient, jusqu'au code.
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

function RoomInfo({ model, level, onPlay }: { model: ProjectModel; level: Level; onPlay: (id: string, step: number) => void }) {
  const room = level.room!;
  const block = model.blocs.find((b) => b.id === room.bloc);
  // The journey whose step numbers the machines show comes first, and says so.
  const through = model.parcours
    .filter((j) => stepRuns(model, j).some((r) => r.bloc === room.bloc))
    .sort((a, b) => Number(b === room.journey) - Number(a === room.journey));
  return (
    <Panel>
      <p className="text-[13px] font-semibold text-faint">Vous êtes dans la pièce</p>
      <h2 className="mt-1 text-[22px] leading-tight font-semibold">{level.title}</h2>
      <p className="mt-2 text-[15px] leading-relaxed text-muted">{block?.en_bref || block?.role}</p>
      {through.map((journey, index) => (
        <section key={journey.id} className="mt-6">
          {index === 0 && journey === room.journey && <p className="mb-1 text-[12.5px] text-faint">Les numéros sur les machines suivent ce parcours.</p>}
          {index === 1 && <p className="mb-1 text-[12.5px] font-semibold text-faint">Passent aussi par ici</p>}
          <button type="button" onClick={() => onPlay(journey.id, 1)} className="flex items-center gap-2 text-left text-[15px] font-semibold hover:underline">
            <Play size={15} className="shrink-0 text-lamp-ink" aria-hidden="true" />
            {journey.nom}
          </button>
          <ol className="mt-2 space-y-2.5">
            {stepRuns(model, journey).map((run) => (
              <li key={`${run.from}`} className={run.bloc === room.bloc ? "" : "opacity-70"}>
                <p className="text-[12.5px] font-semibold text-faint">{run.title.startsWith("Retour") ? run.title : `Dans « ${run.title} »`}</p>
                <ul className="mt-0.5 space-y-0.5 text-[14px]">
                  {journey.etapes.slice(run.from - 1, run.to).map((step, k) => (
                    <li key={k}>
                      <button type="button" onClick={() => onPlay(journey.id, run.from + k)} className="text-left hover:underline">
                        <span className="mr-1.5 text-faint">{run.from + k}.</span>
                        {stepLabel(step)}
                      </button>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
        </section>
      ))}
      {(room.unplaced.length > 0 || room.elsewhere.length > 0) && (
        <section className="mt-7">
          <h3 className="text-[15px] font-semibold">Autres cas particuliers</h3>
          <ul className="mt-2 space-y-2 text-[14px]">
            {[...room.unplaced, ...room.elsewhere].map((branch, k) => (
              <li key={k} className="rounded-lg border border-line-soft px-3 py-2">
                <span className="font-medium">Si {branch.quand_simple || branch.quand}</span>
                <span className="block text-muted">{branch.alors_simple || branch.alors}</span>
                <span className="block text-[12.5px] text-faint">
                  {model.parcours.find((j) => j.id === branch.journey)?.nom}
                  {room.unplaced.includes(branch as (typeof room.unplaced)[number]) ? " · aucune machine seule ne le porte" : ""}
                </span>
              </li>
            ))}
          </ul>
        </section>
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
        : block !== undefined && (step.touche.includes(block.id) || (step.composant !== null && ownComponent(step.composant)));
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
