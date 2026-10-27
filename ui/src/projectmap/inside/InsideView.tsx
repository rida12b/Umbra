import { useEffect, useMemo, useRef, useState } from "react";
import type { InsideMap } from "../../api";
import { StateMessage } from "../../ui";
import { CardStrip, cardTitle } from "../card/CardStrip";
import { useCard, type CardState } from "../card/useCard";
import { AroundList, HintCard, type Place } from "../MapCards";
import type { Hint, Pointer } from "../MapDrawing";
import { MapFooter } from "../MapFooter";
import { InsideDrawing } from "./InsideDrawing";
import { insideGeometry } from "./insideGeometry";
import { useInside } from "./useInside";

interface Props {
  projectId: string;
  root: string; // the Project folder: functions open in VS Code from it
  box: string;
  card: { part: string; file: string | null } | null; // Level 2: the card open under the map
  onCard: (card: { part: string; file: string | null } | null) => void;
  onCardTitle: (title: string | null) => void; // what the top bar names after the box
  actions: number;
  origin: string | null; // where the box stood on Level 0 (« 42% 38% »): the inside grows from there
  onUp: () => void; // Esc, or a box with no inside: back to Level 0
  onStub: (neighbour: string) => void;
}

/** Level 1 (ADR-0007, #105): inside one box, its parts left → right, its neighbours as grey stubs.
 * Level 2 (#106): a click on a part or on a file of it opens its card under the map, on the same screen. */
export function InsideView({ projectId, root, box, card, onCard, onCardTitle, actions, origin, onUp, onStub }: Props) {
  const state = useInside(projectId, box);
  const cardState = useCard(projectId, box, card?.part ?? null, card?.file ?? null);
  useEffect(() => {
    if (state.kind === "none") onUp(); // an old link to a box that has no inside any more
  }, [state.kind, onUp]);
  useEffect(() => {
    if (cardState.kind === "none") onCard(null); // an old link to a part that is not drawn any more
  }, [cardState.kind, onCard]);
  const title = cardTitle(cardState);
  useEffect(() => onCardTitle(card ? title : null), [card, title, onCardTitle]);
  if (state.kind === "loading" || state.kind === "none") return <StateMessage>Lecture de la boîte…</StateMessage>;
  if (state.kind === "failed")
    return (
      <StateMessage title="La lecture de la boîte a échoué">
        <p className="font-mono text-[13px] text-danger">{state.message}</p>
      </StateMessage>
    );
  return <Inside inside={state.inside} root={root} card={card} cardState={cardState} onCard={onCard} actions={actions} origin={origin} onUp={onUp} onStub={onStub} />;
}

interface InsideProps {
  inside: InsideMap;
  root: string;
  card: Props["card"];
  cardState: CardState;
  onCard: Props["onCard"];
  actions: number;
  origin: string | null;
  onUp: () => void;
  onStub: (neighbour: string) => void;
}

function Inside({ inside, root, card, cardState, onCard, actions, origin, onUp, onStub }: InsideProps) {
  const stage = useRef<HTMLDivElement>(null);
  const drawn = useMemo(() => insideGeometry(inside), [inside]);
  const selected = card && !card.file ? card.part : null; // a part's card: the part is selected
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
      else if (card) onCard(null); // the card first, then the box: one level up per Esc
      else onUp();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const shown = cardState.kind === "ready" ? cardState.card : null;
  const head = shown ? { title: shown.title, folder: shown.folder, sentence: shown.sentence } : inside;
  return (
    <div className="relative flex h-full min-h-0 flex-col">
      <header className="pm-head">
        <div className="min-w-0 flex-1">
          <h1 className="pm-inside-title">
            {head.title} {head.folder && <span className="p">{head.folder}</span>}
          </h1>
          {head.sentence && <p className="pm-sentence">{head.sentence}</p>}
        </div>
      </header>
      <p className="pm-slide" aria-hidden="true">
        La carte glisse sur le côté : la suite est à droite →
      </p>
      <div ref={stage} className="pm-mapwrap pm-zoomin" style={origin ? { transformOrigin: origin } : undefined} onClick={(e) => e.target === e.currentTarget && card && onCard(null)}>
        <InsideDrawing
          inside={inside}
          drawn={drawn}
          selected={selected}
          litFile={card?.file ?? null}
          onSelect={(id) => onCard({ part: id, file: null })}
          onFile={(id, file) => onCard({ part: id, file })}
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
      <CardStrip state={cardState} root={root} />
      <MapFooter actions={actions} toast={toast} onToast={setToast} />
    </div>
  );
}
