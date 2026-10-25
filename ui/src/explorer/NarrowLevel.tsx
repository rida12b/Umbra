import { ChevronRight } from "lucide-react";
import { lowerFirst } from "../arch/story";
import type { Box, Level } from "./levels";
import type { Play } from "./ExplorerCanvas";

interface Props {
  level: Level;
  selected: string | null;
  play: Play | null;
  onSelect: (id: string) => void;
  onEnter: (box: Box) => void;
  onOpenDoor?: (bloc: string) => void;
}

/** A level on a phone: the same boxes as a list, since a map is unreadable that narrow. The floor reads top to
 * bottom: ENTRÉE, each room of the belt followed by what it calls and what joins it, then what never runs. */
export function NarrowLevel({ level, selected, play, onSelect, onEnter, onOpenDoor }: Props) {
  const ends = level.floor && level.floor.entree && level.floor.sortie ? level.floor : null;
  const name = (id: string) => level.boxes.find((b) => b.id === id)?.title ?? id;
  if (level.room) return <NarrowRoom level={level} selected={selected} play={play} onSelect={onSelect} onEnter={onEnter} onOpenDoor={onOpenDoor ?? onSelect} />;
  const groups: { title: string; boxes: Entry[] }[] = level.floor ? floorGroups(level) : [{ title: level.title, boxes: level.boxes.map((box) => ({ box, depth: 0, badge: null })) }];
  return (
    <div className="px-4 py-4">
      {ends && (
        <p className="mb-4 text-[14.5px] leading-relaxed">
          <span className="font-semibold text-kind-person">▶ Entrée :</span> {name(ends.entree!)}
          <br />
          <span className="font-semibold text-kind-store">Sortie ■ :</span>{" "}
          {ends.sortie!.kind === "store" ? name(ends.sortie!.id) : `réponse renvoyée à ${name(ends.sortie!.to)}`}
        </p>
      )}
      {groups.map((group) => (
        <section key={group.title} className="mb-5">
          <h3 className="mb-2 text-[13px] font-semibold text-faint">{group.title}</h3>
          <ul className="flex flex-col gap-2">
            {group.boxes.map(({ box, depth, badge, relation, fed }) => {
              const lit = play?.step.boxes.includes(box.id);
              return (
                <li key={box.id} style={{ marginLeft: depth * 20 }}>
                  {fed && <p className="mb-1 pl-4 text-[13.5px] text-muted">↓ {fed}</p>}
                  <div
                    className={`rounded-xl border-2 bg-panel px-4 py-3 ${lit ? "border-lamp-line" : box.id === selected ? "border-ink/40" : "border-line"} ${
                      box.faded ? "opacity-60" : ""
                    } ${depth > 0 ? "border-l-4 border-l-line" : ""}`}
                  >
                    {relation && <span className="mb-0.5 block text-[13px] text-ink/80 italic">{relation}</span>}
                    {badge && <span className={`mb-1 inline-block rounded-md px-2 py-0.5 text-[12px] font-bold text-bg ${badge.startsWith("▶") ? "bg-kind-person" : "bg-kind-store"}`}>{badge}</span>}
                    <button type="button" className="block w-full text-left" onClick={() => onSelect(box.id)}>
                      <span className="block text-[12.5px] text-faint">{box.kind}</span>
                      <span className="block text-[16px] font-semibold">{box.title}</span>
                      <span className="block text-[14px] text-muted">{box.words}</span>
                    </button>
                    {box.inside > 0 && (
                      <button type="button" onClick={() => onEnter(box)} className="mt-1 flex items-center gap-1 text-[13.5px] font-medium text-lamp-ink">
                        Entrer dedans <ChevronRight size={14} aria-hidden="true" />
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}

function NarrowRoom({ level, selected, play, onSelect, onEnter, onOpenDoor }: Omit<Props, "onOpenDoor"> & { onOpenDoor: (bloc: string) => void }) {
  const room = level.room!;
  const box = (id: string) => level.boxes.find((b) => b.id === id);
  const door = (d: (typeof room.doors)[number]) => (
    <li key={d.bloc}>
      <button type="button" onClick={() => onOpenDoor(d.bloc)} className={`fl-door flow w-full text-[14px] ${d.role === "entree" ? "in" : d.role === "sortie" ? "out" : ""}`}>
        {d.role && <span className={`fl-badge ${d.role === "entree" ? "in" : "out"}`}>{d.role === "entree" ? "▶ ENTRÉE" : "SORTIE ■"}</span>}
        <span className="font-semibold">{d.side === "left" ? "depuis" : "vers"} {box(d.bloc)?.title ?? d.bloc}</span>
        {d.verb && <span className="block italic text-muted">{d.verb}</span>}
        {d.crossings.length > 0 && <span className="block text-[13px] text-faint">{d.crossings.length > 1 ? "étapes" : "étape"} {d.crossings.map((c) => c.step).join(", ")}</span>}
      </button>
    </li>
  );
  return (
    <div className="px-4 py-4">
      <ul className="flex flex-col gap-2">
        {room.doors.filter((d) => d.side === "left").map(door)}
        {room.belt.map((machine) => {
          const b = box(machine.id);
          const lit = play?.step.boxes.includes(machine.id);
          return (
            <li key={machine.id} className="flex flex-col gap-1.5">
              <div className={`rounded-xl border-2 border-l-[6px] border-l-kind-room bg-panel px-4 py-3 ${lit ? "border-lamp-line" : machine.id === selected ? "border-ink/40" : "border-line"}`}>
                <button type="button" className="block w-full text-left" onClick={() => onSelect(machine.id)}>
                  <span className="block text-[16px] font-semibold">{machine.nom}</span>
                  <span className="block text-[14px] text-muted">{machine.words}</span>
                  {machine.steps.length > 0 && <span className="block text-[12.5px] text-faint">{machine.steps.length > 1 ? "étapes" : "étape"} {machine.steps.join(", ")}</span>}
                  {/* What goes in and out, in full: a phone has room to wrap (V32). */}
                  {machine.entre[0] && <span className="mt-1 block text-[13px] text-muted">→ reçoit {machine.entre.join(", ")}</span>}
                  {machine.sort[0] && <span className="block text-[13px] text-muted">rend {machine.sort.join(", ")} →</span>}
                </button>
                {b && b.inside > 0 && (
                  <button type="button" onClick={() => onEnter(b)} className="mt-1 flex items-center gap-1 text-[13.5px] font-medium text-lamp-ink">
                    Entrer dedans <ChevronRight size={14} aria-hidden="true" />
                  </button>
                )}
              </div>
              {machine.chutes.map((chute, k) => (
                <p key={k} className="ml-4 rounded-lg border-l-4 border-l-danger bg-panel px-3 py-1.5 text-[13.5px]">
                  <span className="font-medium">Si {lowerFirst(chute.quand)}</span> <span className="text-muted">— {chute.alors}</span>
                </p>
              ))}
            </li>
          );
        })}
        {room.doors.filter((d) => d.side === "right").map(door)}
        {room.reply && (
          <li className="rounded-xl border-2 border-dashed border-fl-data px-4 py-2.5 text-[14px]">
            <span className="font-semibold">
              {room.reply.step} · {room.reply.verb} {box(room.reply.door)?.title ?? room.reply.door}
            </span>
            {room.reply.words && <span className="block text-[13px] text-muted">{room.reply.words}</span>}
          </li>
        )}
      </ul>
      {room.band.length > 0 && (
        <p className="mt-4 rounded-xl border border-dashed border-line px-4 py-2.5 text-[14px]">
          <span className="block text-[12px] font-semibold tracking-wide text-faint uppercase">câblage, au démarrage</span>
          {room.band.map((id) => box(id)?.title ?? id).join(" · ")}
        </p>
      )}
    </div>
  );
}

type Entry = { box: Box; depth: number; badge: string | null; relation?: string; fed?: string };

function floorGroups(level: Level): { title: string; boxes: Entry[] }[] {
  const floor = level.floor!;
  const sortie = floor.sortie?.kind === "store" ? floor.sortie.id : null;
  const entry = (id: string, depth: number): Entry[] => {
    const box = level.boxes.find((b) => b.id === id);
    const badge = id === floor.entree ? "▶ ENTRÉE" : id === sortie ? "SORTIE ■" : null;
    return box ? [{ box, depth, badge, relation: floor.relations[id] }] : [];
  };
  // What hangs on a room follows it, one step in: a part it calls, a side door, a door on that door.
  const hung = (id: string, depth: number): Entry[] => floor.items.filter((i) => i.attach === id).flatMap((i) => [...entry(i.id, depth), ...hung(i.id, depth + 1)]);
  const belt = [...(floor.entree ? [floor.entree] : []), ...floor.belt];
  const fed = (id: string) => entry(id, 0).map((e) => ({ ...e, fed: floor.beltLinks.find((l) => l.to === id)?.verb }));
  return [
    { title: "Le chemin de la donnée, de l'entrée à la sortie", boxes: belt.flatMap((id) => [...fed(id), ...hung(id, 1)]) },
    { title: "Pièces sans chemin connu", boxes: floor.items.filter((i) => i.role === "orphan").flatMap((i) => entry(i.id, 0)) },
    { title: "Autour du projet (ne tourne pas)", boxes: floor.strip.flatMap((id) => entry(id, 0)) },
  ].filter((g) => g.boxes.length > 0);
}
