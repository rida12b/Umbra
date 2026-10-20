import type { ArchBlock, ArchFlow, Project, ProjectModel } from "../api";
import { navigate } from "../route";
import { Button, SectionTitle } from "../ui";
import { BLOCK_LABEL } from "./BlockNode";
import { CitedCode } from "./CitedCode";
import { ModelStatusLine } from "./ModelStatus";

// What the right-hand panel of the architecture shows when no journey step is in focus.

export function Overview({ model, onJourney }: { model: ProjectModel; onJourney: (id: string) => void }) {
  return (
    <div className="px-6 pt-5 pb-10">
      <h1 className="text-[20px] font-semibold tracking-[-0.01em]">Ce que fait ce projet</h1>
      {model.pitch && <p className="mt-2.5 text-[16px] leading-relaxed text-ink">{model.pitch}</p>}
      {model.pitch ? (
        <details className="mt-3 text-[14px]">
          <summary className="cursor-pointer text-muted hover:text-ink">En détail</summary>
          <p className="mt-2 leading-relaxed text-muted">{model.resume}</p>
        </details>
      ) : (
        <p className="mt-2.5 text-[14px] leading-relaxed text-muted">{model.resume}</p>
      )}
      {model.parcours.length > 0 && (
        <>
          <SectionTitle>Suivre un parcours sur la carte</SectionTitle>
          <ul className="flex flex-col gap-1">
            {model.parcours.map((journey) => (
              <li key={journey.id}>
                <Button variant="link" onClick={() => onJourney(journey.id)}>
                  {journey.nom}
                </Button>
                <span className="text-[12.5px] text-faint"> — {journey.etapes.length} étapes</span>
              </li>
            ))}
          </ul>
        </>
      )}
      {model.incertitudes.length > 0 && (
        <>
          <SectionTitle>Ce qu'on ne peut pas savoir d'ici</SectionTitle>
          <ul className="list-disc space-y-1.5 pl-5 text-[13px] text-muted">
            {model.incertitudes.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </>
      )}
      <ModelStatusLine />
    </div>
  );
}

export function BlockDetails({ block, model, project, onBack }: {
  block: ArchBlock; model: ProjectModel; project: Project; onBack: () => void;
}) {
  const components = model.composants.filter((component) => component.bloc === block.id);
  return (
    <div className="px-6 pt-4 pb-10">
      <Button variant="link" className="text-[13px] text-muted" onClick={onBack}>
        Retour
      </Button>
      <p className="mt-4 text-[12px] text-faint">{BLOCK_LABEL[block.type]}</p>
      <h1 className="text-[19px] font-semibold tracking-[-0.01em]">{block.nom}</h1>
      <p className="mt-2 text-[14px] text-muted">{block.role}</p>
      {block.techno && <p className="mt-1 text-[12.5px] text-faint">{block.techno}</p>}
      {components.length > 0 && <SectionTitle>Ses composants</SectionTitle>}
      {components.map((component) => (
        <section key={component.id} className="border-t border-line-soft py-2.5">
          <p className="text-[13.5px] font-medium">{component.nom}</p>
          <p className="text-[13px] text-muted">{component.role}</p>
          {component.expose.length > 0 && (
            <ul className="mt-1.5 space-y-1 text-[13px] text-muted">
              {component.expose.map((item, index) => (
                <li key={index}>
                  {item.quoi}
                  <CitedCode projectId={project.id} cited={item} />
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}
      <SectionTitle>Son code</SectionTitle>
      {block.code.length === 0 ? (
        <p className="text-[13px] text-muted">Pas de code dans ce projet : c'est un élément extérieur (personne, service, base).</p>
      ) : (
        <ul className="space-y-1">
          {block.code.map((code) => (
            <li key={code.chemin}>
              <button
                type="button"
                className="font-mono text-[12.5px] text-ink underline decoration-line underline-offset-[3px] hover:decoration-ink"
                onClick={() => navigate({ projectId: project.id, node: code.element, expand: false })}
              >
                {code.chemin}
              </button>
            </li>
          ))}
        </ul>
      )}
      {block.indices && (
        <>
          <SectionTitle>Pourquoi on le pense</SectionTitle>
          <p className="text-[13px] text-muted">{block.indices}</p>
        </>
      )}
    </div>
  );
}

export function FlowDetails({ flow, model, onBack }: { flow: ArchFlow; model: ProjectModel; onBack: () => void }) {
  const name = (id: string) => model.blocs.find((block) => block.id === id)?.nom ?? id;
  return (
    <div className="px-6 pt-4 pb-10">
      <Button variant="link" className="text-[13px] text-muted" onClick={onBack}>
        Retour
      </Button>
      <p className="mt-4 text-[12px] text-faint">Flux</p>
      <h1 className="text-[19px] font-semibold tracking-[-0.01em]">
        De « {name(flow.de)} » vers « {name(flow.vers)} »
      </h1>
      <p className="mt-2 text-[14px] text-muted">{flow.quoi}</p>
    </div>
  );
}
