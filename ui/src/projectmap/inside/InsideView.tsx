import { useEffect, useMemo, useRef, useState } from "react";
import { api, type InsideMap } from "../../api";
import { ActionsPanel } from "../actions/ActionsPanel";
import { CaptionBar } from "../CaptionBar";
import { StateMessage } from "../../ui";
import { CardStrip, cardTitle } from "../card/CardStrip";
import { useCard, type CardState } from "../card/useCard";
import { AroundList, HintCard, type Place } from "../MapCards";
import type { Hint, Pointer } from "../MapDrawing";
import { insideLit } from "../lit";
import { MapFooter } from "../MapFooter";
import type { Panel } from "../ProjectMap";
import type { Lit } from "../useLit";
import { InsideDrawing } from "./InsideDrawing";
import { insideGeometry } from "./insideGeometry";
import { useInside } from "./useInside";

interface Props {
  projectId: string;
  name: string; // the repo, for « Ce qu'on peut faire »
  root: string; // the Project folder: functions open in VS Code from it
  box: string;
  card: { part: string; file: string | null } | null; // Level 2: the card open under the map
  onCard: (card: { part: string; file: string | null } | null) => void;
  onCardTitle: (title: string | null) => void; // what the top bar names after the box
  actions: number;
  panel: Panel;
  lit: Lit; // a path lit inside this box (an action, #107; a question naming its parts)
  origin: string | null; // where the box stood on Level 0 (« 42% 38% »): the inside grows from there
  onUp: () => void; // Esc, or a box with no inside: back to Level 0
  onStub: (neighbour: string) => void;
}

/** Level 1 (ADR-0007, #105): inside one box, its parts left → right, its neighbours as grey stubs.
 * Level 2 (#106): a click on a part or on a file of it opens its card under the map, on the same screen. */
export function InsideView({ projectId, name, root, box, card, onCard, onCardTitle, actions, panel, lit, origin, onUp, onStub }: Props) {
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
  return (
    <Inside
      inside={state.inside}
      projectId={projectId}
      name={name}
      root={root}
      card={card}
      cardState={cardState}
      onCard={onCard}
      actions={actions}
      panel={panel}
      lit={lit}
      origin={origin}
      onUp={onUp}
      onStub={onStub}
    />
  );
}

interface InsideProps {
  inside: InsideMap;
  projectId: string;
  name: string;
  root: string;
  card: Props["card"];
  cardState: CardState;
  onCard: Props["onCard"];
  actions: number;
  panel: Panel;
  lit: Lit;
  origin: string | null;
  onUp: () => void;
  onStub: (neighbour: string) => void;
}

function Inside({ inside, projectId, name, root, card, cardState, onCard, actions, panel, lit, origin, onUp, onStub }: InsideProps) {
  const stage = useRef<HTMLDivElement>(null);
  const drawn = useMemo(() => insideGeometry(inside), [inside]);
  const selected = card && !card.file ? card.part : null; // a part's card: the part is selected
  const [hint, setHint] = useState<{ hint: Hint; at: Place } | null>(null);
  const [around, setAround] = useState<Place | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const overList = useRef(false);
  const highlight = lit.highlight?.inside === inside.box ? lit.highlight : null;
  const drawnLit = useMemo(() => (highlight ? insideLit(highlight, inside.links, lit.step) : null), [highlight, inside.links, lit.step]);
  // A tap on a phone opens a hint that stays: none while a path is lit, and none left over from the step before.
  const touch = typeof window.matchMedia === "function" && window.matchMedia("(hover: none)").matches;
  useEffect(() => setHint(null), [highlight?.serial, lit.step]);

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
      else if (highlight) lit.clear(); // the lit path first, then the card, then the box
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
      {highlight && (
        <CaptionBar
          highlight={highlight}
          step={lit.step}
          onMove={lit.move}
          onCopy={() => {
            lit.copy();
            setToast("Copié");
          }}
          onClear={lit.clear}
        />
      )}
      <p className="pm-slide" aria-hidden="true">
        La carte glisse sur le côté : la suite est à droite →
      </p>
      <div className="pm-stage">
        <div className="pm-mapcol">
          <div ref={stage} className="pm-mapwrap pm-zoomin" style={origin ? { transformOrigin: origin } : undefined} onClick={(e) => e.target === e.currentTarget && card && onCard(null)}>
            <InsideDrawing
              inside={inside}
              drawn={drawn}
              selected={selected}
              litFile={card?.file ?? null}
              lit={drawnLit}
              onSelect={(id) => onCard({ part: id, file: null })}
              onFile={(id, file) => onCard({ part: id, file })}
              onStub={onStub}
              onHint={(next, at) => setHint(next && at && !(touch && highlight) ? { hint: next, at: place(at) } : null)}
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
          <CardStrip
            state={cardState}
            root={root}
            onPath={(action) => api.showAction(projectId, action).catch((error: Error) => setToast(`Le chemin n'a pas pu être tracé : ${error.message}`))}
          />
        </div>
        {panel.open && <ActionsPanel projectId={projectId} name={name} onClose={panel.onClose} />}
      </div>
      <MapFooter actions={actions} open={panel.open} onActions={panel.onOpen} toast={toast} onToast={setToast} />
    </div>
  );
}
