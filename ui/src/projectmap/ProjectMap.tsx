import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, type Project, type SystemMap } from "../api";
import { useLive } from "../live";
import { MAP_VIEW, navigate } from "../route";
import { Button, StateMessage } from "../ui";
import { CaptionBar } from "./CaptionBar";
import { frenchDate, geometry } from "./geometry";
import { InsideView } from "./inside/InsideView";
import { callouts, copyText } from "./lit";
import { MapDrawing, type Hint, type Pointer } from "./MapDrawing";
import { AroundList, HintCard, type Place } from "./MapCards";
import { MapFooter } from "./MapFooter";
import { useSystem } from "./useSystem";

export interface Crumbs {
  inside: string | null; // the box whose inside is open (Level 1): « Serveur »
  card: string | null; // the part or file whose card is open (Level 2): « items.py »
}

interface Props {
  project: Project;
  box: string | null; // Level 1: the box whose inside is shown; null on Level 0
  card: { part: string; file: string | null } | null; // Level 2: the card open inside that box
  onCrumb: (crumbs: Crumbs) => void; // what the top bar names after « Vue d'ensemble »
}

/** A Project's map (ADR-0007): Level 0, what it is, who comes in, its parts, what leaves; Level 1, inside one box. */
export function ProjectMap({ project, box, card, onCrumb }: Props) {
  const [state, retry] = useSystem(project.id);
  const [selected, setSelected] = useState<string | null>(null); // kept while zooming in and out
  const origin = useRef<string | null>(null);
  const highlight = useLive().highlight;
  const map = state.kind === "ready" ? state.map : null;
  const inside = box ? map?.boxes.find((b) => b.id === box) : undefined;

  const go = useCallback((next: string | null) => navigate({ projectId: project.id, node: MAP_VIEW, box: next }), [project.id]);
  const up = useCallback(() => go(null), [go]);
  const openCard = useCallback(
    (next: { part: string; file: string | null } | null) => navigate({ projectId: project.id, node: MAP_VIEW, box, part: next?.part, file: next?.file }),
    [project.id, box],
  );
  const [cardTitle, setCardTitle] = useState<string | null>(null);
  const crumb = inside?.opens ? inside.title : null; // a box with no inside stays on the whole map
  const shownCard = crumb && card ? cardTitle : null;
  useEffect(() => onCrumb({ inside: crumb, card: shownCard }), [crumb, shownCard, onCrumb]);
  // Claude lights its answer on Level 0 (#104): a `show` brings the map back to it.
  const serial = highlight?.serial;
  const seen = useRef(serial);
  useEffect(() => {
    if (serial !== undefined && serial !== seen.current && box) up();
    seen.current = serial;
  }, [serial, box, up]);

  if (state.kind === "loading") return <StateMessage>Lecture de la carte…</StateMessage>;
  if (state.kind === "reading")
    return (
      <StateMessage title="Umbra lit le projet">
        <p>La carte s'affiche dès que la lecture est finie. Aucun appel à Claude : tout est lu dans les fichiers.</p>
      </StateMessage>
    );
  if (state.kind === "offline")
    return (
      <StateMessage title="Le moteur ne répond pas">
        <p className="text-danger">{state.message}</p>
      </StateMessage>
    );
  if (state.kind === "failed")
    return (
      <StateMessage title="La lecture du projet a échoué">
        <p className="font-mono text-[13px] text-danger">{state.message}</p>
        <Button className="mt-3" onClick={retry}>
          Réessayer
        </Button>
      </StateMessage>
    );
  if (box && inside?.opens)
    return (
      <InsideView
        key={box}
        projectId={project.id}
        root={project.root}
        box={box}
        card={card}
        onCard={openCard}
        onCardTitle={setCardTitle}
        actions={state.map.actions}
        origin={origin.current}
        onUp={() => {
          setSelected(box);
          up();
        }}
        onStub={(neighbour) => {
          origin.current = null;
          setSelected(neighbour);
          const next = state.map.boxes.find((b) => b.id === neighbour);
          go(next?.opens ? neighbour : null);
        }}
      />
    );
  return (
    <Loaded
      map={state.map}
      projectId={project.id}
      selected={selected}
      onSelect={setSelected}
      onOpen={(id, at) => {
        origin.current = at;
        go(id);
      }}
    />
  );
}

interface LoadedProps {
  map: SystemMap;
  projectId: string;
  selected: string | null;
  onSelect: (id: string | null) => void;
  onOpen: (id: string, origin: string | null) => void; // zoom into a box that has an inside
}

