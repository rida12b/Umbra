import { ChevronRight, Cloud, Database, Server, User, Wrench, type LucideIcon } from "lucide-react";
import type { Shape } from "./floor";
import type { Rect } from "./floorLayout";
import type { Box } from "./levels";

// The pieces the factory floor is drawn with. The kind of a part shows as an icon and a coloured
// stripe (never the lit colour, which belongs to the journey being followed); the rest stays neutral.

const ICON: Record<Shape, LucideIcon> = { person: User, room: Server, store: Database, outside: Cloud, tool: Wrench };
const KIND_NAME: Record<Shape, string> = {
  person: "Personne",
  room: "Pièce qui travaille",
  store: "Endroit où la donnée est gardée",
  outside: "Service ou modèle appelé",
  tool: "Outil ou document (ne tourne pas)",
};
const STRIPE: Record<Shape, string> = {
  person: "border-l-kind-person",
  room: "border-l-kind-room",
  store: "border-l-kind-store",
  outside: "border-l-kind-outside",
  tool: "border-l-line",
};
const TINT: Record<Shape, string> = {
  person: "text-kind-person",
  room: "text-kind-room",
  store: "text-kind-store",
  outside: "text-kind-outside",
  tool: "text-faint",
};

export type Look = "normal" | "lit" | "dim";

interface PieceProps {
  box: Box;
  shape: Shape;
  rect: Rect;
  tag: boolean; // a supplier, a side door or a strip item: one compact line
  look: Look;
  selected: boolean;
  badge: "entree" | "sortie" | null;
  footer: string | null; // « 4 machines · 3 étapes ici »
  relation: string | null; // a hung part: how it is linked to its room, in words (« Serveur cherche dans »)
  limit: string | null; // under the SORTIE: what it cannot do
  onSelect: (id: string) => void;
  onEnter: (box: Box) => void;
}

export function FloorPiece({ box, shape, rect, tag, look, selected, badge, footer, relation, limit, onSelect, onEnter }: PieceProps) {
  const Icon = ICON[shape];
  const tone = look === "lit" ? "border-lamp-line shadow-[0_0_0_3px_var(--u-lamp-soft)]" : look === "dim" ? "border-line-soft opacity-45" : "border-line";
  const dashed = shape === "outside" || shape === "tool" ? "border-dashed" : "";
  return (
    <div
      data-floor-id={box.id}
      data-shape={shape}
      onDoubleClick={() => box.inside > 0 && onEnter(box)}
      onClick={(event) => {
        event.stopPropagation();
        onSelect(box.id);
      }}
      className={`absolute flex flex-col rounded-xl border-2 border-l-[6px] bg-panel text-left ${tone} ${STRIPE[shape]} ${dashed} ${
        selected ? "ring-2 ring-lamp" : ""
      } ${tag ? "px-3 py-2" : "px-3.5 py-2.5"}`}
      style={{ left: rect.x, top: rect.y, width: rect.w, height: rect.h }}
    >
      {badge && (
        <span
          aria-hidden="true" // said inside the button, where keyboard and screen-reader users land
          className={`absolute -top-3 left-3 rounded-md px-2 py-0.5 text-[12px] font-bold tracking-wide ${
            badge === "entree" ? "bg-kind-person text-bg" : "bg-kind-store text-bg"
          }`}
        >
          {badge === "entree" ? "▶ ENTRÉE" : "SORTIE ■"}
        </span>
      )}
      <button
        type="button"
        aria-pressed={selected}
        onClick={(event) => {
          event.stopPropagation();
          onSelect(box.id);
        }}
        className="flex min-h-0 shrink-0 flex-col rounded-md text-left"
      >
        <span className="sr-only">{badge === "entree" ? "Entrée : " : badge === "sortie" ? "Sortie : " : ""}</span>
        <span className="flex items-start gap-1.5">
          <Icon size={tag ? 15 : 17} className={`mt-[3px] shrink-0 ${TINT[shape]}`} aria-hidden="true" />
          <span className={`font-semibold leading-snug text-ink ${tag ? "line-clamp-2 text-[14px]" : "line-clamp-3 text-[16px]"}`}>{box.title}</span>
        </span>
        <span className="sr-only"> ({KIND_NAME[shape]}) </span>
        <span className={`shrink-0 leading-snug ${tag ? "line-clamp-3 text-[13px]" : "mt-0.5 line-clamp-2 text-[14px]"} ${relation ? "text-ink/80 italic" : "text-muted"}`}>
          {relation ?? box.words}
        </span>
      </button>
      {!tag && limit && (
        <em className="mt-auto line-clamp-2 shrink-0 pt-1 text-[12.5px] leading-snug text-muted" title={limit}>
          « {limit} »
        </em>
      )}
      {!tag && (
        <div className={`${limit ? "" : "mt-auto"} flex items-end justify-between gap-2 pt-1 text-[12.5px]`}>
          <span className="line-clamp-2 min-w-0 text-faint">{footer}</span>
          {box.inside > 0 && (
            <button
              type="button"
              aria-label={`Entrer dans : ${box.title}`}
              onClick={(event) => {
                event.stopPropagation();
                onEnter(box);
              }}
              className="flex shrink-0 items-center text-muted hover:text-ink hover:underline"
            >
              Entrer <ChevronRight size={14} aria-hidden="true" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/** The key: only the kinds drawn on this floor, and the kinds of line. */
export function FloorKey({ shapes, lines }: { shapes: Shape[]; lines: Set<string> }) {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[13px] text-muted" aria-label="Légende">
      {shapes.map((shape) => {
        const Icon = ICON[shape];
        return (
          <li key={shape} data-key-shape={shape} className="flex items-center gap-1.5">
            <Icon size={15} className={TINT[shape]} aria-hidden="true" />
            {KIND_NAME[shape]}
          </li>
        );
      })}
      {lines.has("data") && <LineKey dash="" width={3} text="La donnée avance" />}
      {lines.has("reply") && <LineKey dash="6 5" width={2} text="Réponse renvoyée" />}
      {lines.has("lookup") && <LineKey dash="" width={1.3} text="Va chercher une information" />}
      {lines.has("control") && <LineKey dash="2 4" width={1.5} text="Démarre ou contrôle (pas de donnée)" />}
    </ul>
  );
}

function LineKey({ dash, width, text }: { dash: string; width: number; text: string }) {
  return (
    <li className="flex items-center gap-1.5">
      <svg width="28" height="8" aria-hidden="true">
        <line x1="0" y1="4" x2="28" y2="4" stroke="var(--u-muted)" strokeWidth={width} strokeDasharray={dash} />
      </svg>
      {text}
    </li>
  );
}
