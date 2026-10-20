import { BaseEdge, EdgeLabelRenderer, type Edge, type EdgeProps } from "@xyflow/react";
import { roundedPath, type Point } from "./archLayout";
import type { StepMark } from "./journeyPath";

export type EdgeLook = "plain" | "lit" | "dim";
export type RoutedData = {
  points: Point[];
  labelAt: Point[];
  look: EdgeLook;
  flowText: string | null; // overview: what goes through
  steps: StepMark[]; // journey: the steps written on this arrow
  activeStep: number | null;
  onStep: (number: number) => void;
};
export type RoutedFlowEdge = Edge<RoutedData, "routed">;

export const STEP_LABEL_HEIGHT = 26;
export const FLOW_LABEL_HEIGHT = 18;

const STROKE = { plain: "var(--u-faint)", lit: "var(--u-lamp)", dim: "var(--u-line)" };

/** An arrow drawn where ELK routed it, with its labels where ELK kept room for them. */
export function RoutedEdge({ id, data, selected }: EdgeProps<RoutedFlowEdge>) {
  if (!data || data.points.length < 2) return null;
  const { points, labelAt, look, flowText, steps, activeStep, onStep } = data;
  const color = selected ? "var(--u-ink)" : STROKE[look];
  return (
    <>
      <BaseEdge
        id={id}
        path={roundedPath(points)}
        markerEnd={`url(#arrow-${look})`}
        style={{ stroke: color, strokeWidth: look === "lit" ? 1.8 : 1.2 }}
        interactionWidth={14}
      />
      <EdgeLabelRenderer>
        {steps.map((mark, index) => {
          const at = labelAt[index];
          if (!at) return null;
          return (
            <button
              key={mark.number}
              type="button"
              className={`nodrag nopan absolute flex items-center gap-1.5 rounded-full border bg-bg py-0.5 pr-2.5 pl-0.5 text-[12px] whitespace-nowrap text-ink ${
                mark.number === activeStep ? "border-lamp shadow-[0_0_0_3px_var(--u-lamp-soft)]" : "border-line"
              }`}
              style={{ transform: `translate(${at.x}px, ${at.y}px)`, pointerEvents: "all" }}
              onClick={(event) => {
                event.stopPropagation(); // the step, not the arrow under it (labels are portals inside the edge)
                onStep(mark.number);
              }}
            >
              <span className="step-number" data-on={mark.number === activeStep}>
                {mark.number}
              </span>
              {mark.label}
            </button>
          );
        })}
        {flowText && labelAt[0] && (
          <span
            className="absolute rounded bg-bg px-1 text-[11px] whitespace-nowrap text-muted"
            style={{ transform: `translate(${labelAt[0].x}px, ${labelAt[0].y}px)` }}
          >
            {flowText}
          </span>
        )}
      </EdgeLabelRenderer>
    </>
  );
}

/** The arrow heads, one per look (SVG markers cannot take their colour from the line). */
export function ArrowMarkers() {
  return (
    <svg className="absolute size-0" aria-hidden="true">
      <defs>
        {(Object.keys(STROKE) as EdgeLook[]).map((look) => (
          <marker key={look} id={`arrow-${look}`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0 8 4 0 8z" style={{ fill: STROKE[look] }} />
          </marker>
        ))}
      </defs>
    </svg>
  );
}
