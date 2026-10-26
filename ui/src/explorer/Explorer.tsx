import { ChevronRight } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { Journey, MapView, Project } from "../api";
import { MethodBanner } from "../arch/MethodBanner";
import { ModelPending } from "../arch/ModelStatus";
import { useModel } from "../model";
import { navigate, type Route } from "../route";
import type { Theme } from "../theme";
import { StateMessage } from "../ui";
import { CodeLevel } from "./CodeLevel";
import { ExplorerCanvas, type Play } from "./ExplorerCanvas";
import { FloorCanvas } from "./FloorCanvas";
import { RoomCanvas } from "./RoomCanvas";
import { enterable } from "./room";
import { InfoPanel } from "./InfoPanel";
import { buildLevel, levelOf, PROJECT_SETTINGS, trail, type Box, type Level, type LevelKey } from "./levels";
import { NarrowLevel } from "./NarrowLevel";
import { PlateSheet } from "./PlateSheet";
import { PlayerBar } from "./PlayerBar";
import { followedRoom, groupOf, journeyStations, stepGroups, type Station } from "./stations";
import { trackJourney } from "./track";

/** Explorer levels live in the URL as `x:<level>` (« x:parts », « x:part:engine »); anything else is code. */
const LEVEL_PREFIX = "x:";

