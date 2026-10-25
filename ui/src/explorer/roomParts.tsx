import { Search, User } from "lucide-react";
import { lowerFirst } from "../arch/story";
import type { Chute, Door, Machine } from "./room";
import type { Rect } from "./roomLayout";

// The pieces of an open room, as in mockup B (inventaire.md V27-V38): a machine with its step number in
// a circle and its in/out chips, a door outside the frame (green entry, amber exit), a red refusal card
// under its machine, a thing the machine searches or calls, and the start-up wiring band. Long words
// are cut, the full text stays on hover and focus.

type Look = "normal" | "lit" | "dim";
const at = (r: Rect) => ({ left: r.x, top: r.y, width: r.w, height: r.h });

export function MachineCard({ machine, rect, look, selected, onSelect }: { machine: Machine; rect: Rect; look: Look; selected: boolean; onSelect: (id: string) => void }) {
  const [first, ...again] = machine.steps;
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
      className={`fl-machine ${look === "lit" ? "lit" : look === "dim" ? "dim" : ""} ${selected ? "ring-2 ring-fl-service" : ""}`}
      style={at(rect)}
    >
      <span className="flex items-start gap-1.5">
        {first !== undefined && <span className="fl-num mt-0.5">{first}</span>}
        <span className="line-clamp-3 text-[14px] leading-tight font-bold text-ink">{machine.nom}</span>
      </span>
      <span className="mt-1 line-clamp-2 text-[12.5px] leading-snug text-muted">{machine.words}</span>
      {again.length > 0 && <span className="text-[11.5px] text-faint">aussi à l'étape {again.join(", ")}</span>}
      <span className="mt-auto flex flex-col gap-1">
        {machine.entre[0] && <span className="fl-io" title={machine.entre.join(", ")}>→ reçoit {machine.entre[0]}</span>}
        {machine.sort[0] && <span className="fl-io out" title={machine.sort.join(", ")}>rend {machine.sort[0]} →</span>}
      </span>
    </button>
  );
}

export function DoorCard({ door, name, person, rect, enterable, onOpen }: {
  door: Door; name: string; person: boolean; rect: Rect; enterable: boolean; onOpen: (bloc: string) => void;
}) {
  const into = door.side === "left";
  // Only the way out lists its steps (V36); the way in says who sends, as in the mockup (V27).
  const crossings = into ? [] : door.crossings.filter((c) => c.dir === "out");
  return (
    <button
      type="button"
      data-room-item={`door:${door.bloc}`}
      title={`${into ? "depuis" : "vers"} ${name}${door.verb ? ` — ${door.verb}` : ""}${enterable ? " (entrer dans cette pièce)" : ""}`}
      onClick={(event) => {
        event.stopPropagation();
        onOpen(door.bloc);
      }}
      className={`fl-door ${door.role === "entree" ? "in" : door.role === "sortie" ? "out" : ""}`}
      style={at(rect)}
    >
      {door.role === "entree" && (
        <span className="flex items-center gap-1.5">
          {person && <User size={18} className="text-fl-person" aria-hidden="true" />}
          <span className="fl-badge in">▶ ENTRÉE</span>
        </span>
      )}
      {door.role === "sortie" && <span className="fl-badge out">SORTIE ■</span>}
      <span className="line-clamp-5 text-[12.5px] leading-snug text-muted">
        {into ? "depuis" : "vers"} <strong className="font-semibold text-ink">{name}</strong>
        {door.verb && ` — ${door.verb}`}
      </span>
      {crossings.slice(0, 3).map((c) => (
        <span key={c.step} className="fl-io solid text-left" title={`étape ${c.step} : ${c.machine}`}>
          {c.step} · {c.machine}
        </span>
      ))}
      {door.role !== "sortie" && <span className="mt-auto text-[12.5px] text-fl-service">{enterable && door.role !== "entree" ? "Entrer ›" : "Voir la fiche ›"}</span>}
    </button>
  );
}

export function ChuteCard({ chute, rect }: { chute: Chute; rect: Rect }) {
  const text = `Si ${lowerFirst(chute.quand)} — ${chute.alors}`;
  return (
    <div data-room-item="chute" tabIndex={0} title={text} aria-label={`Refus. ${text}`} className="fl-refus" style={at(rect)}>
      <span className="flex items-center gap-1.5 text-[13px] font-bold text-fl-refus">
        <span className="size-[9px] shrink-0 bg-fl-refus" aria-hidden="true" />
        refus
      </span>
      <span className="line-clamp-4 text-ink/90">Si {lowerFirst(chute.quand)}</span>
      <span className="line-clamp-5 text-muted">{chute.alors}</span>
      {chute.technical && <span className="fl-tech mt-auto self-start">texte du modèle, technique</span>}
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

/** The start-up wiring (V29): what runs once when the service starts, with where it is in the code. */
export function WiringBand({ rect, items }: { rect: Rect; items: { nom: string; words: string; file: string | null }[] }) {
  return (
    <div data-room-item="band" className="absolute flex flex-col justify-center gap-1 rounded-lg border border-dashed border-line px-3 text-[12.5px]" style={at(rect)}>
      <span className="w-fit rounded border border-line px-1.5 text-[10.5px] font-semibold tracking-wide text-faint uppercase">câblage, au démarrage</span>
      {items.map((item) => (
        <span key={item.nom} className="truncate text-muted" title={`${item.nom} — ${item.words}`}>
          <strong className="font-semibold text-ink">{item.nom}</strong>
          {item.words && ` — ${item.words}`}
          {item.file && <span className="font-mono text-fl-service"> · {item.file}</span>}
        </span>
      ))}
    </div>
  );
}
