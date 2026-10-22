import { ChevronRight } from "lucide-react";
import { ZONE_TITLE, ZONES, type Box, type Level } from "./levels";
import type { Play } from "./ExplorerCanvas";

interface Props {
  level: Level;
  selected: string | null;
  play: Play | null;
  onSelect: (id: string) => void;
  onEnter: (box: Box) => void;
}

/** A level on a phone: the same boxes, listed by zone, since a map of boxes is unreadable that narrow. */
export function NarrowLevel({ level, selected, play, onSelect, onEnter }: Props) {
  const groups = level.zoned
    ? ZONES.map((zone) => ({ title: ZONE_TITLE[zone], boxes: level.boxes.filter((b) => b.zone === zone) })).filter((g) => g.boxes.length > 0)
    : [{ title: level.title, boxes: level.boxes }];
  return (
    <div className="px-4 py-4">
      {groups.map((group) => (
        <section key={group.title} className="mb-5">
          <h3 className="mb-2 text-[13px] font-semibold text-faint">{group.title}</h3>
          <ul className="flex flex-col gap-2">
            {group.boxes.map((box) => {
              const lit = play?.step.boxes.includes(box.id);
              return (
                <li key={box.id}>
                  <div
                    className={`rounded-xl border-2 bg-panel px-4 py-3 ${lit ? "border-lamp-line" : box.id === selected ? "border-ink/40" : "border-line"} ${
                      box.faded ? "opacity-60" : ""
                    }`}
                  >
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