/** The route node that opens one level of the explorer. */
export const levelNode = (key: LevelKey) => `${LEVEL_PREFIX}${key}`;
export const DEFAULT_LEVEL: LevelKey = "parts";
const TRANSIT_MS = 900; // a step that changes room: the floor shows the data going there, then the room opens
const STILL = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** The camera follows the data (#77): the room of the step's machine, else the floor. */
function followed(station: Station | undefined, rooms: Set<string>): LevelKey {
  const room = followedRoom(station, rooms);
  return room ? `part:${room}` : DEFAULT_LEVEL;
}

/** One step of a journey placed on a level, for the canvases. */
function playOn(journey: Journey, stations: Station[], level: Level, n: number): Play | null {
  const track = trackJourney(journey, stations, level);
  const step = track[n - 1];
  const station = stations[n - 1];
  if (!step || !station) return null;
  return {
    boxes: new Set(track.flatMap((s) => [...s.boxes, ...s.touched])),
    links: new Set(track.flatMap((s) => (s.link ? [s.link] : []))),
    step,
    journey: journey.id,
    stations,
    station,
    previous: stations[n - 2] ?? null,
  };
}

export function explorerLevel(node: string): LevelKey | null {
  if (node === "arch:" || node === "carte:") return DEFAULT_LEVEL; // links made before the explorer
  if (!node.startsWith(LEVEL_PREFIX)) return null;
  const key = node.slice(LEVEL_PREFIX.length);
  return key === "context" || key === "around" ? DEFAULT_LEVEL : (key as LevelKey); // levels before the factory floor
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
    (change: Partial<Route>) => navigate({ ...route, projectId: project.id, expand: false, row: null, ...change }),
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
  // A cited file opens its code, the function holding the cited line selected (see CodeLevel, « line:N »).
  const openCode = useCallback(
    (path: string, lines: [number, number] | null) => go({ node: path, select: lines ? `line:${lines[0]}${lines[1] !== lines[0] ? `-${lines[1]}` : ""}` : null }),
    [go],
  );
  const rooms = useMemo(() => (model ? enterable(model) : new Set<string>()), [model]);
  // A door opens the room behind it (a history entry: Back returns here), or explains a part without machines.
  const openDoor = useCallback((bloc: string) => (rooms.has(bloc) ? openLevel(`part:${bloc}`) : select(bloc)), [rooms, openLevel, select]);
  // Every step played opens where its machine is: one history entry per step, Back replays the step before.
  const play = useCallback(
    (id: string, step: number) => {
      const target = model?.parcours.find((j) => j.id === id);
      const station = model && target ? journeyStations(model, target)[step - 1] : undefined;
      go({ journey: id, step, select: null, node: levelNode(followed(station, rooms)) });
    },
    [go, model, rooms],
  );
  const stop = useCallback(() => go({ journey: null, step: null }), [go]);
  const journey = model?.parcours.find((j) => j.id === route.journey) ?? null;
  const onStep = useCallback((step: number) => journey && play(journey.id, step), [journey, play]);
  const stepNumber = journey ? Math.min(route.step ?? 1, journey.etapes.length) : 0;
  const stations = useMemo(() => (model && journey ? journeyStations(model, journey) : null), [model, journey]);
  const groups = useMemo(() => (model && journey ? stepGroups(model, journey) : null), [model, journey]);
  const playState = useMemo(() => (model && journey && stations && level ? playOn(journey, stations, level, stepNumber) : null), [model, journey, stations, level, stepNumber]);

  // A step that changes room first shows the floor, the belt lit from the old room to the new one, then the room opens.
  const [transit, setTransit] = useState<number | null>(null); // the step whose move is shown on the floor
  const shown = useRef<{ journey: string; station: Station } | null>(null);
  useLayoutEffect(() => {
    const station = stations?.[stepNumber - 1];
    const before = shown.current;
    shown.current = journey && station ? { journey: journey.id, station } : null;
    if (!journey || !station || before?.journey !== journey.id || STILL || narrow) return;
    const [a, b] = [before.station.room, station.room];
    const moved = a && b && a !== b && levelKey === `part:${b}`;
    if (!moved) return;
    setTransit(stepNumber);
    const timer = window.setTimeout(() => setTransit(null), TRANSIT_MS);
    return () => {
      window.clearTimeout(timer);
      setTransit(null);
    };
  }, [journey, stations, stepNumber, levelKey, narrow]);
  const floorLevel = useMemo(() => (model && transit !== null ? buildLevel(model, DEFAULT_LEVEL, project.name) : null), [model, transit, project.name]);
  const transitPlay = useMemo(
    () => (model && journey && stations && floorLevel && transit !== null ? playOn(journey, stations, floorLevel, transit) : null),
    [model, journey, stations, floorLevel, transit],
  );

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
  // During the transit the floor is drawn: the breadcrumb and the map's name say so.
  const crumbs = transitPlay ? trail(model, DEFAULT_LEVEL) : levelKey ? trail(model, levelKey) : [...trail(model, "parts"), ...(codeView?.breadcrumbs.map((c) => ({ key: c.key, title: c.label, code: true })) ?? [])];
  const box = level && route.select ? (level.boxes.find((b) => b.id === route.select) ?? null) : null;

  const bar = journey && (
    <PlayerBar
      journey={journey}
      step={stepNumber}
      station={stations?.[stepNumber - 1] ?? null}
      group={groupOf(groups, stepNumber)}
      onStep={onStep}
      onStop={stop}
      onOpenFile={openCode}
    />
  );
  let barUnderMap = false; // on a wide screen the bar sits under the map only, the panel runs to the bottom (V65)
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
        onDrill={(node) => navigate({ ...route, projectId: project.id, node, expand: false }, { replace: true })}
      />
    );
  else if (level && level.room === null)
    body = (
      <StateMessage title={`« ${level.title} » n'a pas de machine à ouvrir`}>
        <p>{level.hint}</p>
        <button type="button" className="mt-3 underline underline-offset-[3px]" onClick={() => openLevel(DEFAULT_LEVEL)}>
          Revenir à l'usine
        </button>
      </StateMessage>
    );
  else if (!level)
    body = (
      <StateMessage title="Ce niveau n'existe plus">
        <p>Le projet a changé depuis ce lien.</p>
        <button type="button" className="mt-3 underline underline-offset-[3px]" onClick={() => openLevel(DEFAULT_LEVEL)}>
          Revenir à l'usine
        </button>
      </StateMessage>
    );
  else {
    barUnderMap = !narrow;
    const settingsPlate = route.select === PROJECT_SETTINGS;
    const panelFor = (selected: Box | null, settings: boolean) => (
      <InfoPanel
        projectId={project.id}
        model={model}
        level={level}
        box={selected}
        playing={journey ? { journey, step: stepNumber } : null}
        onEnter={enter}
        onPlay={play}
        onStep={onStep}
        onOpenMachine={(bloc, machine) => go({ node: levelNode(`part:${bloc}`), select: machine })}
        onOpenCode={openCode}
        oldMethod={!!state?.methode_ancienne}
        projectSettings={settings}
        row={route.row ?? null}
      />
    );
    const panel = panelFor(box, settingsPlate);
    const sheet = box || settingsPlate;
    body = narrow ? (
      <div key={level.room?.bloc ?? "level"} className="h-full overflow-y-auto">
        <NarrowLevel model={model} level={level} selected={route.select ?? null} play={playState} onSelect={select} onEnter={enter} onOpenDoor={openDoor} />
        <section className="border-t border-line-soft" aria-label="Explication">
          {sheet ? panelFor(null, false) : panel}
        </section>
        {sheet && (
          <PlateSheet from={route.select ?? ""} onClose={() => select(null)}>
            {panel}
          </PlateSheet>
        )}
      </div>
    ) : (
      <div className="grid h-full min-h-0 grid-cols-[minmax(0,1fr)_400px]">
        <section className="flex min-h-0 flex-col" aria-label={`Carte : ${transitPlay && floorLevel ? floorLevel.title : level.title}`}>
          <div className="map-surface relative min-h-0 flex-1">
            {floorLevel?.floor && transitPlay ? (
              <FloorCanvas model={model} floor={floorLevel.floor} level={floorLevel} selected={null} play={transitPlay} onSelect={select} onEnter={enter} transit={TRANSIT_MS - 150} onNothingLit={() => setTransit(null)} />
            ) : level.floor ? (
              <FloorCanvas model={model} floor={level.floor} level={level} selected={route.select ?? null} play={playState} onSelect={select} onEnter={enter} />
            ) : level.room ? (
              <RoomCanvas key={level.room.bloc} model={model} room={level.room} enterable={rooms} selected={route.select ?? null} play={playState} onSelect={select} onOpenDoor={openDoor} />
            ) : (
              <ExplorerCanvas level={level} theme={theme} selected={route.select ?? null} play={playState} onSelect={select} onEnter={enter} />
            )}
          </div>
          {bar}
        </section>
        <aside className="min-h-0 overflow-y-auto border-l border-line-soft" aria-label="Explication">
          {panel}
        </aside>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <MethodBanner projectId={project.id} state={state} />
      <nav className="flex min-h-[51px] flex-wrap items-center gap-1 border-b border-line-soft px-5 py-2 text-[15px]" aria-label="Où vous êtes">
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
        {levelKey && !narrow && journey && <span className="ml-auto text-[13px] text-faint">Échap : arrêter le chemin</span>}
        {levelKey && !narrow && !journey && model && trail(model, levelKey).length > 1 && (
          // As in the mockup (V25): a real button, the key in small after it.
          <button
            type="button"
            onClick={() => {
              const above = trail(model, levelKey).at(-2);
              if (above) openLevel(above.key);
            }}
            className="ml-auto rounded-md border border-line px-2.5 py-1 text-[13px] text-ink hover:bg-panel"
          >
            ‹ Remonter <span className="text-[11.5px] text-faint">(Échap)</span>
          </button>
        )}
      </nav>
      <div className="min-h-0 flex-1">{body}</div>
      {!barUnderMap && bar}
    </div>
  );
}
