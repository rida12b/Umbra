import { BaseEdge, EdgeLabelRenderer, getBezierPath, Handle, Position, type Edge, type EdgeProps, type Node, type NodeProps } from "@xyflow/react";
import { ChevronRight } from "lucide-react";
import { roundedPath, type Point } from "../arch/archLayout";
import type { Box } from "./levels";
import type { RowLabel } from "./rowLayout";

// The pieces the explorer map is drawn with: a box, a zone title, an arrow placed by ELK, and the
// arrow of the step being played when the level has no arrow of its own between those boxes.

export const BOX_WIDTH = 288;
export const BOX_HEIGHT = 148;

export type Look = "normal" | "lit" | "dim";
export type BoxData = {
  box: Box;
  look: Look;
  selected: boolean;
  vertical: boolean; // rows read top to bottom: arrows leave at the bottom, arrive at the top
  onSelect: (id: string) => void;
  onEnter: (box: Box) => void;
};
export type BoxFlowNode = Node<BoxData, "box">;

export function BoxNode({ data }: NodeProps<BoxFlowNode>) {
  const { box, look, selected, vertical, onSelect, onEnter } = data;
  const tone =
    look === "lit" ? "border-lamp-line" : look === "dim" || box.faded ? "border-line-soft opacity-40" : "border-line";
  return (
    // Two separate controls (select, enter): a button inside a button is neither announced nor usable by keyboard.
    <div
      onDoubleClick={() => box.inside > 0 && onEnter(box)}
      className={`flex flex-col rounded-xl border-2 bg-panel px-3.5 py-3 text-left ${tone} ${
        selected ? "shadow-[0_0_0_4px_var(--u-lamp-soft)] ring-2 ring-lamp" : ""
      } ${box.faded ? "border-dashed" : ""}`}
      style={{ width: BOX_WIDTH, height: BOX_HEIGHT }}
    >
      <Handle type="target" position={vertical ? Position.Top : Position.Left} />
      <button
        type="button"
        aria-pressed={selected}
        className="nodrag flex min-h-0 flex-col rounded-md text-left"
        onClick={(event) => {
          event.stopPropagation();
          onSelect(box.id);
        }}
      >
        <span className="line-clamp-2 text-[18px] leading-snug font-semibold text-ink">{box.title}</span>
        <span className="mt-1 line-clamp-2 text-[15px] leading-snug text-muted">{box.words}</span>
      </button>
      <div className="mt-auto flex items-center justify-between gap-2">
        <span className="truncate text-[13px] text-faint">{box.kind}</span>
        {box.inside > 0 && (
        <button
          type="button"
          className="nodrag flex shrink-0 items-center gap-1 rounded-md text-[14px] font-medium text-lamp-ink hover:underline"
          aria-label={`Entrer dedans : ${box.title}`}
          onClick={(event) => {
            event.stopPropagation();
            onEnter(box);
          }}
        >
          Entrer dedans <ChevronRight size={15} aria-hidden="true" />
        </button>
        )}
      </div>
      <Handle type="source" position={vertical ? Position.Bottom : Position.Right} />
    </div>
  );
}

export type ZoneData = { title: string; width: number; height: number };
export type ZoneFlowNode = Node<ZoneData, "zone">;

/** The title of one zone's row (« Ce qui reçoit »), on its left. */
export function ZoneNode({ data }: NodeProps<ZoneFlowNode>) {
  return (
    <div
      className="flex items-center justify-end border-r-2 border-line pr-3 text-right text-[17px] leading-snug font-semibold text-faint"
      style={{ width: data.width, height: data.height }}
    >
      {data.title}
    </div>
  );
}

export type ArrowData = {
  points: Point[] | null; // ELK's route; null: a plain curve between the two boxes (a played step)
  label: string | null; // shown on hover, selection or play only
  labelAt: RowLabel | null; // where the layout keeps room for it; null: the middle of its longest part
  look: Look;
  moving: boolean; // the step being played: a light runs along the arrow
};
export type ArrowFlowEdge = Edge<ArrowData, "arrow">;

const STILL = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const STROKE: Record<Look, string> = { normal: "var(--u-faint)", lit: "var(--u-lamp-line)", dim: "var(--u-line)" };

export function ArrowEdge(props: EdgeProps<ArrowFlowEdge>) {
  const { id, data, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition } = props;
  if (!data) return null;
  const [curve, curveX, curveY] = getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition });
  const path = data.points && data.points.length > 1 ? roundedPath(data.points) : curve;
  const middle = data.labelAt?.at ?? (data.points && data.points.length > 1 ? midpoint(data.points) : { x: curveX, y: curveY });
  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={`url(#explorer-arrow-${data.look})`}
        style={{ stroke: STROKE[data.look], strokeWidth: data.moving ? 3 : data.look === "lit" ? 2 : 1.4 }}
        interactionWidth={16}
      />
      {data.moving && !STILL && (
        <circle r="6" style={{ fill: "var(--u-lamp)" }}>
          <animateMotion dur="1.6s" repeatCount="indefinite" path={path} />
        </circle>
      )}
      {data.label && (
        <EdgeLabelRenderer>
          <span
            className={`absolute rounded-md border px-2 py-0.5 text-[14px] whitespace-nowrap ${
              data.moving ? "border-lamp-line bg-panel font-semibold text-ink" : "border-line-soft bg-bg text-muted"
            }`}
            style={{ transform: `translate(${middle.x}px, ${middle.y}px) translate(-50%, -50%)` }}
          >
            {data.label}
          </span>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

/** The middle of the longest straight part of a route: where its label reads best. */
function midpoint(points: Point[]): Point {
  let best = { length: -1, at: points[0] ?? { x: 0, y: 0 } };
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1];
    const b = points[i];
    if (!a || !b) continue;
    const length = Math.hypot(b.x - a.x, b.y - a.y);
    if (length > best.length) best = { length, at: { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 } };
  }
  return best.at;
}

/** The arrow heads, one per look (SVG markers cannot take their colour from the line). */
export function ArrowHeads() {
  return (
    <svg className="absolute size-0" aria-hidden="true">
      <defs>
        {(Object.keys(STROKE) as Look[]).map((look) => (
          <marker key={look} id={`explorer-arrow-${look}`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0 8 4 0 8z" style={{ fill: STROKE[look] }} />
          </marker>
        ))}
      </defs>
    </svg>
  );
}
