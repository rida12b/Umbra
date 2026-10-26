import { ChevronRight, Play } from "lucide-react";
import { useLayoutEffect, useRef, type ReactNode } from "react";
import type { Branch, Journey, ProjectModel } from "../api";
import { CitedCode } from "../arch/CitedCode";
import { lowerFirst, stepLabel } from "../arch/story";
import { steps, Tag } from "../ui";
import type { Box, Level } from "./levels";
import type { Floor } from "./floor";
import { mainJourney } from "./floor";
import { buildRoom, stepRuns } from "./room";
import { stepGroups } from "./stations";

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
  // In a room, its own journey keeps the room's step cards, the step played framed in yellow (V53).
  if (playing && level.room && level.room.journey?.id === playing.journey.id)
    return <RoomInfo projectId={projectId} model={model} level={level} onPlay={onPlay} active={playing.step} />;
  if (playing) return <StepInfo projectId={projectId} model={model} journey={playing.journey} number={playing.step} onStep={onStep} />;
  if (level.room) return <RoomInfo projectId={projectId} model={model} level={level} onPlay={onPlay} />;
  if (level.floor) return <FloorInfo model={model} level={level} floor={level.floor} onEnter={onEnter} onPlay={onPlay} />;
  return (
    <Panel>
      <p className="text-[13px] font-semibold text-faint">Vous êtes ici</p>
      <h2 className="mt-1 text-[22px] leading-tight font-semibold">{level.title}</h2>
      <p className="mt-2 text-[15px] leading-relaxed text-muted">{level.hint}</p>
      <Journeys model={model} onPlay={onPlay} />
      <Doubts model={model} />
    </Panel>
  );
}

