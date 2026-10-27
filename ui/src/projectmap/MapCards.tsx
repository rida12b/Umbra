import type { AroundItem } from "../api";
import { where } from "./geometry";
import type { Hint } from "./MapDrawing";

/** Where a card opens, in the map area's pixels: the pointer, the area, the element's top and bottom. */
export interface Place {
  x: number;
  y: number;
  width: number;
  height: number;
  above: number;
  below: number;
  left: number; // the element's left edge
}

const CARD_W = 390;
const CARD_H = 150;
const SHOWN_PROOFS = 3;

/** On hover or focus: what the element is, one sentence, and its proof (file:lines). Never more. */
export function HintCard({ hint, at }: { hint: Hint; at: Place }) {
  const left = at.x + 16 + CARD_W > at.width ? Math.max(8, at.x - CARD_W) : at.x + 16;
  const top = at.y + 16 + CARD_H > at.height ? Math.max(8, at.y - CARD_H) : at.y + 16;
  return (
    <div className="pm-pop" style={{ left, top }} role="tooltip">
      <div className="h">{hint.title}</div>
      {hint.text && <div>{hint.text}</div>}
      {hint.proofs.slice(0, SHOWN_PROOFS).map((proof) => (
        <div key={where(proof)} className="mono">
          {where(proof)}
        </div>
      ))}
      {hint.proofs.length > SHOWN_PROOFS && <div className="mono">+ {hint.proofs.length - SHOWN_PROOFS} autres</div>}
      {hint.guess && <div className="guess">Supposé : déduit, pas lu tel quel dans le code.</div>}
      {hint.opens && <div className="hint">clic : voir dedans →</div>}
      {hint.action && <div className="hint">{hint.action}</div>}
    </div>
  );
}

/** « + N autour » unfolded: what sits around the project and does not make the app run. */
export function AroundList({ items, at, onEnter, onLeave }: { items: AroundItem[]; at: Place; onEnter: () => void; onLeave: () => void }) {
  const left = Math.max(0, Math.min(at.left, at.width - 480));
  return (
    <div className="pm-pop pm-around-pop" style={{ left, bottom: at.height - at.above + 8 }} onMouseEnter={onEnter} onMouseLeave={onLeave}>
      <div style={{ padding: "6px 10px 8px", fontSize: "12.5px", color: "var(--u-faint)" }}>Autour du projet : ne fait pas tourner l'appli</div>
      {items.map((item) => (
        <div key={item.id} className="r" title={item.proofs.map(where).join("\n")}>
          <b>{item.title}</b>
          <span>{item.detail}</span>
        </div>
      ))}
    </div>
  );
}

/** « ? »: how to read the map, with the mark each rule is about. */
export function HelpCard() {
  return (
    <div className="pm-pop pm-help" role="dialog" aria-label="Lire la carte">
      <div className="h">Lire la carte</div>
      <div className="row">
        <svg width="22" height="16" aria-hidden="true">
          <path d="M2,8 H18" stroke="currentColor" strokeWidth="2" />
          <path d="M14,4 L19,8 L14,12" fill="none" stroke="currentColor" strokeWidth="2" />
        </svg>
        une flèche = un verbe : ce qu'une boîte fait à l'autre
      </div>
      <div className="row">
        <svg width="22" height="16" aria-hidden="true">
          <circle cx="11" cy="8" r="6" fill="none" stroke="currentColor" strokeWidth="2" />
          <circle cx="11" cy="8" r="2.4" fill="currentColor" />
        </svg>
        ce qui sort du projet (colonne SORTIES)
      </div>
      <div className="row">
        <svg width="22" height="16" aria-hidden="true">
          <rect x="2" y="2" width="18" height="12" rx="3" fill="none" stroke="currentColor" strokeWidth="1.6" strokeDasharray="4 3" />
        </svg>
        pointillés = supposé, pas lu dans le code
      </div>
      <div className="row">
        <svg width="22" height="16" aria-hidden="true">
          <circle cx="11" cy="8" r="7" fill="none" stroke="currentColor" strokeWidth="1.4" />
          <path d="M9.5,5 L12.5,8 L9.5,11" fill="none" stroke="currentColor" strokeWidth="1.6" />
        </svg>
        clic sur une boîte avec ce rond : voir dedans
      </div>
      <div className="row">
        <svg width="22" height="16" aria-hidden="true">
          <path d="M7,2 L7,14 L10,11 L12.5,15 L14,14 L11.5,10 L15,10 z" fill="currentColor" />
        </svg>
        <span>au survol : la preuve, fichier et lignes</span>
      </div>
    </div>
  );
}
