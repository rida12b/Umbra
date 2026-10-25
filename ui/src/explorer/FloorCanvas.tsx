import { useLayoutEffect, useMemo, useRef, useState } from "react";
import type { ProjectModel } from "../api";
import type { Play } from "./ExplorerCanvas";
import type { Floor, LinkStyle } from "./floor";
import { placeFloor, type Point, type Rect } from "./floorLayout";
import { FloorKey, FloorPiece, type Look } from "./floorParts";
import type { Box, Level } from "./levels";

const PAD = 24; // around the floor; also room for the ENTRÉE badge and the wrap lane on the left
const STILL = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const STROKE: Record<LinkStyle, { width: number; dash: string }> = {
  data: { width: 3, dash: "" },
  reply: { width: 2, dash: "6 5" },
  lookup: { width: 1.3, dash: "" },
  control: { width: 1.5, dash: "2 4" },
};

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
  const plan = useMemo(() => placeFloor(floor, Math.max(width - 2 * PAD, 240)), [floor, width]);
  const boxes = new Map(level.boxes.map((b) => [b.id, b]));
  const name = (id: string) => model.blocs.find((b) => b.id === id)?.nom ?? id;
  const stepsHere = (id: string) =>
    (floor.journey?.etapes ?? []).filter((s) => (model.composants.find((c) => c.id === s.composant)?.bloc ?? s.composant) === id).length;
  const machines = (id: string) => model.composants.filter((c) => c.bloc === id).length;

  const lookOf = (id: string): Look => (play ? (play.step.boxes.includes(id) ? "lit" : play.boxes.has(id) ? "normal" : "dim") : "normal");
  const lineLook = (id: string, from: string, to: string): Look =>
    play ? (play.step.link === id ? "lit" : play.links.has(id) ? "normal" : "dim") : selected && (from === selected || to === selected) ? "lit" : "normal";
  const sortieStore = floor.sortie?.kind === "store" ? floor.sortie.id : null;

  return (
    <div ref={screen} className="absolute inset-0 overflow-x-hidden overflow-y-auto" onClick={() => onSelect(null)}>
      <header className="flex flex-col gap-2 border-b border-line-soft px-8 pt-5 pb-4">
        <p className="max-w-[78ch] text-[16px] leading-relaxed text-ink">{model.pitch || model.resume}</p>
        <p className="text-[14px] text-muted">
          {floor.journey ? (
            <>
              Le tapis suit le chemin <strong className="font-semibold text-ink">« {floor.journey.nom} »</strong>
              {floor.sortie?.kind === "reply" && <> · la donnée finit en réponse renvoyée à {name(floor.sortie.to)}</>}
              {floor.equivalents > 1 && <> · choisi parmi {floor.equivalents} chemins équivalents</>}
            </>
          ) : (
            <strong className="font-semibold text-ink">Aucun chemin de données dans le modèle : les pièces sont posées sans tapis.</strong>
          )}
          {floor.skipped > 0 && <> · {floor.skipped} étape(s) dans une pièce inconnue du modèle, non montrée(s)</>}
        </p>
        <FloorKey shapes={floor.shapes} lines={new Set(floor.links.map((l) => l.style))} />
      </header>
      <div className="relative" style={{ width: plan.size.width + 2 * PAD, height: plan.size.height + 2 * PAD }}>
        <div className="absolute" style={{ left: PAD, top: PAD + 8 }}>
          <svg className="pointer-events-none absolute overflow-visible" width={plan.size.width} height={plan.size.height} aria-hidden="true">
            <defs>
              {(["normal", "lit", "dim"] as const).map((look) => (
                <marker key={look} id={`floor-arrow-${look}`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
                  <path d="M0 0 8 4 0 8z" style={{ fill: colour(look) }} />
                </marker>
              ))}
            </defs>
            {plan.wraps.map(({ from, to, gapY }) => {
              const a = plan.rects.get(from);
              const b = plan.rects.get(to);
              return a && b ? <Line key={`wrap-${from}`} points={wrapRoute(a, b, gapY)} look="normal" width={3} dash="" moving={false} /> : null;
            })}
            {plan.routes.map(({ link, points }) => {
              const look = lineLook(link.id, link.from, link.to);
              return <Line key={link.id} points={points} look={look} width={STROKE[link.style].width} dash={STROKE[link.style].dash} moving={look === "lit" && !!play} />;
            })}
          </svg>
          {plan.routes.map(({ link, label }) =>
            label && link.verb ? (
              <span
                key={`label-${link.id}`}
                className="pointer-events-none absolute line-clamp-3 w-[80px] -translate-x-1/2 -translate-y-1/2 text-center text-[12.5px] leading-tight text-muted"
                style={{ left: label.x, top: label.y }}
              >
                {link.verb}
              </span>
            ) : null,
          )}
          {plan.orphans && <Band rect={plan.orphans} title="Pièces sans chemin connu" />}
          {plan.strip && <Band rect={plan.strip} title="Autour du projet (ne tourne pas)" />}
          {floor.items.map((item) => {
            const rect = plan.rects.get(item.id);
            const box = boxes.get(item.id);
            if (!rect || !box) return null;
            const room = item.role === "entree" || item.role === "belt" || item.role === "orphan";
            const steps = stepsHere(item.id);
            const parts = machines(item.id);
            const footer = [parts ? `${parts} machine${parts > 1 ? "s" : ""}` : "", steps ? `${steps} étape${steps > 1 ? "s" : ""} ici` : ""].filter(Boolean).join(" · ");
            return (
              <FloorPiece
                key={item.id}
                box={box}
                shape={item.shape}
                rect={rect}
                tag={!room}
                look={lookOf(item.id)}
                selected={selected === item.id}
                badge={item.id === floor.entree && floor.belt.length > 0 ? "entree" : item.id === sortieStore && floor.belt.length > 1 ? "sortie" : null}
                footer={footer || null}
                limit={item.id === sortieStore ? floor.limit : null}
                onSelect={onSelect}
                onEnter={onEnter}
              />
            );
          })}
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

function colour(look: Look): string {
  return look === "lit" ? "var(--u-lamp-line)" : look === "dim" ? "var(--u-line)" : "var(--u-muted)";
}

function Line({ points, look, width, dash, moving }: { points: Point[]; look: Look; width: number; dash: string; moving: boolean }) {
  const path = points.map((p, i) => `${i ? "L" : "M"}${p.x} ${p.y}`).join(" ");
  return (
    <g>
      <path d={path} fill="none" stroke={colour(look)} strokeWidth={look === "lit" ? width + 1 : width} strokeDasharray={dash} markerEnd={`url(#floor-arrow-${look})`} />
      {moving && !STILL && (
        <circle r="5" style={{ fill: "var(--u-lamp)" }}>
          <animateMotion dur="1.6s" repeatCount="indefinite" path={path} />
        </circle>
      )}
    </g>
  );
}

/** The belt going on to the next line, like text: out of the last room, down its right side, back left between the lines, into the first room. */
function wrapRoute(last: Rect, first: Rect, gapY: number): Point[] {
  const out = { x: last.x + last.w, y: last.y + last.h / 2 };
  const into = first.y + first.h / 2;
  const lane = out.x + 34; // outside the gutter lanes of that column
  return [out, { x: lane, y: out.y }, { x: lane, y: gapY }, { x: -18, y: gapY }, { x: -18, y: into }, { x: first.x, y: into }];
}

function Band({ rect, title }: { rect: Rect; title: string }) {
  return (
    <div className="absolute rounded-xl border border-dashed border-line" style={{ left: rect.x, top: rect.y, width: rect.w, height: rect.h }}>
      <p className="px-3 pt-2 text-[12.5px] font-semibold tracking-wide text-faint uppercase">{title}</p>
    </div>
  );
}