/** The panel of the factory floor (V19-V24): the belt's journey first, then the rooms, then the other journeys. */
function FloorInfo({ model, level, floor, onEnter, onPlay }: {
  model: ProjectModel; level: Level; floor: Floor; onEnter: (box: Box) => void; onPlay: (id: string, step: number) => void;
}) {
  const main = floor.journey;
  const others = model.parcours.filter((j) => j !== main);
  const blocOf = (id: string | null) => (id ? (model.composants.find((c) => c.id === id)?.bloc ?? id) : null);
  const rooms = floor.items.filter((i) => i.role === "belt" || i.role === "orphan");
  const data = model.donnee?.[0]?.nom;
  return (
    <Panel>
      <p className="text-[12px] text-faint">Vous êtes ici</p>
      <h2 className="mt-1 text-[20px] leading-tight font-bold">L'usine (vue d'ensemble)</h2>
      <p className="mt-2 text-[13px] leading-relaxed text-muted">
        Les grandes pièces du projet, posées sur le tapis qui suit la donnée : elle entre à gauche, ressort à droite. Pour voir l'intérieur d'une pièce,
        cliquez sur « Entrer ».
      </p>
      {main && (
        <section className="mt-6">
          <h3 className="text-[14px] font-bold">Le trajet sur le tapis</h3>
          <div className="mt-2 rounded-lg border border-line-soft px-3 py-2.5 text-[13px]">
            <p className="text-[14px] leading-snug font-bold">{main.nom}</p>
            {main.depart && (
              <p className="mt-1 text-muted">
                <strong className="text-fl-data">Départ : </strong>
                {main.depart}
              </p>
            )}
            {main.fin && (
              <p className="text-muted">
                <strong className="text-fl-data">Arrivée : </strong>
                {main.fin}
              </p>
            )}
            <p className="mt-1 text-[12px] text-faint">
              {steps(main.etapes.length)}
              {main.branches?.length ? ` · ${otherCases(main.branches.length)}` : ""}
            </p>
            <button
              type="button"
              onClick={() => onPlay(main.id, 1)}
              aria-label={`Suivre le trajet : ${main.nom}`}
              className="mt-2.5 inline-flex items-center gap-2 rounded-md border border-fl-data bg-fl-data/15 px-3 py-1.5 text-[13px] font-bold text-ink hover:bg-fl-data/25"
            >
              <Play size={13} className="fill-fl-data text-fl-data" aria-hidden="true" />
              {data ? `Suivre « ${data} »` : "Suivre ce trajet"}
            </button>
            <p className="mt-2 text-[11px] leading-snug text-faint">
              {main.principal_deduit || !main.principal
                ? "Choisi car il passe par le plus de pièces : le modèle ne dit pas lequel est le trajet principal."
                : "Le modèle le donne comme trajet principal."}
            </p>
          </div>
        </section>
      )}
      {rooms.length > 0 && (
        <section className="mt-6">
          <h3 className="text-[14px] font-bold">Les pièces</h3>
          <ul className="mt-2 flex flex-col gap-2">
            {rooms.map((item) => {
              const box = level.boxes.find((b) => b.id === item.id);
              const block = model.blocs.find((b) => b.id === item.id);
              if (!box || !block) return null;
              const room = buildRoom(model, item.id);
              const machines = room ? room.belt.length + room.band.length : 0;
              const here = (main?.etapes ?? []).filter((s) => blocOf(s.composant) === item.id).length;
              return (
                <li key={item.id} className="rounded-lg border border-line-soft px-3 py-2.5 text-[13px]">
                  <p className="text-[14px] font-bold">{block.nom}</p>
                  <p className="text-muted">{block.en_bref || block.role}</p>
                  <p className="mt-1 flex items-end justify-between gap-2 text-[12px] text-faint">
                    <span>{[machines ? `${machines} machine${machines > 1 ? "s" : ""}` : "", here ? `${here} étape${here > 1 ? "s" : ""} ici` : ""].filter(Boolean).join(" · ")}</span>
                    {box.inside > 0 && (
                      <button type="button" onClick={() => onEnter(box)} className="shrink-0 text-[13px] text-fl-service hover:underline">
                        Entrer ›
                      </button>
                    )}
                  </p>
                </li>
              );
            })}
          </ul>
        </section>
      )}
      {others.length > 0 && (
        <section className="mt-6">
          <h3 className="text-[14px] font-bold">
            Autres trajets <span className="text-[11.5px] font-normal text-faint">(un seul trajet à la fois sur le tapis)</span>
          </h3>
          <ul className="mt-2 flex flex-col gap-2">
            {others.map((journey) => (
              <li key={journey.id}>
                <details className="rounded-lg border border-line-soft px-3 py-2.5 text-[13px]">
                  <summary className="cursor-pointer">
                    <span className="text-[14px] font-bold">{journey.nom}</span>
                    {/* Shown while folded, as in the mockup (V24). */}
                    <span className="mt-1 line-clamp-2 block text-muted">{journey.depart || journey.declencheur}</span>
                  </summary>
                  <button type="button" onClick={() => onPlay(journey.id, 1)} aria-label={`Suivre le trajet : ${journey.nom}`} className="mt-1.5 inline-flex items-center gap-1.5 text-[13px] text-fl-data hover:underline">
                    <Play size={12} aria-hidden="true" /> Suivre ce trajet ({steps(journey.etapes.length)})
                  </button>
                </details>
              </li>
            ))}
          </ul>
        </section>
      )}
      <Doubts model={model} />
    </Panel>
  );
}

