import { BaseEdge, EdgeLabelRenderer, type Edge, type EdgeProps } from "@xyflow/react";
import { roundedPath, type Point } from "./archLayout";

export type RoutedData = {
  points: Point[];
  labelAt: Point | null;
  text: string; // what one block does to the other, shortened
  full: string; // the whole description, on hover
};
export type RoutedFlowEdge = Edge<RoutedData, "routed">;

export const FLOW_LABEL_HEIGHT = 20;

/** A flow drawn where ELK routed it, with what goes through written on the line. */
export function RoutedEdge({ id, data, selected }: EdgeProps<RoutedFlowEdge>) {
  if (!data || data.points.length < 2) return null;
  const { points, labelAt, text, full } = data;
  return (
    <>
      <BaseEdge
        id={id}
        path={roundedPath(points)}
        markerEnd="url(#arrow-flow)"
        style={{ stroke: selected ? "var(--u-ink)" : "var(--u-faint)", strokeWidth: 1.4 }}
        interactionWidth={14}
      />
      {labelAt && (
        <EdgeLabelRenderer>
          <span
            className="absolute rounded bg-bg px-1.5 text-[13px] whitespace-nowrap text-muted"
            style={{ transform: `translate(${labelAt.x}px, ${labelAt.y}px)`, pointerEvents: "all" }}
            title={full}
          >
            {text}
          </span>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

/** The arrow head (SVG markers cannot take their colour from the line). */
export function ArrowMarker() {
  return (
    <svg className="absolute size-0" aria-hidden="true">
      <defs>
        <marker id="arrow-flow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0 0 8 4 0 8z" style={{ fill: "var(--u-faint)" }} />
        </marker>
      </defs>
    </svg>
  );
}
