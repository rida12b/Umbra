import { useEffect, useMemo, useRef, useState } from "react";
import type { InsideMap } from "../../api";
import { StateMessage } from "../../ui";
import { AroundList, HintCard, type Place } from "../MapCards";
import type { Hint, Pointer } from "../MapDrawing";
import { MapFooter } from "../MapFooter";
import { InsideDrawing } from "./InsideDrawing";
import { insideGeometry } from "./insideGeometry";
import { useInside } from "./useInside";

interface Props {
  projectId: string;
  box: string;
  actions: number;
  origin: string | null; // where the box stood on Level 0 (« 42% 38% »): the inside grows from there
  onUp: () => void; // Esc, or a box with no inside: back to Level 0
  onStub: (neighbour: string) => void;
}

/** Level 1 (ADR-0007, #105): inside one box, its parts left → right, its neighbours as grey stubs. */
export function InsideView({ projectId, box, actions, origin, onUp, onStub }: Props) {
  const state = useInside(projectId, box);
  useEffect(() => {
    if (state.kind === "none") onUp(); // an old link to a box that has no inside any more
  }, [state.kind, onUp]);
  if (state.kind === "loading" || state.kind === "none") return <StateMessage>Lecture de la boîte…</StateMessage>;
  if (state.kind === "failed")
    return (
      <StateMessage title="La lecture de la boîte a échoué">
        <p className="font-mono text-[13px] text-danger">{state.message}</p>
      </StateMessage>
    );
  return <Inside inside={state.inside} actions={actions} origin={origin} onUp={onUp} onStub={onStub} />;
}

function Inside({ inside, actions, origin, onUp, onStub }: { inside: InsideMap; actions: number; origin: string | null; onUp: () => void; onStub: (neighbour: string) => void }) {
  const stage = useRef<HTMLDivElement>(null);
  const drawn = useMemo(() => insideGeometry(inside), [inside]);
  const [selected, setSelected] = useState<string | null>(null);
  const [hint, setHint] = useState<{ hint: Hint; at: Place } | null>(null);
  const [around, setAround] = useState<Place | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const overList = useRef(false);

  const place = (at: Pointer): Place => {
    const area = stage.current?.getBoundingClientRect();
    const target = at.currentTarget.getBoundingClientRect();
    const mouse = "clientX" in at && at.clientX ? { x: at.clientX, y: at.clientY } : { x: target.left + target.width / 2, y: target.bottom - 8 };
    return { x: mouse.x - (area?.left ?? 0), y: mouse.y - (area?.top ?? 0), width: area?.width ?? 0, height: area?.height ?? 0, below: target.bottom - (area?.top ?? 0), above: target.top - (area?.top ?? 0), left: target.left - (area?.left ?? 0) };
  };

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (around) setAround(null);
      else if (selected) setSelected(null);
      else onUp();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <div className="relative flex h-full min-h-0 flex-col">
      <header className="pm-head">
        <div className="min-w-0 flex-1">
          <h1 className="pm-inside-title">
            {inside.title} {inside.folder && <span className="p">{inside.folder}</span>}
          </h1>
          {inside.sentence && <p className="pm-sentence">{inside.sentence}</p>}
        </div>
      </header>
      <p className="pm-slide" aria-hidden="true">
        La carte glisse sur le côté : la suite est à droite →
      </p>
      <div ref={stage} className="pm-mapwrap pm-zoomin" style={origin ? { transformOrigin: origin } : undefined} onClick={(e) => e.target === e.currentTarget && setSelected(null)}>
        <InsideDrawing
          inside={inside}
          drawn={drawn}
          selected={selected}
          onSelect={(id) => {
            setSelected((current) => (current === id ? null : id));
            setToast("Le détail d'une partie arrive dans la prochaine version d'Umbra.");
          }}
          onStub={onStub}
          onHint={(next, at) => setHint(next && at ? { hint: next, at: place(at) } : null)}
          onAround={(at) => {
            setHint(null);
            setAround(place(at));
          }}
          onAroundLeave={() => window.setTimeout(() => !overList.current && setAround(null), 150)}
        />
        {hint && <HintCard hint={hint.hint} at={hint.at} />}
        {around && (
          <AroundList
            items={inside.around}
            at={around}
            onEnter={() => (overList.current = true)}
            onLeave={() => {
              overList.current = false;
              setAround(null);
            }}
          />
        )}
      </div>
      <MapFooter actions={actions} toast={toast} onToast={setToast} />
    </div>
  );
}
