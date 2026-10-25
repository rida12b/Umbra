import { useLayoutEffect, useMemo, useRef, useState } from "react";
import type { ProjectModel } from "../api";
import type { Play } from "./ExplorerCanvas";
import type { Floor } from "./floor";
import { LineMarkers, Line } from "./floorLines";
import { placeFloor, type Rect } from "./floorLayout";
import { FloorHeader } from "./FloorHeader";
import { FloorPiece, type Look } from "./floorParts";
import type { Box, Level } from "./levels";
import { buildRoom } from "./room";

// Where the reader was on the floor before entering a room: Échap brings them back there, focus on that room.
const remembered: { model: ProjectModel | null; top: number; entered: string | null } = { model: null, top: 0, entered: null };

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
  const plan = useMemo(() => placeFloor(floor, Math.max(width - 2 * PAD, 240), counts), [floor, width, counts]);
  useLayoutEffect(() => {
    const el = screen.current;
    if (!el || remembered.model !== model) return;
    el.scrollTop = remembered.top;
    const card = remembered.entered && el.querySelector<HTMLElement>(`[data-floor-id="${CSS.escape(remembered.entered)}"] button`);
    if (card) card.focus({ preventScroll: true });
    remembered.model = null;
  }, [model, plan]);
  const enter = (box: Box) => {
    Object.assign(remembered, { model, top: screen.current?.scrollTop ?? 0, entered: box.id });
    onEnter(box);
  };
  const boxes = new Map(level.boxes.map((b) => [b.id, b]));
  const block = (id: string) => model.blocs.find((b) => b.id === id);
  const name = (id: string) => block(id)?.nom ?? id;
  const stepsHere = (id: string) =>
    (floor.journey?.etapes ?? []).filter((s) => (model.composants.find((c) => c.id === s.composant)?.bloc ?? s.composant) === id).length;
  const lookOf = (id: string): Look => (play ? (play.step.boxes.includes(id) ? "lit" : play.boxes.has(id) ? "normal" : "dim") : "normal");
  const sortieStore = floor.sortie?.kind === "store" ? floor.sortie.id : null;
  // A tag whose line is drawn says it on the line (« démarre »); the card keeps its own words, as in the mockup (V8).
  const drawn = new Set(plan.routes.filter((r) => r.link.style !== "reply").flatMap((r) => [r.link.from, r.link.to]));
  const lit = (from: string, to: string) => !!play && play.step.boxes.includes(from) && play.step.boxes.includes(to);

  return (
    <div ref={screen} className="absolute inset-0 overflow-x-hidden overflow-y-auto" onClick={() => onSelect(null)}>
      <FloorHeader model={model} floor={floor} />
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
              <Line key={link.id} points={points} kind="belt" lit={lit(link.from, link.to)} />
            ))}
            {plan.routes.map(({ link, points }) => (
              <Line key={link.id} points={points} kind={link.style} lit={lit(link.from, link.to)} />
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
                  <span className="fl-chip w-[118px]" style={{ left: label.x, top: points.length > 2 ? label.y : y - 30 }}>
                    {link.verb}
                  </span>
                )}
                {carried && points.length === 2 && (
                  <span className="fl-chip data w-[118px] text-[11.5px]" style={{ left: label.x, top: y + 34 }}>
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
                relation={drawn.has(item.id) ? null : (floor.relations[item.id] ?? null)}
                limit={item.id === sortieStore ? floor.limit : null}
                onSelect={onSelect}
                onEnter={enter}
              />
            );
          })}
          {plan.strip && (model.reglages_projet?.length ?? 0) > 0 && (
            <ProjectSettings rect={plan.strip} count={model.reglages_projet!.length} files={[...new Set(model.reglages_projet!.map((r) => r.fichier).filter(Boolean))] as string[]} />
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
    <div
      className="absolute flex flex-col justify-center rounded-lg border border-dashed border-fl-code bg-panel px-2.5 py-1.5"
      style={{ left: rect.x + rect.w + 4, top: rect.y + 36, width: 200, height: 76 }}
    >
      <span className="text-[14px] font-semibold text-ink">Réglages du projet</span>
      <span className="truncate text-[12px] text-muted" title={files.join(", ")}>
        {count} réglage{count > 1 ? "s" : ""} · {files.join(", ")}
      </span>
    </div>
  );
}
