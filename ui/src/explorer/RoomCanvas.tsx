import { ArrowDown } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { ProjectModel } from "../api";
import type { Play } from "./ExplorerCanvas";
import type { Room } from "./room";
import { placeRoom, type Segment } from "./roomLayout";
import { ChuteCard, DoorCard, HungTag, MachineCard, WiringBand } from "./roomParts";

const PAD = 24;
const STILL = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

interface Props {
  model: ProjectModel;
  room: Room;
  enterable: Set<string>;
  selected: string | null;
  play: Play | null;
  onSelect: (id: string | null) => void;
  onOpenDoor: (bloc: string) => void;
}

/** A part opened in place: its machines in data order, its doors, its refusals; scrolled down only. */
export function RoomCanvas({ model, room, enterable, selected, play, onSelect, onOpenDoor }: Props) {
  const screen = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(1000);
  const [hidden, setHidden] = useState(0);
  useLayoutEffect(() => {
    const el = screen.current;
    if (!el) return;
    const measure = () => setWidth(el.clientWidth);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  const plan = useMemo(() => placeRoom(room, Math.max(width - 2 * PAD, 240)), [room, width]);
  const name = (id: string) => model.blocs.find((b) => b.id === id)?.nom ?? model.composants.find((c) => c.id === id)?.nom ?? id;

  // Items not fully in sight are counted; the button brings the next one into view.
  const outOfSight = useCallback(() => {
    const el = screen.current;
    if (!el) return [] as HTMLElement[];
    const view = el.getBoundingClientRect();
    return [...el.querySelectorAll<HTMLElement>("[data-room-item]")].filter((item) => {
      const box = item.getBoundingClientRect();
      return box.top < view.top - 1 || box.bottom > view.bottom + 1 || box.left < view.left - 1 || box.right > view.right + 1;
    });
  }, []);
  useEffect(() => {
    const el = screen.current;
    if (!el) return;
    const count = () => setHidden(outOfSight().length);
    count();
    el.addEventListener("scroll", count, { passive: true });
    window.addEventListener("resize", count);
    return () => {
      el.removeEventListener("scroll", count);
      window.removeEventListener("resize", count);
    };
  }, [plan, outOfSight]);
  const showNext = () => {
    const next = outOfSight().sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top)[0];
    next?.scrollIntoView({ block: "nearest", behavior: STILL ? "auto" : "smooth" });
  };

  const look = (id: string) => (play ? (play.step.boxes.includes(id) ? "lit" : "dim") : "normal");
  return (
    <div ref={screen} className="absolute inset-0 overflow-x-hidden overflow-y-auto" onClick={() => onSelect(null)}>
      <div className={STILL ? "" : "room-open"} style={{ position: "relative", width: plan.size.width + 2 * PAD, height: plan.size.height + 2 * PAD }}>
        <div className="absolute" style={{ left: PAD, top: PAD }}>
          <svg className="pointer-events-none absolute overflow-visible" width={plan.size.width} height={plan.size.height} aria-hidden="true">
            <defs>
              <marker id="room-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
                <path d="M0 0 8 4 0 8z" style={{ fill: "var(--u-muted)" }} />
              </marker>
            </defs>
            {[...plan.belt, ...plan.doorLinks].map((s: Segment) => (
              <path key={`${s.from}>${s.to}`} d={s.points.map((p, i) => `${i ? "L" : "M"}${p.x} ${p.y}`).join(" ")} fill="none" stroke="var(--u-muted)" strokeWidth={2.5} markerEnd="url(#room-arrow)" />
            ))}
          </svg>
          {room.band.length > 0 && plan.rects.get("band") && <WiringBand rect={plan.rects.get("band")!} names={room.band.map(name)} />}
          {room.belt.length === 0 && (
            <p className="absolute text-[14px] text-muted" style={{ top: (plan.rects.get("band")?.h ?? 0) + 24 }}>
              Aucune donnée ne passe dans cette pièce : elle sert seulement au démarrage ou au développement.
            </p>
          )}
          {room.doors.map((door) => (
            <DoorCard key={door.bloc} door={door} name={name(door.bloc)} rect={plan.rects.get(`door:${door.bloc}`)!} enterable={enterable.has(door.bloc)} onOpen={onOpenDoor} />
          ))}
          {room.belt.map((machine) => (
            <MachineCard key={machine.id} machine={machine} rect={plan.rects.get(machine.id)!} look={look(machine.id)} selected={selected === machine.id} onSelect={onSelect} />
          ))}
          {room.belt.flatMap((machine) => machine.chutes.map((chute, k) => <ChuteCard key={`${machine.id}:${k}`} chute={chute} rect={plan.rects.get(`chute:${machine.id}:${k}`)!} />))}
          {room.belt.flatMap((machine) =>
            machine.hung.map((h) => <HungTag key={`${machine.id}:${h.bloc}`} id={h.bloc} name={name(h.bloc)} steps={h.steps} rect={plan.rects.get(`hung:${machine.id}:${h.bloc}`)!} onSelect={onSelect} />),
          )}
        </div>
      </div>
      {hidden > 0 && (
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            showNext();
          }}
          className="sticky bottom-3 left-full mr-3 ml-auto flex w-fit items-center gap-1.5 rounded-full border border-line bg-panel px-3 py-1.5 text-[13px] font-medium shadow-md"
        >
          {hidden} hors champ <ArrowDown size={14} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