function Doubts({ model }: { model: ProjectModel }) {
  if (model.incertitudes.length === 0) return null;
  return (
    <details className="mt-6 text-[13px]">
      <summary className="cursor-pointer text-muted hover:text-ink">Ce que Claude n'a pas pu vérifier ({model.incertitudes.length})</summary>
      <ul className="mt-2 list-disc space-y-1.5 pl-5 text-muted">
        {model.incertitudes.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </details>
  );
}

/** The panel of an open room (V40, V44-V46): the driving journey's steps grouped by room, each refusal after the step that handles it. */
function RoomInfo({ projectId, model, level, onPlay, active = null }: {
  projectId: string; model: ProjectModel; level: Level; onPlay: (id: string, step: number) => void; active?: number | null;
}) {
  const room = level.room!;
  const block = model.blocs.find((b) => b.id === room.bloc);
  // The step played is kept in view inside the side panel only: on a phone the panel is under the list, and
  // scrolling the page to it would push the lit machine off the screen.
  const top = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const side = top.current?.closest("aside");
    const card = side?.querySelector<HTMLElement>('[aria-current="step"]');
    if (!side || !card) return;
    const [s, c] = [side.getBoundingClientRect(), card.getBoundingClientRect()];
    if (c.top < s.top) side.scrollTop += c.top - s.top - 12;
    else if (c.bottom > s.bottom) side.scrollTop += c.bottom - s.bottom + 12;
  }, [active]);
  const journey = room.journey;
  const others = model.parcours.filter((j) => j !== journey && stepRuns(model, j).some((r) => r.bloc === room.bloc));
  const branchesAt = (n: number) => (journey?.branches ?? []).filter((b) => b.etape === n);
  const loose = (journey?.branches ?? []).filter((b) => !b.etape || b.etape < 1 || b.etape > (journey?.etapes.length ?? 0));
  return (
    <Panel>
      <div ref={top} className="text-[12px] text-faint">Vous êtes dans la pièce</div>
      <h2 className="mt-1 text-[20px] leading-tight font-bold">{level.title}</h2>
      <p className="mt-1.5 text-[13px] leading-relaxed text-muted">{block?.en_bref || block?.role}</p>
      {journey && (
        <section className="mt-5">
          <button type="button" onClick={() => onPlay(journey.id, 1)} className="flex items-center gap-2 text-left text-[14px] font-bold hover:underline">
            <Play size={14} className="shrink-0 fill-fl-data text-fl-data" aria-hidden="true" />
            {journey.nom}
          </button>
          <p className="mt-0.5 text-[12px] text-faint">Les numéros sur les machines suivent ce trajet.</p>
          {active !== null && <Ends journey={journey} at="start" />}
          {stepRuns(model, journey).map((run) => (
            <div key={run.from} className={run.bloc === room.bloc ? "" : "opacity-75"}>
              <p className="mt-4 mb-1.5 text-[11px] font-semibold tracking-wide text-faint uppercase">{run.title.startsWith("Retour") || run.title.startsWith("Fait") ? run.title : `Dans « ${run.title} »`}</p>
              <ol className="flex flex-col gap-2">
                {journey.etapes.slice(run.from - 1, run.to).map((step, k) => {
                  const n = run.from + k;
                  return (
                    <li key={n}>
                      <div className={`rounded-lg border px-3 py-2 text-[13px] ${n === active ? "border-2 border-fl-hl" : "border-line-soft"}`} aria-current={n === active ? "step" : undefined}>
                        <button type="button" onClick={() => onPlay(journey.id, n)} className="flex items-start gap-2 text-left hover:underline">
                          <span className="fl-num mt-0.5">{n}</span>
                          <span className="font-bold leading-snug">{stepLabel(step)}</span>
                        </button>
                        <p className="mt-1 leading-snug text-muted">{step.simple || step.texte}</p>
                        <CitedCode projectId={projectId} cited={step} />
                      </div>
                      {branchesAt(n).map((branch, b) => (
                        <IfThen key={b} projectId={projectId} branch={branch} />
                      ))}
                    </li>
                  );
                })}
              </ol>
            </div>
          ))}
          {loose.map((branch, b) => (
            <IfThen key={`loose-${b}`} projectId={projectId} branch={branch} />
          ))}
          {active !== null && <Ends journey={journey} at="end" />}
        </section>
      )}
      {others.length > 0 && (
        <section className="mt-6">
          <h3 className="text-[14px] font-bold">Passent aussi par ici</h3>
          <ul className="mt-2 flex flex-col gap-1.5">
            {others.map((j) => (
              <li key={j.id}>
                <button type="button" onClick={() => onPlay(j.id, 1)} className="flex items-center gap-2 text-left text-[13px] hover:underline">
                  <Play size={12} className="shrink-0 text-fl-data" aria-hidden="true" />
                  {j.nom} <span className="text-faint">· {steps(j.etapes.length)}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </Panel>
  );
}

/** Where a journey starts and ends (V64): two framed cards around its steps, « ▶ Départ » and « ■ Arrivée ». */
function Ends({ journey, at }: { journey: Journey; at: "start" | "end" }) {
  const words = at === "start" ? journey.depart || journey.declencheur : journey.fin || journey.resultat;
  if (!words) return null;
  return (
    <p className={`rounded-lg border border-line-soft px-3 py-2 text-[13.5px] leading-relaxed text-muted ${at === "start" ? "mt-3" : "mt-4"}`}>
      <strong className={at === "start" ? "text-fl-data" : "text-fl-store"}>{at === "start" ? "▶ Départ" : "■ Arrivée"}</strong> — {words}
    </p>
  );
}

/** A special case, as in the mockup (V46): no frame, a red bar on the left, « Si … alors … ». */
function IfThen({ projectId, branch }: { projectId: string; branch: Branch }) {
  const technical = !branch.quand_simple;
  return (
    <div className="my-2 border-l-[3px] border-fl-refus py-0.5 pl-3 text-[12.5px] leading-snug text-muted">
      <p>
        <strong className="text-ink">Si</strong> {lowerFirst(branch.quand_simple || branch.quand)}
      </p>
      <p>
        <strong className="text-ink">alors</strong> {lowerFirst(branch.alors_simple || branch.alors)} {technical && <span className="fl-tech">texte du modèle, technique</span>}
      </p>
      <CitedCode projectId={projectId} cited={branch} />
    </div>
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

function StepInfo({ projectId, model, journey, number, onStep }: {
  projectId: string; model: ProjectModel; journey: Journey; number: number; onStep: (n: number) => void;
}) {
  const current = journey.etapes[number - 1];
  if (!current) return null;
  const main = mainJourney(model).journey === journey;
  const machineOf = (id: string | null) => (id ? (model.composants.find((c) => c.id === id)?.nom ?? model.blocs.find((b) => b.id === id)?.nom ?? null) : null);
  // A long journey is cut into its phases (or its rooms): the reader sees where the data is, not 16 lines.
  const groups = stepGroups(model, journey) ?? [{ title: "", from: 1, to: journey.etapes.length }];
  const branchesAt = (n: number) => (journey.branches ?? []).filter((b) => b.etape === n);
  const loose = (journey.branches ?? []).filter((b) => !b.etape || b.etape < 1 || b.etape > journey.etapes.length);
  // The sentence of the step is in the bar under the map; here: where it sits in the whole path.
  return (
    <Panel>
      <p className="flex items-center gap-2 text-[13px] font-semibold text-faint">
        Chemin de données
        {main && <span className="rounded-full bg-fl-hl px-2 py-px text-[11px] font-bold text-[#1b1e24]">principal</span>}
      </p>
      <h2 className="mt-1 text-[20px] leading-snug font-semibold">{journey.nom}</h2>
      {/* V64: where it starts, every step with its machine, where it ends. */}
      <Ends journey={journey} at="start" />
      {groups.map((group) => (
        <section key={group.from}>
          {group.title && <p className="mt-4 mb-1 text-[11px] font-semibold tracking-wide text-faint uppercase">{group.title}</p>}
          <ol className={`flex flex-col gap-1 ${group.title ? "" : "mt-4"}`} start={group.from}>
            {journey.etapes.slice(group.from - 1, group.to).map((step, k) => {
              const n = group.from + k;
              const on = n === number;
              return (
                <li key={n}>
                  <button
                    type="button"
                    onClick={() => onStep(n)}
                    aria-current={on ? "step" : undefined}
                    className={`flex w-full items-center gap-3 rounded-lg px-2.5 py-1.5 text-left text-[15px] ${on ? "bg-lamp-soft font-semibold ring-2 ring-fl-hl" : "text-muted hover:bg-raised"}`}
                  >
                    <span className={`flex size-6 shrink-0 items-center justify-center rounded-full text-[12.5px] font-bold ${on ? "bg-lamp text-on-lamp" : "border border-line"}`}>{n}</span>
                    <span className="min-w-0">
                      {stepLabel(step)}
                      {machineOf(step.composant) && <span className="block text-[12.5px] font-normal text-faint">{machineOf(step.composant)}</span>}
                    </span>
                    {step.manuel && (
                      <span className="ml-auto shrink-0 text-[12px] font-normal text-ok" title="Fait par une personne (un clic, une commande), pas par le programme">
                        par une personne
                      </span>
                    )}
                  </button>
                  {branchesAt(n).map((branch, b) => (
                    <div key={b} className="ml-9">
                      <IfThen projectId={projectId} branch={branch} />
                    </div>
                  ))}
                </li>
              );
            })}
          </ol>
        </section>
      ))}
      <Ends journey={journey} at="end" />
      {loose.length > 0 && (
        <section className="mt-6">
          <h3 className="text-[15px] font-semibold">Quand ça ne se passe pas comme prévu (sur tout le chemin)</h3>
          {loose.map((branch, index) => (
            <IfThen key={index} projectId={projectId} branch={branch} />
          ))}
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
