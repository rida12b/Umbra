import { ArrowRight } from "lucide-react";
import { useMemo } from "react";
import type { Project, ProjectModel } from "../api";
import { MAP_VIEW, navigate } from "../route";
import type { Theme } from "../theme";
import { ArchCanvas } from "./ArchCanvas";
import { BLOCK_LABEL } from "./BlockNode";
import { steps } from "../ui";
import { ModelStatusLine } from "./ModelStatus";

const MAX_CORE = 7; // C4 context level: a handful of parts, read at a glance

interface Props {
  project: Project;
  model: ProjectModel;
  theme: Theme;
  narrow: boolean;
  onJourney: (id: string) => void;
  onBlock: (id: string) => void;
}

/** What the project does, its main parts at a readable size, then the stories of how it works. */
export function HomePage({ project, model, theme, narrow, onJourney, onBlock }: Props) {
  const core = useMemo(() => {
    const linked = new Set(model.flux.flatMap((flow) => [flow.de, flow.vers]));
    return model.blocs.filter((b) => (b.importance ?? "coeur") === "coeur" && linked.has(b.id)).slice(0, MAX_CORE);
  }, [model]);
  const others = model.blocs.length - core.length;

  return (
    <div className="h-full overflow-y-auto">
      <article className="mx-auto max-w-[1640px] px-8 pt-10 pb-24">
        <p className="text-[14px] font-medium text-faint">{project.name}</p>
        <h1 className="mt-1 text-[28px] leading-tight font-semibold tracking-[-0.01em]">Ce que fait ce projet</h1>
        <p className="mt-4 max-w-[68ch] text-[19px] leading-relaxed text-ink">{model.pitch || model.resume}</p>
        <p className="mt-3 text-[14px] text-faint">
          Décrit par Claude Code à partir du code, chaque étape avec son code à l'appui.
          {model.incertitudes.length > 0 && (
            <>
              {" "}
              <a href="#unverified" className="text-muted underline decoration-line underline-offset-[3px] hover:text-ink">
                {model.incertitudes.length} point{model.incertitudes.length > 1 ? "s" : ""} non vérifié{model.incertitudes.length > 1 ? "s" : ""}
              </a>
            </>
          )}
        </p>

        <section className="mt-12" aria-labelledby="journeys-heading">
          <h2 id="journeys-heading" className="text-[20px] font-semibold">Comment ça marche</h2>
          <p className="mt-1 text-[15px] text-muted">Chaque histoire suit ce qui se passe, étape par étape.</p>
          <ul className={`mt-5 grid max-w-[1240px] gap-3 ${narrow ? "grid-cols-1" : "grid-cols-3"}`}>
            {model.parcours.map((journey) => (
              <li key={journey.id}>
                <button
                  type="button"
                  onClick={() => onJourney(journey.id)}
                  className="group flex h-full w-full flex-col rounded-xl border border-line bg-panel px-5 py-4 text-left hover:border-lamp-line"
                >
                  <span className="text-[17px] leading-snug font-semibold">{journey.nom}</span>
                  <span className="mt-2 text-[15px] leading-relaxed text-muted">{journey.depart || journey.declencheur}</span>
                  {(journey.fin || journey.resultat) && (
                    <span className="mt-2 flex gap-2 text-[15px] leading-relaxed text-ink">
                      <ArrowRight size={16} className="mt-1 shrink-0 text-lamp-ink" aria-hidden="true" />
                      {journey.fin || journey.resultat}
                    </span>
                  )}
                  <span className="mt-auto pt-3 text-[13px] text-faint group-hover:text-ink">
                    Lire l'histoire en {steps(journey.etapes.length)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        {core.length > 0 && (
          <section className="mt-14" aria-labelledby="parts-heading">
            <h2 id="parts-heading" className="text-[20px] font-semibold">Les pièces principales</h2>
            <p className="mt-1 text-[15px] text-muted">
              Cliquez une pièce pour savoir ce qu'elle fait et dans quelles histoires elle joue.
            </p>
            {narrow ? (
              <ul className="mt-5 flex flex-col gap-2">
                {core.map((block) => (
                  <li key={block.id}>
                    <button type="button" onClick={() => onBlock(block.id)} className="w-full rounded-lg border border-line bg-panel px-4 py-3 text-left">
                      <span className="block text-[13px] text-faint">{BLOCK_LABEL[block.type]}</span>
                      <span className="block text-[16px] font-semibold">{block.nom}</span>
                      <span className="block text-[14px] text-muted">{block.en_bref || block.role}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="map-surface mt-5 h-[640px] overflow-hidden rounded-xl border border-line">
                <ArchCanvas model={model} theme={theme} blocks={core} onPickBlock={onBlock} />
              </div>
            )}
          </section>
        )}

        {others > 0 && (
          <button
            type="button"
            className="mt-3 text-[15px] text-ink underline decoration-line underline-offset-[3px] hover:decoration-ink"
            onClick={() => navigate({ projectId: project.id, node: MAP_VIEW, expand: false })}
          >
            Voir toutes les pièces ({model.blocs.length})
          </button>
        )}
        <section className="mt-14 max-w-[70ch] space-y-3 text-[15px]">
          <details>
            <summary className="cursor-pointer text-muted hover:text-ink">Le projet en détail</summary>
            <p className="mt-2 max-w-[70ch] leading-relaxed text-muted">{model.resume}</p>
          </details>
          {model.incertitudes.length > 0 && (
            <details id="unverified">
              <summary className="cursor-pointer text-muted hover:text-ink">Ce que Claude n'a pas pu vérifier</summary>
              <ul className="mt-2 max-w-[70ch] list-disc space-y-1.5 pl-5 text-[14px] text-muted">
                {model.incertitudes.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </details>
          )}
        </section>
        <ModelStatusLine />
      </article>
    </div>
  );
}
