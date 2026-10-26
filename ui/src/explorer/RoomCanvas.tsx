import { ArrowDown } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { ProjectModel } from "../api";
import type { Play } from "./ExplorerCanvas";
import { buildFloor, mainJourney } from "./floor";
import { FloorHeader } from "./FloorHeader";
import { Line, LineMarkers } from "./floorLines";
import type { Room } from "./room";
import type { Point } from "./floorLayout";
import { placeRoom, type Rect } from "./roomLayout";
import { PROJECT_SETTINGS } from "./levels";
import { ProjectSettingsCard } from "./ProjectSettingsCard";
import { rememberRoom } from "./roomMemory";
import { ChuteCard, DoorCard, HungTag, MachineCard, WiringBand } from "./roomParts";

const PAD = 24;
const BUTTON_STRIP = 56; // the « hors champ » button's height and margin at the bottom of the view
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

/** A part opened in place, under the floor's own header: its machines in data order, its doors, its refusals. */
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
  const floor = useMemo(() => buildFloor(model), [model]);
  const name = useCallback((id: string) => model.blocs.find((b) => b.id === id)?.nom ?? model.composants.find((c) => c.id === id)?.nom ?? id, [model]);
  const plan = useMemo(() => placeRoom(room, Math.max(width - 2 * PAD, 240), (bloc) => name(bloc).length), [room, width, name]);
  const block = model.blocs.find((b) => b.id === room.bloc);
  const component = (id: string) => model.composants.find((c) => c.id === id);
  const station = play?.station ?? null;
  // Another journey than the one the room is drawn for: the doors', tags' and answer's step numbers belong to the
  // room's journey, so they are hidden; the wiring band gets the played journey's numbers when it is the station.
  const foreign = !!play && play.journey !== room.journey?.id;
  const bandSteps = (id: string) => (play ? play.stations.filter((s) => s.machine === id).map((s) => s.n) : []);
  const wiring = room.band.map((id) => ({
    nom: name(id), words: component(id)?.en_bref ?? "", file: component(id)?.fichiers[0] ?? null, lit: station?.machine === id, steps: bandSteps(id), current: station?.n ?? null,
  }));
  // The band wires the machines it uses (V30): a thin grey mark down to each of them.
  const wired = room.belt.filter((m) => room.band.some((id) => component(id)?.utilise.includes(m.id)));

  // Items not fully in sight are counted; the button brings the next one into view.
  const outOfSight = useCallback(() => {
    const el = screen.current;
    if (!el) return [] as HTMLElement[];
    const view = el.getBoundingClientRect();
    return [...el.querySelectorAll<HTMLElement>("[data-room-item]")].filter((item) => {
      const box = item.getBoundingClientRect();
      // Below (or under the button's strip) or right: the button only goes forward, never loops, never hides an item.
      return box.bottom > view.bottom - BUTTON_STRIP || box.right > view.right + 1;
    });
  }, []);
  useEffect(() => {
    const el = screen.current;
    if (!el) return;
    const count = () => setHidden(outOfSight().length);
    count();
    const late = window.setTimeout(count, 260); // after the room's opening animation (220 ms) has set the final sizes
    el.addEventListener("scroll", count, { passive: true });
    window.addEventListener("resize", count);
    return () => {
      window.clearTimeout(late);
      el.removeEventListener("scroll", count);
      window.removeEventListener("resize", count);
    };
  }, [plan, outOfSight]);
  const showNext = () => {
    const next = outOfSight().sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top)[0];
    next?.scrollIntoView({ block: "start", behavior: STILL ? "auto" : "smooth" });
  };

  // On entering (the canvas is keyed by room): keyboard focus on the room's title, the page at its top.
  const title = useRef<HTMLParagraphElement>(null);
  useLayoutEffect(() => title.current?.focus({ preventScroll: true }), []);
  // The step's machine is always in view: a room may be taller than the screen.
  useLayoutEffect(() => {
    if (station?.machine) screen.current?.querySelector<HTMLElement>(`[data-room-item="${CSS.escape(station.machine)}"]`)?.scrollIntoView({ block: "nearest" });
  }, [station?.machine, plan]);
  const openDoor = (bloc: string) => {
    if (enterable.has(bloc)) rememberRoom(bloc);
    onOpenDoor(bloc);
  };
  const strip = floor.strip.map((id) => model.blocs.find((b) => b.id === id)).filter((b) => b !== undefined);
  const settings = model.reglages_projet ?? [];
  // The same words as on the floor (V18, V39): what the strip item does to the floor, never data.
  const control = (id: string) => {
    const link = floor.stripLinks.find((l) => l.from === id || l.to === id);
    return link ? `${link.verb || "→"} « ${name(link.from === id ? link.to : link.from)} » — contrôle, pas de donnée` : null;
  };

  // While a journey plays (V47-V51): only the step's machine lights up, the other machines stay as they are.
  const touched = (id: string) => !!station?.touches.includes(id);
  const look = (id: string) => (station?.machine === id ? "lit" : "normal");
  const numbersOf = (id: string) => (play ? play.stations.filter((s) => s.machine === id).map((s) => s.n) : null);
  // The belt's data (V48) rides the main journey only; another journey shows what the machine takes in.
  const pill = play && mainJourney(model).journey?.id === play.journey ? (model.donnee?.[0]?.nom ?? null) : null;
  // The belt section the data just ran along (V49): from the step before's machine, or the door it came in by.
  const previous = play?.previous ?? null;
  const entry = room.doors.find((d) => d.role === "entree")?.bloc ?? room.doors.find((d) => d.side === "left")?.bloc;
  const came = !play
    ? null
    : !previous
      ? entry && `door:${entry}`
      : previous.room === room.bloc
        ? previous.machine
        : (previous.room ?? previous.person) && `door:${previous.room ?? previous.person}`;
  const went = station?.room === room.bloc ? station.machine : null;
  const lit = (from: string, to: string) => !!came && !!went && came !== went && ((from === came && to === went) || (from === went && to === came));
  const back = (from: string) => from === went;
  // No belt section joins them (a return to an earlier machine, a door that feeds another machine): a short lit
  // hop above the cards, for this step only, so the picture moves as the words say.
  const joined = [...plan.belt, ...plan.doorLinks].some((s) => lit(s.from, s.to));
  const hop = play && !joined && came && went && came !== went ? hopBetween(plan.rects.get(came), plan.rects.get(went)) : null;
  const bare = (id: string) => id.replace(/^door:/, "");
  // The answer going back (V37) lights on the step that sends it, in the journey the room is drawn for.
  const replying = !!room.reply && play?.journey === room.journey?.id && station?.n === room.reply.step;
  // The step that crosses each door, on its belt section (V34).
  const crossing = (bloc: string, dir: "in" | "out") => room.doors.find((d) => d.bloc === bloc)?.crossings.find((c) => c.dir === dir)?.step;
  const f = plan.frame;
  return (
    <div className="absolute inset-0">
      <div ref={screen} className="absolute inset-0 overflow-x-hidden overflow-y-auto" onClick={() => onSelect(null)}>
        <FloorHeader model={model} floor={floor} />
        <div className={STILL ? "" : "room-open"} style={{ position: "relative", width: plan.size.width + 2 * PAD, height: plan.size.height + 2 * PAD }}>
          <div className="absolute" style={{ left: PAD, top: PAD, width: plan.size.width, height: plan.size.height }}>
            <div className="fl-frame" style={{ left: f.x, top: f.y, width: f.w, height: f.h }} aria-hidden="true" />
            <p ref={title} tabIndex={-1} className="absolute line-clamp-2 text-[13px] leading-snug text-muted outline-none" style={{ left: f.x + 16, top: f.y + 8, width: f.w - 32 }}>
              <strong className="font-bold text-ink">{block?.nom ?? room.bloc}</strong>
              {block?.en_bref && ` — ${block.en_bref}`}
              <span className="text-[11.5px] text-faint"> · pièce ouverte, la donnée va de gauche à droite</span>
            </p>
            <svg className="pointer-events-none absolute overflow-visible" width={plan.size.width} height={plan.size.height} aria-hidden="true">
              <LineMarkers />
              {plan.rects.get("band") &&
                wired.map((m) => {
                  const band = plan.rects.get("band")!;
                  const r = plan.rects.get(m.id)!;
                  const x = r.x + r.w / 2;
                  return <line key={m.id} x1={x} y1={band.y + band.h} x2={x} y2={r.y} stroke="var(--fl-control)" strokeWidth={1.2} />;
                })}
              {room.belt.flatMap((m) =>
                m.chutes.map((_, k) => {
                  const r = plan.rects.get(m.id)!;
                  const c = plan.rects.get(`chute:${m.id}:${k}`)!;
                  const top = k === 0 ? r.y + r.h : plan.rects.get(`chute:${m.id}:${k - 1}`)!.y + plan.rects.get(`chute:${m.id}:${k - 1}`)!.h;
                  return <line key={`${m.id}:${k}`} x1={r.x + 26} y1={top} x2={r.x + 26} y2={c.y} stroke="var(--fl-refus)" strokeOpacity={0.6} strokeWidth={1.5} strokeDasharray="4 4" />;
                }),
              )}
              {plan.reply && <Line points={plan.reply.points} kind="reply" lit={replying} />}
              {hop && <Line points={hop} kind="data" lit />}
              {[...plan.belt, ...plan.doorLinks].map((s) => (
                <Line key={`${s.from}>${s.to}`} points={s.points} kind="belt" lit={lit(s.from, s.to)} back={back(s.from)} dim />
              ))}
            </svg>
            {plan.rects.get("band") &&
              wired.map((m) => {
                const band = plan.rects.get("band")!;
                const r = plan.rects.get(m.id)!;
                return (
                  <span key={m.id} className="fl-chip ctl text-[10.5px]" style={{ left: r.x + r.w / 2, top: (band.y + band.h + r.y) / 2 }} aria-hidden="true">
                    câblage
                  </span>
                );
              })}
            {plan.doorLinks.map((s) => {
              const step = foreign ? undefined : s.from.startsWith("door:") ? crossing(bare(s.from), "in") : crossing(bare(s.to), "out");
              const p = s.points;
              if (step === undefined || p.length < 2) return null;
              return (
                // A turning section shares its start with the straight one above it: its number goes on its own, vertical part.
                <span
                  key={`n-${s.from}>${s.to}`}
                  className="fl-chip text-[11px] font-semibold"
                  style={p.length > 2 ? { left: p[1]!.x - 16, top: (p[1]!.y + p[2]!.y) / 2 } : { left: (p[0]!.x + p.at(-1)!.x) / 2, top: p[0]!.y - 17 }}
                  aria-hidden="true"
                >
                  {step}
                </span>
              );
            })}
            {room.reply && plan.rects.get("reply") && <ReplyLabel rect={plan.rects.get("reply")!} step={foreign ? null : room.reply.step} verb={room.reply.verb} to={name(room.reply.door)} words={room.reply.words} />}
            {room.band.length > 0 && plan.rects.get("band") && <WiringBand rect={plan.rects.get("band")!} items={wiring} />}
            {room.belt.length === 0 && (
              <p className="absolute text-[14px] text-muted" style={{ left: f.x + 16, top: (plan.rects.get("band")?.y ?? 34) + (plan.rects.get("band")?.h ?? 0) + 24 }}>
                Aucune donnée ne passe dans cette pièce : elle sert seulement au démarrage ou au développement.
              </p>
            )}
            {room.doors.map((door) => (
              <DoorCard
                key={door.bloc}
                door={door}
                name={name(door.bloc)}
                person={["user", "device"].includes(model.blocs.find((b) => b.id === door.bloc)?.type ?? "")}
                rect={plan.rects.get(`door:${door.bloc}`)!}
                enterable={enterable.has(door.bloc)}
                onOpen={openDoor}
                hideSteps={foreign}
                touched={touched(door.bloc) || came === `door:${door.bloc}`}
              />
            ))}
            {room.belt.map((machine) => (
              <MachineCard
                key={machine.id}
                machine={machine}
                rect={plan.rects.get(machine.id)!}
                look={look(machine.id)}
                selected={selected === machine.id}
                onSelect={onSelect}
                numbers={numbersOf(machine.id)}
                current={station?.n ?? null}
                pill={look(machine.id) === "lit" ? (pill ?? machine.entre[0] ?? null) : null}
              />
            ))}
            {room.belt.flatMap((machine) => machine.chutes.map((chute, k) => <ChuteCard key={`${machine.id}:${k}`} chute={chute} rect={plan.rects.get(`chute:${machine.id}:${k}`)!} />))}
            {room.belt.flatMap((machine) =>
              machine.hung.map((h) => <HungTag key={`${machine.id}:${h.bloc}`} id={h.bloc} name={name(h.bloc)} verb={floor.links.find((l) => l.from === room.bloc && l.to === h.bloc)?.verb ?? null} steps={foreign ? [] : h.steps} rect={plan.rects.get(`hung:${machine.id}:${h.bloc}`)!} onSelect={onSelect} touched={touched(h.bloc)} />),
            )}
          </div>
        </div>
        {(strip.length > 0 || settings.length > 0) && (
          // The floor's strip stays under the room (V39): the same « Autour du projet », after a scroll.
          <section className="mx-6 mb-6 rounded-xl border border-dashed border-line px-3 pt-2 pb-3" aria-label="Autour du projet (ne tourne pas)">
            <p className="text-[12px] font-semibold tracking-wide text-faint uppercase">Autour du projet (ne tourne pas)</p>
            <ul className="mt-2 flex flex-wrap gap-3">
              {strip.map((b) => (
                <li key={b.id} className="w-[230px] rounded-lg border border-dashed border-line px-2.5 py-1.5 text-[12.5px]">
                  <span className="block font-semibold text-ink">{b.nom}</span>
                  <span className="line-clamp-2 text-muted">{b.en_bref || b.role}</span>
                  {control(b.id) && <span className="line-clamp-2 text-[11.5px] text-faint">{control(b.id)}</span>}
                </li>
              ))}
              {settings.length > 0 && (
                <li>
                  <ProjectSettingsCard model={model} className="w-[230px]" selected={selected === PROJECT_SETTINGS} onOpen={() => onSelect(PROJECT_SETTINGS)} />
                </li>
              )}
            </ul>
          </section>
        )}
        {/* Room for the « hors champ » button at the end: once scrolled down, it covers nothing. */}
        <div style={{ height: BUTTON_STRIP }} aria-hidden="true" />
      </div>
      {hidden > 0 && (
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            showNext();
          }}
          className="absolute right-4 bottom-3 flex items-center gap-1.5 rounded-full border border-line bg-panel px-3 py-1.5 text-[13px] font-medium shadow-md"
        >
          {hidden} hors champ <ArrowDown size={14} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

/** A path from one card to another over the top of both: up, across, down onto the second. */
function hopBetween(a: Rect | undefined, b: Rect | undefined): Point[] | null {
  if (!a || !b) return null;
  const y = Math.min(a.y, b.y) - 7; // under the « câblage » chips, which sit higher in the gap
  const xa = a.x + a.w * (a.x + a.w / 2 === b.x + b.w / 2 ? 0.3 : 0.5); // one above the other: two separate legs
  const xb = b.x + b.w * (a.x + a.w / 2 === b.x + b.w / 2 ? 0.7 : 0.5);
  return [{ x: xa, y: a.y }, { x: xa, y }, { x: xb, y }, { x: xb, y: b.y - 1 }]; // the tip stays above the card
}

/** The answer's words under the room (V38): its step, who it answers, and what it holds. */
function ReplyLabel({ rect, step, verb, to, words }: { rect: Rect; step: number | null; verb: string; to: string; words: string }) {
  return (
    <p className="absolute rounded-md border border-dashed border-line bg-bg px-2.5 py-1 text-center text-[12px] leading-snug" style={{ left: rect.x, top: rect.y, width: rect.w, minHeight: rect.h }}>
      {step !== null && `${step} · `}
      {verb} {to} <span className="fl-tech">texte du modèle, technique</span>
      {words && <span className="block truncate text-[11px] text-muted" title={words}>{words}</span>}
    </p>
  );
}
