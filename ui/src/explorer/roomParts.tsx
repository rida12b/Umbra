import { ArrowRight, CornerDownRight, Search, Wrench } from "lucide-react";
import { lowerFirst } from "../arch/story";
import type { Chute, Door, Machine } from "./room";
import type { Rect } from "./roomLayout";

// The pieces of an open room: a machine, a door, a refusal hanging under its machine, a thing the
// machine searches or calls, and the start-up wiring band. Long words are cut, the full text stays on
// hover and focus.

type Look = "normal" | "lit" | "dim";
const tone = (look: Look) => (look === "lit" ? "border-lamp-line shadow-[0_0_0_3px_var(--u-lamp-soft)]" : look === "dim" ? "opacity-45" : "");
const at = (r: Rect) => ({ left: r.x, top: r.y, width: r.w, height: r.h });

export function MachineCard({ machine, rect, look, selected, onSelect }: { machine: Machine; rect: Rect; look: Look; selected: boolean; onSelect: (id: string) => void }) {
  return (
    <button
      type="button"
      data-room-item={machine.id}
      aria-pressed={selected}
      title={machine.nom}
      onClick={(event) => {
        event.stopPropagation();
        onSelect(machine.id);
      }}
      className={`absolute flex flex-col rounded-xl border-2 border-l-[6px] border-line border-l-kind-room bg-panel px-3 py-2.5 text-left ${tone(look)} ${selected ? "ring-2 ring-lamp" : ""}`}
      style={at(rect)}
    >
      <span className="line-clamp-2 text-[15px] font-semibold leading-snug text-ink">{machine.nom}</span>
      <span className="mt-1 line-clamp-3 text-[13.5px] leading-snug text-muted">{machine.words}</span>
      {machine.steps.length > 0 && (
        <span className="mt-auto text-[12.5px] text-faint">
          {machine.steps.length > 1 ? "étapes" : "étape"} {machine.steps.join(", ")}
        </span>
      )}
    </button>
  );
}

export function DoorCard({ door, name, rect, enterable, onOpen }: { door: Door; name: string; rect: Rect; enterable: boolean; onOpen: (bloc: string) => void }) {
  const label = door.side === "left" ? `depuis ${name}` : `vers ${name}`;
  return (
    <button
      type="button"
      data-room-item={`door:${door.bloc}`}
      title={`${label}${door.verb ? ` — ${door.verb}` : ""}${enterable ? " (entrer dans cette pièce)" : ""}`}
      onClick={(event) => {
        event.stopPropagation();
        onOpen(door.bloc);
      }}
      className="absolute flex flex-col rounded-xl border-2 border-dashed border-line bg-bg px-2.5 py-2 text-left text-[12.5px] hover:border-ink/40"
      style={at(rect)}
    >
      <span className="flex items-start gap-1 font-semibold text-ink">
        <ArrowRight size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
        <span className="line-clamp-2 text-[13px] leading-snug">{label}</span>
      </span>
      {door.verb && <span className="mt-0.5 line-clamp-2 italic text-muted">{door.verb}</span>}
      <span className="mt-auto flex flex-col gap-0.5 text-faint">
        {door.crossings.slice(0, 3).map((c) => (
          <span key={`${c.dir}${c.step}`} className="line-clamp-2" title={`étape ${c.step} : ${c.machine}`}>
            {c.dir === (door.side === "left" ? "in" : "out") ? "→" : "↩"} {c.step} · {c.machine}
          </span>
        ))}
        {door.crossings.length > 3 && <span>+ {door.crossings.length - 3} passage(s)</span>}
      </span>
    </button>
  );
}

export function ChuteCard({ chute, rect }: { chute: Chute; rect: Rect }) {
  return (
    <div
      data-room-item="chute"
      tabIndex={0}
      title={`Si ${lowerFirst(chute.quand)} — ${chute.alors}`}
      aria-label={`Si ${lowerFirst(chute.quand)} — ${chute.alors}`} // the whole refusal, for keyboard and screen readers
      className="absolute flex flex-col rounded-lg border border-danger/60 border-l-4 border-l-danger bg-panel px-2.5 py-1.5 text-[12.5px] leading-snug"
      style={at(rect)}
    >
      <span className="flex items-start gap-1 font-medium text-ink">
        <CornerDownRight size={13} className="mt-0.5 shrink-0 text-danger" aria-hidden="true" />
        <span>Si {lowerFirst(chute.quand)}</span>
      </span>
      <span className="line-clamp-5 text-muted">{chute.alors}</span>
      {chute.technical && <span className="mt-auto text-[11.5px] text-faint">texte du modèle, technique</span>}
    </div>
  );
}

export function HungTag({ name, steps, rect, onSelect, id }: { name: string; steps: number[]; rect: Rect; id: string; onSelect: (id: string) => void }) {
  return (
    <button
      type="button"
      data-room-item={`hung:${id}`}
      title={`${name} — étapes ${steps.join(", ")}`}
      onClick={(event) => {
        event.stopPropagation();
        onSelect(id);
      }}
      className="absolute flex items-start gap-1.5 rounded-lg border border-dashed border-line bg-bg px-2.5 py-1.5 text-left text-[12.5px] leading-snug"
      style={at(rect)}
    >
      <Search size={13} className="mt-0.5 shrink-0 text-kind-outside" aria-hidden="true" />
      <span className="min-w-0">
        <span className="line-clamp-1 font-medium text-ink">{name}</span>
        <span className="block truncate text-faint">{steps.length > 1 ? "étapes" : "étape"} {steps.join(", ")} · va y chercher</span>
      </span>
    </button>
  );
}

export function WiringBand({ rect, names }: { rect: Rect; names: string[] }) {
  return (
    <div data-room-item="band" className="absolute flex flex-col justify-center rounded-xl border border-dashed border-line px-3 text-[13px]" style={at(rect)}>
      <span className="flex items-center gap-1.5 text-[12px] font-semibold tracking-wide text-faint uppercase">
        <Wrench size={13} aria-hidden="true" /> câblage, au démarrage
      </span>
      <span className="truncate text-ink" title={names.join(", ")}>
        {names.join(" · ")}
      </span>
    </div>
  );
}
