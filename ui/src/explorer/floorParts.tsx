import { Cloud, Database, Server, User, Wrench, type LucideIcon } from "lucide-react";
import { Fragment } from "react";
import type { Shape } from "./floor";
import type { Rect } from "./floorLayout";
import type { Box } from "./levels";

// The pieces the factory floor is drawn with, as in the validated mockup B (inventaire.md V7-V18):
// the person at the entry on green, a working room listing its machines, the store as an amber
// cylinder, tools as dashed tags. Classes `fl-*` live in styles.css with the mockup's colours.

const ICON: Record<Shape, LucideIcon> = { person: User, room: Server, store: Database, outside: Cloud, tool: Wrench };
const KIND_NAME: Record<Shape, string> = {
  person: "Personne",
  room: "Service (pièce)",
  store: "Base de données",
  outside: "Service extérieur",
  tool: "Autour du projet",
};

export type Look = "normal" | "lit" | "dim";

interface PieceProps {
  box: Box;
  shape: Shape;
  rect: Rect;
  tag: boolean; // a side door, a supplier or a strip item
  look: Look;
  selected: boolean;
  badge: "entree" | "sortie" | null;
  kindLine: string | null; // « Personne · HTTP / JSON »
  preview: { num: number | null; nom: string }[]; // the room's machines, in data order (V14)
  wiring: string | null; // « + Assemblage de l'application (câblage) »
  footer: string | null; // « 4 machines · 4 étapes ici »
  relation: string | null; // a hung part: how it is linked to its room, in words
  limit: string | null; // under the SORTIE: what it cannot do
  onSelect: (id: string) => void;
  onEnter: (box: Box) => void;
}

export function FloorPiece(props: PieceProps) {
  const { box, shape, rect, tag, look, selected, badge, kindLine, preview, wiring, footer, relation, limit, onSelect, onEnter } = props;
  const Icon = ICON[shape];
  const lit = look === "lit" ? "lit" : look === "dim" ? "dim" : "";
  const person = shape === "person";
  return (
    <div
      data-floor-id={box.id}
      data-shape={shape}
      onDoubleClick={() => box.inside > 0 && onEnter(box)}
      onClick={(event) => {
        event.stopPropagation();
        onSelect(box.id);
      }}
      className={`fl-card k-${shape} ${lit} ${selected ? "ring-2 ring-fl-service" : ""}`}
      style={{ left: rect.x, top: rect.y, width: rect.w, height: rect.h }}
    >
      {badge && (
        <span aria-hidden="true" className={`fl-badge ${badge === "entree" ? "in" : "out"}`}>
          {badge === "entree" ? "▶ ENTRÉE" : "SORTIE ■"}
        </span>
      )}
      <button type="button" aria-pressed={selected} className="flex min-h-0 shrink-0 flex-col gap-1 text-left">
        <span className="sr-only">{badge === "entree" ? "Entrée : " : badge === "sortie" ? "Sortie : " : ""}</span>
        <span className="flex items-start gap-2">
          {(person || tag) && <Icon size={person ? 26 : 16} strokeWidth={person ? 1.6 : 2} className={`mt-0.5 shrink-0 ${person ? "text-fl-person" : "text-faint"}`} aria-hidden="true" />}
          <span className={`font-semibold leading-tight text-ink ${tag ? "line-clamp-2 text-[14px]" : "line-clamp-3 text-[15px]"}`}>{box.title}</span>
        </span>
        <span className="sr-only"> ({KIND_NAME[shape]}) </span>
        <span className={`line-clamp-2 text-[12.5px] leading-snug ${relation ? "text-ink/80 italic" : "text-muted"}`}>{relation ?? box.words}</span>
      </button>
      {!tag && kindLine && <span className="text-[11px] text-faint">{kindLine}</span>}
      {!tag && preview.length > 0 && (
        <span className="mt-1 flex flex-wrap items-center gap-1" aria-label="Ses machines, dans l'ordre de la donnée">
          {preview.slice(0, 5).map((m, i) => (
            <Fragment key={m.nom}>
              <span className="fl-pv">
                {m.num !== null && <span className="fl-num">{m.num}</span>}
                <span className="truncate">{m.nom}</span>
              </span>
              {i < Math.min(preview.length, 5) - 1 && <span className="text-[11px] text-fl-data" aria-hidden="true">→</span>}
            </Fragment>
          ))}
        </span>
      )}
      {!tag && wiring && <span className="text-[11.5px] text-faint">+ {wiring} (câblage)</span>}
      {!tag && limit && <em className="line-clamp-2 shrink-0 text-[12px] leading-snug text-fl-store">« {limit} »</em>}
      {!tag && (footer || box.inside > 0) && (
        <span className="mt-auto flex items-end justify-between gap-2 text-[12px]">
          <span className="text-muted">{footer}</span>
          {box.inside > 0 && (
            <button
              type="button"
              aria-label={`Entrer dans : ${box.title}`}
              onClick={(event) => {
                event.stopPropagation();
                onEnter(box);
              }}
              className={`shrink-0 text-[13px] hover:underline ${shape === "store" ? "text-fl-store" : "text-fl-service"}`}
            >
              Entrer ›
            </button>
          )}
        </span>
      )}
    </div>
  );
}

/** The key, as in the mockup (V7): kinds, then the kinds of line, then the « read in the code » mark. */
export function FloorKey({ withCode, outside }: { withCode: boolean; outside: boolean }) {
  const sw = "inline-block shrink-0";
  return (
    <ul className="flex flex-wrap items-center gap-x-3.5 gap-y-1.5 border-t border-line-soft pt-2 text-[12px] text-muted" aria-label="Légende">
      <li data-key-shape="person" className="flex items-center gap-1.5"><span className={`${sw} size-3 rounded-full border-2 border-fl-person`} />Personne</li>
      <li data-key-shape="room" className="flex items-center gap-1.5"><span className={`${sw} h-[11px] w-4 rounded-[3px] border border-line border-l-4 border-l-fl-service`} />Service (pièce)</li>
      <li data-key-shape="store" className="flex items-center gap-1.5"><span className={`${sw} h-[13px] w-3 border-2 border-fl-store`} style={{ borderRadius: "50% / 30%" }} />Base de données</li>
      <li data-key-shape="tool" className="flex items-center gap-1.5"><span className={`${sw} h-2.5 w-4 rounded-[3px] border border-dashed border-faint`} />Autour du projet</li>
      {/* Not in the mockup (it had none): an outside service is drawn dashed like a tool, so the key names it when one is drawn. */}
      {outside && <li data-key-shape="outside" className="flex items-center gap-1.5"><span className={`${sw} h-2.5 w-4 rounded-[3px] border border-dashed border-muted`} />Service extérieur</li>}
      <li className="flex items-center gap-1.5"><span className={`${sw} h-[5px] w-[22px] rounded-[3px] bg-fl-data`} />Donnée (tapis)</li>
      <li className="flex items-center gap-1.5"><span className={`${sw} w-[22px] border-t-2 border-dashed border-fl-data`} />Réponse</li>
      <li className="flex items-center gap-1.5"><span className={`${sw} w-[22px] border-t border-faint`} />Contrôle, pas de donnée</li>
      <li className="flex items-center gap-1.5"><span className={`${sw} size-[9px] bg-fl-refus`} />Refus</li>
      {withCode && (
        <li className="flex basis-full items-center gap-1.5"><span className={`${sw} h-2.5 w-4 rounded-[3px] border border-dashed border-fl-code`} />Lu dans le code, pas encore dans le modèle</li>
      )}
    </ul>
  );
}
