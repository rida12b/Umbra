import { ChevronRight } from "lucide-react";
import type { Box, Level } from "./levels";
import type { Play } from "./ExplorerCanvas";

interface Props {
  level: Level;
  selected: string | null;
  play: Play | null;
  onSelect: (id: string) => void;
  onEnter: (box: Box) => void;
}

/** A level on a phone: the same boxes as a list, since a map is unreadable that narrow. The floor reads top to
 * bottom: ENTRÉE, each room of the belt followed by what it calls and what joins it, then what never runs. */
export function NarrowLevel({ level, selected, play, onSelect, onEnter }: Props) {
  const groups = level.floor ? floorGroups(level) : [{ title: level.title, boxes: level.boxes.map((box) => ({ box, depth: 0, badge: null })) }];
  return (
    <div className="px-4 py-4">
      {groups.map((group) => (
        <section key={group.title} className="mb-5">
          <h3 className="mb-2 text-[13px] font-semibold text-faint">{group.title}</h3>
          <ul className="flex flex-col gap-2">
            {group.boxes.map(({ box, depth, badge }) => {
              const lit = play?.step.boxes.includes(box.id);
              return (
                <li key={box.id} style={{ marginLeft: depth * 20 }}>
                  <div
                    className={`rounded-xl border-2 bg-panel px-4 py-3 ${lit ? "border-lamp-line" : box.id === selected ? "border-ink/40" : "border-line"} ${
                      box.faded ? "opacity-60" : ""
                    } ${depth > 0 ? "border-dashed" : ""}`}
                  >
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

type Entry = { box: Box; depth: number; badge: string | null };

function floorGroups(level: Level): { title: string; boxes: Entry[] }[] {
  const floor = level.floor!;
  const sortie = floor.sortie?.kind === "store" ? floor.sortie.id : null;
  const entry = (id: string, depth: number): Entry[] => {
    const box = level.boxes.find((b) => b.id === id);
    const badge = id === floor.entree ? "▶ ENTRÉE" : id === sortie ? "SORTIE ■" : null;
    return box ? [{ box, depth, badge }] : [];
  };
  // What hangs on a room follows it, one step in: a part it calls, a side door, a door on that door.
  const hung = (id: string, depth: number): Entry[] => floor.items.filter((i) => i.attach === id).flatMap((i) => [...entry(i.id, depth), ...hung(i.id, depth + 1)]);
  const belt = [...(floor.entree ? [floor.entree] : []), ...floor.belt];
  return [
    { title: "Le chemin de la donnée, de l'entrée à la sortie", boxes: belt.flatMap((id) => [...entry(id, 0), ...hung(id, 1)]) },
    { title: "Pièces sans chemin connu", boxes: floor.items.filter((i) => i.role === "orphan").flatMap((i) => entry(i.id, 0)) },
    { title: "Autour du projet (ne tourne pas)", boxes: floor.strip.flatMap((id) => entry(id, 0)) },
  ].filter((g) => g.boxes.length > 0);
}
