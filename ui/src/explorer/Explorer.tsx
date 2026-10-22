import { ChevronRight } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { MapView, Project } from "../api";
import { ModelPending } from "../arch/ModelStatus";
import { useModel } from "../model";
import { navigate, type Route } from "../route";
import type { Theme } from "../theme";
import { StateMessage } from "../ui";
import { CodeLevel } from "./CodeLevel";
import { ExplorerCanvas, type Play } from "./ExplorerCanvas";
import { InfoPanel } from "./InfoPanel";
import { buildLevel, levelOf, trail, type Box, type LevelKey } from "./levels";
import { NarrowLevel } from "./NarrowLevel";
import { PlayerBar } from "./PlayerBar";
import { trackJourney } from "./track";

/** Explorer levels live in the URL as `x:<level>` (« x:parts », « x:part:engine »); anything else is code. */
const LEVEL_PREFIX = "x:";

/** The route node that opens one level of the explorer. */
export const levelNode = (key: LevelKey) => `${LEVEL_PREFIX}${key}`;
export const DEFAULT_LEVEL: LevelKey = "parts";

export function explorerLevel(node: string): LevelKey | null {
  if (node === "arch:" || node === "carte:") return DEFAULT_LEVEL; // links made before the explorer
  if (!node.startsWith(LEVEL_PREFIX)) return null;
  return node.slice(LEVEL_PREFIX.length) as LevelKey;
}

interface Props {
  project: Project;
  route: Route;
  theme: Theme;
  narrow: boolean;
}

/**
 * The whole explorer on one screen: a map that zooms from the context of the project down to its
 * functions, a panel that explains what is selected, and a data path played on the map.
 */
export function Explorer({ project, route, theme, narrow }: Props) {
  const state = useModel();
  const model = state?.model ?? null;
  const levelKey = explorerLevel(route.node);
  const level = useMemo(() => (model && levelKey ? buildLevel(model, levelKey, project.name) : null), [model, levelKey, project.name]);
  const [codeView, setCodeView] = useState<MapView | null>(null);

  const go = useCallback(
    (change: Partial<Route>) => navigate({ ...route, projectId: project.id, expand: false, ...change }),
    [route, project.id],
  );
  const openLevel = useCallback((key: LevelKey) => go({ node: levelNode(key), select: null }), [go]);
  const enter = useCallback(
    (box: Box) => {
      const next = levelOf(box.target);
      if (next) openLevel(next);
      else if (box.target.kind === "file") go({ node: box.target.path, select: null });
    },
    [go, openLevel],
  );
  const select = useCallback((id: string | null) => go({ select: id }), [go]);
  const play = useCallback((journey: string, step: number) => go({ journey, step, select: null }), [go]);
  const stop = useCallback(() => go({ journey: null, step: null }), [go]);
  const onStep = useCallback((step: number) => go({ step, select: null }), [go]);

  const journey = model?.parcours.find((j) => j.id === route.journey) ?? null;
  const stepNumber = journey ? Math.min(route.step ?? 1, journey.etapes.length) : 0;
  const track = useMemo(() => (model && journey && level ? trackJourney(model, journey, level) : null), [model, journey, level]);
  const playState: Play | null = useMemo(() => {
    const step = track?.[stepNumber - 1];
    if (!track || !step) return null;
    return {
      boxes: new Set(track.flatMap((s) => s.boxes)),
      links: new Set(track.flatMap((s) => (s.link ? [s.link] : []))),
      step,
    };
  }, [track, stepNumber]);

  // Esc goes back up: first out of the selection, then out of the path being played, then one level up.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || !model) return;
      if (event.target instanceof HTMLElement && event.target.closest("input, textarea, [cmdk-root]")) return;
      if (route.select) select(null);
      else if (route.journey) stop();
      else if (levelKey) {
        const above = trail(model, levelKey).at(-2);
        if (above) openLevel(above.key);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [model, route.select, route.journey, levelKey, select, stop, openLevel]);

  if (!model) return <ModelPending state={state} />;
  const crumbs = levelKey ? trail(model, levelKey) : [...trail(model, "parts"), ...(codeView?.breadcrumbs.map((c) => ({ key: c.key, title: c.label, code: true })) ?? [])];
  const box = level && route.select ? (level.boxes.find((b) => b.id === route.select) ?? null) : null;
  const elsewhere = playState?.step.elsewhere ? level?.boxes.find((b) => b.id === playState.step.elsewhere?.id) : undefined;

  let body;
  if (!levelKey)
    body = (
      <CodeLevel
        key={`${route.node}|${route.expand}`}
        projectId={project.id}
        node={route.node}
        expand={route.expand}
        select={route.select ?? null}
        theme={theme}
        narrow={narrow}
        onView={setCodeView}
        onOpen={(node, expand) => go({ node, expand, select: null })}
      />
    );
  else if (!level)
    body = (
      <StateMessage title="Ce niveau n'existe plus">
        <p>Le projet a changé depuis ce lien.</p>
        <button type="button" className="mt-3 underline underline-offset-[3px]" onClick={() => openLevel(DEFAULT_LEVEL)}>
          Revenir aux pièces
        </button>
      </StateMessage>
    );
  else {
    const panel = (
      <InfoPanel
        projectId={project.id}
        model={model}
        level={level}
        box={box}
        playing={journey ? { journey, step: stepNumber } : null}
        onEnter={enter}
        onPlay={play}
        onStep={onStep}
      />
    );
    body = narrow ? (
      <div className="h-full overflow-y-auto">
        <NarrowLevel level={level} selected={route.select ?? null} play={playState} onSelect={select} onEnter={enter} />
        <section className="border-t border-line-soft" aria-label="Explication">
          {panel}
        </section>
      </div>
    ) : (
      <div className="grid h-full min-h-0 grid-cols-[minmax(0,1fr)_400px]">
        <section className="map-surface relative min-h-0" aria-label={`Carte : ${level.title}`}>
          <ExplorerCanvas level={level} theme={theme} selected={route.select ?? null} play={playState} onSelect={select} onEnter={enter} />
        </section>
        <aside className="min-h-0 overflow-y-auto border-l border-line-soft" aria-label="Explication">
          {panel}
        </aside>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <nav className="flex flex-wrap items-center gap-1 border-b border-line-soft px-5 py-2.5 text-[15px]" aria-label="Où vous êtes">
        {crumbs.map((crumb, index) => {
          const last = index === crumbs.length - 1;
          const code = "code" in crumb;
          return (
            <span key={`${crumb.key}${index}`} className="flex items-center gap-1">
              {index > 0 && <ChevronRight size={15} className="text-faint" aria-hidden="true" />}
              {last ? (
                <span aria-current="page" className="font-semibold">
                  {crumb.title}
                </span>
              ) : (
                <button
                  type="button"
                  className="text-muted hover:text-ink hover:underline"
                  onClick={() => (code ? go({ node: crumb.key, select: null }) : openLevel(crumb.key as LevelKey))}
                >
                  {crumb.title}
                </button>
              )}
            </span>
          );
        })}
        {levelKey && !narrow && (
          <span className="ml-auto text-[13px] text-faint">{journey ? "Échap : arrêter le chemin" : "Échap : remonter d'un niveau"}</span>
        )}
      </nav>
      <div className="min-h-0 flex-1">{body}</div>
      {journey && (
        <PlayerBar
          journey={journey}
          step={stepNumber}
          where={playState?.step ?? null}
          onStep={onStep}
          onStop={stop}
          onEnterElsewhere={() => elsewhere && enter(elsewhere)}
        />
      )}
    </div>
  );
}
