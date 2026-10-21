import { ArrowLeft, ArrowRight } from "lucide-react";
import type { ReactNode } from "react";
import type { ArchBlock, Project, ProjectModel } from "../api";
import { navigate } from "../route";
import { CitedCode } from "./CitedCode";
import { BLOCK_LABEL } from "./BlockNode";
import { journeysOf } from "./story";

interface Props {
  project: Project;
  model: ProjectModel;
  block: ArchBlock;
  onBack: () => void;
  onJourney: (id: string, step: number) => void;
  onBlock: (id: string) => void;
}

/** One part of the project: what it is for, the stories it takes part in, who it works with; then details. */
export function BlockPage({ project, model, block, onBack, onJourney, onBlock }: Props) {
  const name = (id: string) => model.blocs.find((b) => b.id === id)?.nom ?? id;
  const stories = journeysOf(model, block);
  const outgoing = model.flux.filter((flow) => flow.de === block.id);
  const incoming = model.flux.filter((flow) => flow.vers === block.id);
  const components = model.composants.filter((component) => component.bloc === block.id);

  return (
    <div className="h-full overflow-y-auto">
      <article className="mx-auto max-w-[760px] px-6 pt-8 pb-24">
        <button type="button" onClick={onBack} className="flex items-center gap-1.5 text-[15px] text-muted hover:text-ink">
          <ArrowLeft size={16} aria-hidden="true" /> Accueil du projet
        </button>
        <p className="mt-6 text-[14px] text-faint">
          {BLOCK_LABEL[block.type]}
          {block.importance === "ancien" && " · ancien, en cours de remplacement"}
        </p>
        <h1 className="mt-1 text-[28px] leading-tight font-semibold tracking-[-0.01em]">{block.nom}</h1>
        <p className="mt-3 text-[19px] leading-relaxed">{block.en_bref || block.role}</p>

        {stories.length > 0 && (
          <section className="mt-10">
            <h2 className="text-[20px] font-semibold">Les histoires où elle joue</h2>
            <ul className="mt-3 flex flex-col gap-2">
              {stories.map(({ journey, steps }) => (
                <li key={journey.id}>
                  <button
                    type="button"
                    onClick={() => onJourney(journey.id, steps[0] ?? 1)}
                    className="w-full rounded-xl border border-line bg-panel px-5 py-3 text-left hover:border-lamp-line"
                  >
                    <span className="block text-[16px] font-semibold">{journey.nom}</span>
                    <span className="block text-[14px] text-muted">
                      {steps.length === 1 ? `À l'étape ${steps[0]}` : `Aux étapes ${steps.join(", ")}`}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {outgoing.length + incoming.length > 0 && (
          <section className="mt-10">
            <h2 className="text-[20px] font-semibold">Avec qui elle travaille</h2>
            <ul className="mt-3 flex flex-col gap-2 text-[16px] leading-relaxed">
              {[...outgoing, ...incoming].map((flow) => (
                <li key={`${flow.de}>${flow.vers}`}>
                  <FlowSentence
                    from={flow.de === block.id ? <b>{block.nom}</b> : <PartLink name={name(flow.de)} onClick={() => onBlock(flow.de)} />}
                    to={flow.vers === block.id ? <b>{block.nom}</b> : <PartLink name={name(flow.vers)} onClick={() => onBlock(flow.vers)} />}
                    verb={flow.verbe}
                    what={flow.quoi}
                  />
                </li>
              ))}
            </ul>
          </section>
        )}

        <details className="mt-12 border-t border-line-soft pt-4">
          <summary className="cursor-pointer text-[15px] text-muted hover:text-ink">Détails pour développeur</summary>
          <div className="mt-4 space-y-5 text-[15px]">
            {block.en_bref && <p className="leading-relaxed text-muted">{block.role}</p>}
            {block.techno && (
              <p>
                <span className="text-faint">Technologies : </span>
                {block.techno}
              </p>
            )}
            {components.map((component) => (
              <section key={component.id}>
                <p className="font-semibold">{component.nom}</p>
                <p className="text-muted">{component.role}</p>
                {component.expose.map((item, index) => (
                  <div key={index} className="mt-1 text-[14px] text-muted">
                    {item.quoi}
                    <CitedCode projectId={project.id} cited={item} />
                  </div>
                ))}
              </section>
            ))}
            {block.code.length > 0 && (
              <ul className="space-y-1">
                {block.code.map((code) => (
                  <li key={code.chemin}>
                    <button
                      type="button"
                      className="font-mono text-[13.5px] underline decoration-line underline-offset-[3px] hover:decoration-ink"
                      onClick={() => navigate({ projectId: project.id, node: code.element, expand: false })}
                    >
                      {code.chemin}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {block.indices && <p className="text-muted">{block.indices}</p>}
          </div>
        </details>
      </article>
    </div>
  );
}

function PartLink({ name, onClick }: { name: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="font-medium underline decoration-line underline-offset-[3px] hover:decoration-ink">
      {name}
    </button>
  );
}

/** « Application web envoie les demandes à Moteur local », or with no verb « A → B : what goes through ». */
function FlowSentence({ from, to, verb, what }: { from: ReactNode; to: ReactNode; verb?: string; what: string }) {
  if (verb)
    return (
      <span>
        {from} <span className="text-muted">{verb}</span> {to}
      </span>
    );
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      {from}
      <ArrowRight size={15} className="text-lamp-ink" aria-label="vers" />
      {to}
      <span className="text-muted">: {what}</span>
    </span>
  );
}
