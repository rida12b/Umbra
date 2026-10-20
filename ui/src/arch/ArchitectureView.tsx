import { useCallback, useMemo, useState } from "react";
import type { ArchBlock, ArchFlow, Project } from "../api";
import { useModel } from "../model";
import { ARCHITECTURE_VIEW, navigate, routeHash, type Route } from "../route";
import type { Theme } from "../theme";
import { ArchCanvas } from "./ArchCanvas";
import { BlockDetails, FlowDetails, Overview } from "./ArchPanels";
import { BLOCK_LABEL } from "./BlockNode";
import { JourneyPanel } from "./JourneyPanel";
import { StateMessage } from "../ui";
import { ModelPending } from "./ModelStatus";
import { journeySequence } from "./sequence";
import { SequenceView } from "./SequenceView";

interface Props {
  project: Project;
  route: Route;
  theme: Theme;
  narrow: boolean;
}

/** The Project's landing view: its architecture, or a chosen journey drawn as a sequence, step by step. */
export function ArchitectureView({ project, route, theme, narrow }: Props) {
  const state = useModel();
  const model = state?.model ?? null;
  // A picked flow belongs to the page it was picked on: any navigation (journey, Back) drops it.
  const [picked, setFlow] = useState<{ flow: ArchFlow; on: string } | null>(null);
  const here = routeHash(route);
  const flow = picked?.on === here ? picked.flow : null;
  const journey = model?.parcours.find((j) => j.id === route.journey) ?? null;
  const activeStep = journey && journey.etapes.length > 0 ? Math.min(route.step ?? 1, journey.etapes.length) : null;
  const sequence = useMemo(() => (model && journey ? journeySequence(model, journey) : null), [model, journey]);
  // The overview draws every block that has a flow; the others are listed under the map.
  const shown = useMemo(() => new Set(model?.flux.flatMap((flow) => [flow.de, flow.vers]) ?? []), [model]);

  const go = useCallback(
    (change: Partial<Route>) =>
      navigate({ ...route, projectId: project.id, node: ARCHITECTURE_VIEW, expand: false, ...change }),
    [route, project.id],
  );
  const onStep = useCallback((step: number) => {
    setFlow(null);
    go({ step, select: null });
  }, [go]);
  const onPickBlock = useCallback((id: string | null) => {
    setFlow(null);
    go({ select: id });
  }, [go]);

  if (!model) return <ModelPending state={state} />;
  const block = route.select ? model.blocs.find((b) => b.id === route.select) : undefined;
  const back = () => {
    setFlow(null);
    go({ select: null });
  };

  const panel = flow ? (
    <FlowDetails flow={flow} model={model} onBack={back} />
  ) : block ? (
    <BlockDetails block={block} model={model} project={project} onBack={back} />
  ) : journey ? (
    <JourneyPanel projectId={project.id} journey={journey} activeStep={activeStep} onStep={onStep} />
  ) : (
    <Overview model={model} onJourney={(id) => go({ journey: id, step: 1, select: null })} />
  );

  if (narrow)
    return (
      <div className="h-full min-w-0 overflow-y-auto">
        {panel}
        {!journey && !block && !flow && (
          <ul className="border-t border-line-soft px-6 py-4">
            {model.blocs.map((item) => (
              <li key={item.id} className="border-b border-line-soft py-2.5">
                <button type="button" className="text-left" onClick={() => onPickBlock(item.id)}>
                  <span className="block text-[12px] text-faint">{BLOCK_LABEL[item.type]}</span>
                  <span className="block text-[14px] font-medium">{item.nom}</span>
                  <span className="block text-[13px] text-muted">{item.role}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    );

  return (
    <div className="grid h-full min-h-0 grid-cols-[1fr_minmax(360px,440px)]">
      <section className={`relative min-h-0 ${sequence ? "" : "map-surface"}`} aria-label="Carte de l'architecture">
        {sequence && sequence.rows.length === 0 ? (
          <StateMessage title="Ce parcours n'a pas d'étape">Claude n'a décrit aucune étape pour lui. Choisissez un autre parcours.</StateMessage>
        ) : sequence ? (
          <SequenceView sequence={sequence} activeStep={activeStep} onStep={onStep} onPickBlock={onPickBlock} />
        ) : (
          <>
            <ArchCanvas
              model={model}
              theme={theme}
              shown={shown}
              pickedBlock={block?.id ?? null}
              onPickBlock={onPickBlock}
              onPickFlow={(index) => {
                const found = model.flux[index];
                setFlow(found ? { flow: found, on: here } : null);
              }}
            />
            <MapLegend offMap={model.blocs.filter((item) => !shown.has(item.id))} onPick={onPickBlock} />
          </>
        )}
      </section>
      <aside
        key={flow ? "flow" : (block?.id ?? journey?.id ?? "overview")} // another subject starts at the top
        className="min-h-0 overflow-y-auto border-l border-line-soft"
        aria-label="Détail"
      >
        {panel}
      </aside>
    </div>
  );
}

/** How to use the map, and the blocks it leaves out (no flow), in one line at its foot. */
function MapLegend({ offMap, onPick }: { offMap: ArchBlock[]; onPick: (id: string) => void }) {
  return (
    <div className="pointer-events-none absolute right-3 bottom-3 left-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-faint">
      <span className="pointer-events-auto rounded-md border border-line-soft bg-bg/90 px-2.5 py-1.5">
        Choisissez un parcours à gauche pour le suivre étape par étape. Cliquez un bloc pour son détail.
      </span>
      {offMap.length > 0 && (
        <span className="pointer-events-auto rounded-md border border-line-soft bg-bg/90 px-2.5 py-1.5">
          Sans flux :{" "}
          {offMap.map((item, index) => (
            <span key={item.id}>
              {index > 0 && ", "}
              <button type="button" className="text-muted underline decoration-line underline-offset-[3px] hover:text-ink" onClick={() => onPick(item.id)}>
                {item.nom}
              </button>
            </span>
          ))}
        </span>
      )}
    </div>
  );
}
