import ELK from "elkjs/lib/elk.bundled.js";
import type { ElkExtendedEdge, ElkNode } from "elkjs/lib/elk-api";

export interface Point {
  x: number;
  y: number;
}

export interface LayoutBox {
  id: string;
  width: number;
  height: number;
}

/** An arrow and the labels written on it (sizes are estimates of the rendered text). */
export interface LayoutArrow {
  key: string;
  source: string;
  target: string;
  labels: { width: number; height: number }[];
}

export interface Placed {
  size: { width: number; height: number }; // the whole drawing, labels included
  boxes: Map<string, Point>;
  /** Each arrow as a polyline, and the top-left corner of each of its labels, in the same space. */
  arrows: Map<string, { points: Point[]; labels: Point[] }>;
}

const elk = new ELK();

/**
 * Layered layout, left to right (pages are wider than tall): what is used sits right of what uses it. ELK also routes the arrows at right
 * angles and keeps room for their labels, so step labels never sit on a block.
 */
export async function placeArchitecture(boxes: LayoutBox[], arrows: LayoutArrow[]): Promise<Placed> {
  const graph: ElkNode = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.edgeRouting": "ORTHOGONAL",
      "elk.edgeLabels.inline": "false",
      "elk.spacing.nodeNode": "36",
      "elk.spacing.edgeLabel": "4",
      "elk.spacing.edgeEdge": "14",
      "elk.layered.spacing.nodeNodeBetweenLayers": "72",
      "elk.layered.spacing.edgeNodeBetweenLayers": "20",
      "elk.layered.nodePlacement.strategy": "BRANDES_KOEPF",
      "elk.separateConnectedComponents": "true",
      "elk.spacing.componentComponent": "48",
      "elk.aspectRatio": "1.5",
    },
    children: boxes.map((box) => ({ ...box })),
    edges: arrows.map(
      (arrow): ElkExtendedEdge => ({
        id: arrow.key,
        sources: [arrow.source],
        targets: [arrow.target],
        labels: arrow.labels.map((size, index) => ({
          id: `${arrow.key}#${index}`,
          text: " ", // ELK leaves a label without text unplaced
          ...size,
        })),
      }),
    ),
  };
  const result = await elk.layout(graph);
  const placed: Placed = { size: { width: result.width ?? 0, height: result.height ?? 0 }, boxes: new Map(), arrows: new Map() };
  for (const child of result.children ?? []) placed.boxes.set(child.id, { x: child.x ?? 0, y: child.y ?? 0 });
  for (const edge of result.edges ?? []) {
    const points = (edge.sections ?? []).flatMap((s) => [s.startPoint, ...(s.bendPoints ?? []), s.endPoint]);
    const labels = (edge.labels ?? []).map((label) => ({ x: label.x ?? 0, y: label.y ?? 0 }));
    placed.arrows.set(edge.id, { points, labels }); // ELK keeps labels clear of blocks and of each other
  }
  return placed;
}

const CORNER = 8;

/** An SVG path through the points, with small rounded corners. */
export function roundedPath(points: Point[]): string {
  const [start, ...rest] = points;
  if (!start) return "";
  let d = `M ${start.x} ${start.y}`;
  let previous = start;
  rest.forEach((corner, index) => {
    const next = rest[index + 1];
    if (next) {
      const r = Math.min(CORNER, distance(previous, corner) / 2, distance(corner, next) / 2);
      const from = toward(corner, previous, r);
      const to = toward(corner, next, r);
      d += ` L ${from.x} ${from.y} Q ${corner.x} ${corner.y} ${to.x} ${to.y}`;
    } else {
      d += ` L ${corner.x} ${corner.y}`;
    }
    previous = corner;
  });
  return d;
}

function distance(a: Point, b: Point): number {
  return Math.hypot(b.x - a.x, b.y - a.y);
}

function toward(from: Point, to: Point, length: number): Point {
  const d = distance(from, to) || 1;
  return { x: from.x + ((to.x - from.x) * length) / d, y: from.y + ((to.y - from.y) * length) / d };
}

/** Width of a one-line label at the interface size (an estimate: ELK needs sizes before rendering). */
export function textWidth(text: string, charWidth: number): number {
  return Math.ceil(text.length * charWidth);
}
