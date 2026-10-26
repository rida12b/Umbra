import { useLayoutEffect, useMemo, useRef, useState } from "react";
import type { ProjectModel } from "../api";
import type { Play } from "./ExplorerCanvas";
import type { Floor } from "./floor";
import { LineMarkers, Line } from "./floorLines";
import { placeFloor, type Rect } from "./floorLayout";
import { FloorHeader } from "./FloorHeader";
import { FloorPiece, type Look } from "./floorParts";
import type { Box, Level } from "./levels";
import type { Station } from "./stations";
import { buildRoom } from "./room";
import { enteredRoom, takeReturn } from "./roomMemory";

const PAD = 24; // around the floor; also room for the ENTRÉE badge and the wrap lane on the left

interface Props {
  model: ProjectModel;
  floor: Floor;
  level: Level;
  selected: string | null;
  play: Play | null;
  onSelect: (id: string | null) => void;
  onEnter: (box: Box) => void;
}

/** The first screen of a project: the factory floor, read top-left to bottom-right, scrolled down only. */
export function FloorCanvas({ model, floor, level, selected, play, onSelect, onEnter }: Props) {
  const screen = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(1000);
  useLayoutEffect(() => {
    const el = screen.current;
    if (!el) return;
    const measure = () => setWidth(el.clientWidth);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  // Each working room previews its machines in data order (V14), and says what start-up wiring it has.
  const rooms = useMemo(() => new Map(floor.items.flatMap((i) => (i.role === "belt" || i.role === "orphan" ? [[i.id, buildRoom(model, i.id)] as const] : []))), [model, floor]);
  const counts = useMemo(() => Object.fromEntries([...rooms].map(([id, r]) => [id, r ? r.belt.length : 0])), [rooms]);
  const settings = model.reglages_projet ?? [];
  const plan = useMemo(() => placeFloor(floor, Math.max(width - 2 * PAD, 240), counts, settings.length > 0), [floor, width, counts, settings.length]);
  useLayoutEffect(() => {
    const el = screen.current;
    const back = el && takeReturn(model);
    if (!el || !back) return;
    el.scrollTop = back.top;
    const card = back.entered && el.querySelector<HTMLElement>(`[data-floor-id="${CSS.escape(back.entered)}"] button`);
    if (card) card.focus({ preventScroll: true });
  }, [model, plan]);
  // While a journey plays, the lit station is always in view (a room low on the floor, the data going there).
  const station = play?.step.boxes[0];
  useLayoutEffect(() => {
    const card = station ? screen.current?.querySelector<HTMLElement>(`[data-floor-id="${CSS.escape(station)}"]`) : null;
    card?.scrollIntoView({ block: "nearest" });
  }, [station, plan]);
  const enter = (box: Box) => {
    enteredRoom(model, box.id, screen.current?.scrollTop ?? 0);
    onEnter(box);
  };
  const boxes = new Map(level.boxes.map((b) => [b.id, b]));
  const block = (id: string) => model.blocs.find((b) => b.id === id);
  const name = (id: string) => block(id)?.nom ?? id;
  const stepsHere = (id: string) =>
    (floor.journey?.etapes ?? []).filter((s) => (model.composants.find((c) => c.id === s.composant)?.bloc ?? s.composant) === id).length;
  // The station is lit; what the step reaches gets a faint ring; the rest of the journey stays, the others fade.
  const lookOf = (id: string): Look =>
    play ? (play.step.boxes.includes(id) ? "lit" : play.step.touched.includes(id) ? "touched" : play.boxes.has(id) ? "normal" : "dim") : "normal";
  const sortieStore = floor.sortie?.kind === "store" ? floor.sortie.id : null;
  // A tag whose line is drawn says it on the line (« démarre »); the card keeps its own words, as in the mockup (V8).
  const drawn = new Set(plan.routes.filter((r) => r.link.style !== "reply").flatMap((r) => [r.link.from, r.link.to]));
  // A strip item's link to the floor, in words (V18): never drawn, never data.
  const controls = (id: string) => {
    const link = floor.stripLinks.find((l) => l.from === id || l.to === id);
    return link ? `${link.verb || "→"} « ${name(link.from === id ? link.to : link.from)} » — contrôle, pas de donnée` : null;
  };
  // The belt section the data just ran along: from the step before's room to this step's room.
  const here = (s: Station | null | undefined) => (s ? (s.room ?? s.person) : null);
  // The first step comes in from the floor's entry (the person or service that sends the data).
  const [was, now] = [play && !play.previous ? floor.entree : here(play?.previous), here(play?.station)];
  const lit = (from: string, to: string) => !!was && !!now && was !== now && ((from === was && to === now) || (from === now && to === was));
  const back = (from: string) => from === now; // drawn the other way: the particle runs backwards
  const byHand = play && !play.station.room && !play.station.person ? play.station : null;

  return (
    <div ref={screen} className="absolute inset-0 overflow-x-hidden overflow-y-auto" onClick={() => onSelect(null)}>
      <FloorHeader model={model} floor={floor} />
      {byHand && (
        // A step done by hand, outside any part: a person station on the floor, never nothing lit (#77).
        <div className="sticky top-2 z-10 h-0 overflow-visible px-6">
          <p className="inline-flex items-center gap-2 rounded-full border-2 border-fl-hl bg-fl-person-bg px-3 py-1 text-[13.5px] text-ink shadow-md">
            <span className="fl-num on">{byHand.n}</span> Étape faite à la main par une personne, hors du code
          </p>
        </div>
      )}
      <ol className="sr-only" aria-label="Le chemin de la donnée, pièce par pièce">
        {floor.entree && <li>Entrée : {name(floor.entree)}</li>}
        {floor.beltLinks.map((link) => (
          <li key={link.id}>
            {link.verb} → {name(link.to)}
            {link.to === sortieStore ? " (sortie)" : ""}
          </li>
        ))}
        {floor.items.filter((item) => floor.relations[item.id]).map((item) => (
          <li key={item.id}>
            {name(item.id)} : {floor.relations[item.id]}
          </li>
        ))}
      </ol>
      <div className="relative" style={{ width: plan.size.width + 2 * PAD, height: plan.size.height + 2 * PAD }}>
        <div className="absolute" style={{ left: PAD, top: PAD + 8 }}>
          <svg className="pointer-events-none absolute overflow-visible" width={plan.size.width} height={plan.size.height} aria-hidden="true">
            <LineMarkers />
            {plan.belt.map(({ link, points }) => (
              <Line key={link.id} points={points} kind="belt" lit={lit(link.from, link.to)} back={back(link.from)} />
            ))}
            {plan.routes.map(({ link, points }) => (
              <Line key={link.id} points={points} kind={link.style} lit={lit(link.from, link.to)} back={back(link.from)} />
            ))}
          </svg>
          {plan.belt.map(({ link, label, points }) => {
            if (!label) return null;
            const source = block(link.from);
            const carried = source?.sort?.[0];
            const y = points[0]!.y;
            return (
              <div key={`label-${link.id}`} aria-hidden="true">
                {link.verb && (
                  <span className="fl-chip w-[112px]" style={{ left: label.x, top: points.length > 2 ? label.y : y - 30 }}>
                    {link.verb}
                  </span>
                )}
                {carried && points.length === 2 && (
                  <span className="fl-chip data w-[112px] text-[11.5px]" style={{ left: label.x, top: y + 34 }}>
                    « {carried} »
                  </span>
                )}
              </div>
            );
          })}
          {plan.routes.map(({ link, label, points }) => {
            if (link.style === "reply" && label)
              return (
                <span key={`label-${link.id}`} aria-hidden="true" className="fl-chip reply w-max max-w-[420px] whitespace-normal" style={{ left: label.x, top: label.y }}>
                  {link.verb || "répond à"} <span className="fl-tech">texte du modèle, technique</span>
                  <small className="block text-[11px] text-muted">{link.full}</small>
                </span>
              );
            // A hung part's short line carries its verb (« démarre », « fait vérifier par »), its card keeps its own words.
            if (link.style !== "reply" && link.verb) {
              const mid = { x: points[0]!.x, y: (points[0]!.y + points.at(-1)!.y) / 2 };
              return (
                <span key={`label-${link.id}`} aria-hidden="true" className={`fl-chip w-max ${link.style === "data" ? "" : "ctl"}`} style={{ left: mid.x, top: mid.y }}>
                  {link.verb}
                </span>
              );
            }
            return null;
          })}
          {plan.orphans && <Band rect={plan.orphans} title="Pièces sans chemin connu" />}
          {plan.strip && <Band rect={plan.strip} title="Autour du projet (ne tourne pas)" />}
          {floor.items.map((item) => {
            const rect = plan.rects.get(item.id);
            const box = boxes.get(item.id);
            if (!rect || !box) return null;
            const isRoom = item.role === "entree" || item.role === "belt" || item.role === "orphan";
            const room = rooms.get(item.id);
            const steps = stepsHere(item.id);
            const parts = room?.belt.length ?? 0;
            const footer = [parts ? `${parts + (room?.band.length ?? 0)} machine${parts > 1 ? "s" : ""}` : "", steps ? `${steps} étape${steps > 1 ? "s" : ""} ici` : ""]
              .filter(Boolean)
              .join(" · ");
            const b = block(item.id);
            return (
              <FloorPiece
                key={item.id}
                box={box}
                shape={item.shape}
                rect={rect}
                tag={!isRoom}
                look={lookOf(item.id)}
                selected={selected === item.id}
                badge={item.id === floor.entree && floor.belt.length > 0 ? "entree" : item.id === sortieStore && floor.belt.length > 1 ? "sortie" : null}
                kindLine={item.role === "entree" && b ? [box.kind, b.techno].filter(Boolean).join(" · ") : null}
                preview={parts > 1 ? (room?.belt ?? []).map((m) => ({ num: m.steps[0] ?? null, nom: m.nom })) : []}
                wiring={parts > 1 && room?.band.length ? room.band.map((id) => model.composants.find((c) => c.id === id)?.nom ?? id).join(", ") : null}
                footer={footer || null}
                relation={drawn.has(item.id) ? null : (floor.relations[item.id] ?? controls(item.id))}
                limit={item.id === sortieStore ? floor.limit : null}
                onSelect={onSelect}
                onEnter={enter}
              />
            );
          })}
          {plan.rects.get("settings") && (
            <ProjectSettings rect={plan.rects.get("settings")!} count={settings.length} files={[...new Set(settings.map((r) => r.fichier).filter(Boolean))] as string[]} />
          )}
        </div>
      </div>
      {floor.overflow.length > 0 && (
        <p className="px-8 pb-6 text-[13.5px] text-muted">
          + {floor.overflow.length} pièce(s) non dessinée(s) pour garder l'usine lisible : {floor.overflow.map(name).join(", ")}. Elles restent dans la recherche.
        </p>
      )}
    </div>
  );
}

function Band({ rect, title }: { rect: Rect; title: string }) {
  return (
    <div className="absolute rounded-xl border border-dashed border-line" style={{ left: rect.x, top: rect.y, width: rect.w, height: rect.h }}>
      <p className="px-3 pt-2 text-[12px] font-semibold tracking-wide text-faint uppercase">{title}</p>
    </div>
  );
}

/** The project's settings (V18, third card): where the config files are, opened from the panel later (#79). */
function ProjectSettings({ rect, count, files }: { rect: Rect; count: number; files: string[] }) {
  return (
    <div className="absolute flex flex-col justify-center rounded-lg border border-dashed border-fl-code bg-panel px-2.5 py-1.5" style={{ left: rect.x, top: rect.y, width: rect.w, height: rect.h }}>
      <span className="text-[14px] font-semibold text-ink">Réglages du projet</span>
      <span className="line-clamp-2 text-[12px] text-muted" title={files.join(", ")}>
        {count} réglage{count > 1 ? "s" : ""} · {files.join(", ")}
      </span>
    </div>
  );
}