function Loaded({ map, projectId, selected, onSelect, onOpen }: LoadedProps) {
  const stage = useRef<HTMLDivElement>(null);
  const drawn = useMemo(() => geometry(map), [map]);
  const [hint, setHint] = useState<{ hint: Hint; at: Place } | null>(null);
  const [around, setAround] = useState<Place | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const overList = useRef(false);
  // A path Claude Code lit from the terminal (`show`, #104); « effacer » hides it here at once.
  const shown = useLive().highlight;
  const [hidden, setHidden] = useState<number | null>(null);
  const highlight = shown && shown.serial !== hidden ? shown : null;
  const [step, setStep] = useState<number | null>(null);
  useEffect(() => setStep(null), [highlight?.serial]);
  const lit = useMemo(
    () => (highlight ? { boxes: new Set(highlight.boxes), callouts: callouts(drawn, highlight), current: step } : null),
    [highlight, drawn, step],
  );
  const clear = () => {
    if (!highlight) return;
    setHidden(highlight.serial);
    api.clearShown(projectId).catch(() => undefined); // the other tabs go back to the plain map too
  };
  const copy = () => {
    if (!highlight) return;
    copyToClipboard(copyText(highlight));
    setToast("Copié");
  };

  const place = (at: Pointer): Place => {
    const box = stage.current?.getBoundingClientRect();
    const target = at.currentTarget.getBoundingClientRect();
    const mouse = "clientX" in at && at.clientX ? { x: at.clientX, y: at.clientY } : { x: target.left + target.width / 2, y: target.bottom - 8 };
    return { x: mouse.x - (box?.left ?? 0), y: mouse.y - (box?.top ?? 0), width: box?.width ?? 0, height: box?.height ?? 0, below: target.bottom - (box?.top ?? 0), above: target.top - (box?.top ?? 0), left: target.left - (box?.left ?? 0) };
  };
  /** Where the box stands in the map area, in percent: the inside grows from there. */
  const originOf = (id: string): string | null => {
    const area = stage.current?.getBoundingClientRect();
    const element = stage.current?.querySelector(`[data-box="${CSS.escape(id)}"]`)?.getBoundingClientRect();
    if (!area || !element || !area.width || !area.height) return null;
    const x = ((element.left + element.width / 2 - area.left) / area.width) * 100;
    const y = ((element.top + element.height / 2 - area.top) / area.height) * 100;
    return `${x.toFixed(1)}% ${y.toFixed(1)}%`;
  };

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const count = highlight?.steps.length ?? 0;
      if (count && (event.key === "ArrowRight" || event.key === "ArrowLeft")) {
        const forward = event.key === "ArrowRight";
        setStep((n) => (n === null ? (forward ? 1 : count) : Math.min(count, Math.max(1, n + (forward ? 1 : -1)))));
        return;
      }
      if (event.key !== "Escape") return;
      if (around) setAround(null);
      else if (highlight) clear();
      else onSelect(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const where = [map.branch && `branche ${map.branch}`, map.last_change && `dernier changement ${frenchDate(map.last_change)}`].filter(Boolean).join(" · ");
  return (
    <div className="relative flex h-full min-h-0 flex-col">
      <header className="pm-head">
        <div className="min-w-0 flex-1">
          <h1>{map.name}</h1>
          {map.sentence && <p className="pm-sentence">{map.sentence}</p>}
        </div>
        <section className="pm-status" aria-label="Où on en est">
          <h2>Où on en est</h2>
          <p>{where || "pas d'historique git"}</p>
        </section>
      </header>
      {highlight && <CaptionBar caption={highlight.caption} onCopy={copy} onClear={clear} />}
      <p className="pm-slide" aria-hidden="true">
        La carte glisse sur le côté : la suite est à droite →
      </p>
      <div ref={stage} className="pm-mapwrap" onClick={(e) => e.target === e.currentTarget && onSelect(null)}>
        {map.boxes.length === 0 ? (
          <StateMessage title="Rien qui tourne n'a été trouvé">
            <p>Ni service, ni manifeste, ni dossier de code : la carte reste vide.</p>
          </StateMessage>
        ) : (
          <MapDrawing
            map={map}
            drawn={drawn}
            selected={selected}
            onSelect={(id) => {
              // A box with an inside zooms into it; any other box is selected (a second click lets go).
              if (map.boxes.find((b) => b.id === id)?.opens) onOpen(id, originOf(id));
              else onSelect(selected === id ? null : id);
            }}
            onHint={(next, at) => setHint(next && at ? { hint: next, at: place(at) } : null)}
            onAround={(at) => {
              setHint(null);
              setAround(place(at));
            }}
            onAroundLeave={() => window.setTimeout(() => !overList.current && setAround(null), 150)}
            lit={lit}
          />
        )}
        {hint && <HintCard hint={hint.hint} at={hint.at} />}
        {around && (
          <AroundList
            items={map.around}
            at={around}
            onEnter={() => (overList.current = true)}
            onLeave={() => {
              overList.current = false;
              setAround(null);
            }}
          />
        )}
      </div>
      <MapFooter actions={map.actions} toast={toast} onToast={setToast} />
    </div>
  );
}

/** The clipboard API, or the old way when the page is not allowed to use it. */
function copyToClipboard(text: string): void {
  const fallback = () => {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  };
  if (navigator.clipboard) navigator.clipboard.writeText(text).catch(fallback);
  else fallback();
}
