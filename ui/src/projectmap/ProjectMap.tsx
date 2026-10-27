import { useEffect, useMemo, useRef, useState } from "react";
import type { Project, SystemMap } from "../api";
import { Button, StateMessage } from "../ui";
import { frenchDate, geometry } from "./geometry";
import { MapDrawing, type Hint, type Pointer } from "./MapDrawing";
import { AroundList, HelpCard, HintCard, type Place } from "./MapCards";
import { useSystem } from "./useSystem";

/** A Project's default view (ADR-0007, Level 0): what it is, who comes in, its parts, what leaves, where it stands. */
export function ProjectMap({ project }: { project: Project }) {
  const [state, retry] = useSystem(project.id);
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
  return <Loaded map={state.map} />;
}

function Loaded({ map }: { map: SystemMap }) {
  const stage = useRef<HTMLDivElement>(null);
  const drawn = useMemo(() => geometry(map), [map]);
  const [selected, setSelected] = useState<string | null>(null);
  const [hint, setHint] = useState<{ hint: Hint; at: Place } | null>(null);
  const [around, setAround] = useState<Place | null>(null);
  const [help, setHelp] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const overList = useRef(false);

  const place = (at: Pointer): Place => {
    const box = stage.current?.getBoundingClientRect();
    const target = at.currentTarget.getBoundingClientRect();
    const mouse = "clientX" in at && at.clientX ? { x: at.clientX, y: at.clientY } : { x: target.left + target.width / 2, y: target.bottom - 8 };
    return { x: mouse.x - (box?.left ?? 0), y: mouse.y - (box?.top ?? 0), width: box?.width ?? 0, height: box?.height ?? 0, below: target.bottom - (box?.top ?? 0), above: target.top - (box?.top ?? 0), left: target.left - (box?.left ?? 0) };
  };

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (help) setHelp(false);
      else if (around) setAround(null);
      else setSelected(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [help, around]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 2600);
    return () => window.clearTimeout(timer);
  }, [toast]);

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
      <p className="pm-slide" aria-hidden="true">
        La carte glisse sur le côté : la suite est à droite →
      </p>
      <div ref={stage} className="pm-mapwrap" onClick={(e) => e.target === e.currentTarget && setSelected(null)}>
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
              setSelected((current) => (current === id ? null : id));
              if (map.boxes.find((b) => b.id === id)?.opens) setToast("Voir dedans arrive dans la prochaine version d'Umbra.");
            }}
            onHint={(next, at) => setHint(next && at ? { hint: next, at: place(at) } : null)}
            onAround={(at) => {
              setHint(null);
              setAround(place(at));
            }}
            onAroundLeave={() => window.setTimeout(() => !overList.current && setAround(null), 150)}
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
      <footer className="pm-bottom">
        {map.actions > 0 && (
          <button type="button" className="pm-btn" onClick={() => setToast("La liste arrive dans la prochaine version d'Umbra.")}>
            Ce qu'on peut faire <b>({map.actions})</b>
          </button>
        )}
        <button type="button" className="pm-btn round" aria-label="Aide : comment lire la carte" aria-expanded={help} onClick={() => setHelp((open) => !open)}>
          ?
        </button>
      </footer>
      {help && <HelpCard />}
      {toast && (
        <div role="status" className="pm-toast">
          {toast}
        </div>
      )}
    </div>
  );
}
