import type { LinkStyle } from "./floor";
import type { Point } from "./floorLayout";

// The lines of the floor and of an open room, from mockup B: the data belt (a thick yellow band with
// dark slats), the dashed answer, the thin grey control line. Shared so a room's belt is the floor's.

const STILL = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
// The mockup's lines (V11, V16, V9): the belt thick in the data colour, the reply thin and dashed, control thin grey.
export const STROKE: Record<LinkStyle | "belt", { width: number; dash: string; colour: string }> = {
  belt: { width: 5, dash: "", colour: "var(--fl-data)" },
  data: { width: 2, dash: "", colour: "var(--fl-data)" }, // a supplier's short line: thinner than the belt, never mistaken for it
  reply: { width: 2, dash: "7 6", colour: "var(--fl-data)" },
  lookup: { width: 1.3, dash: "", colour: "var(--fl-control)" },
  control: { width: 1.3, dash: "", colour: "var(--fl-control)" },
};

/** The arrow heads, in pixels (not scaled by the stroke: a 5 px belt would get a 25 px arrow). */
export function LineMarkers() {
  return (
    <defs>
      <marker id="fl-arrow-data" viewBox="0 0 8 8" refX="6" refY="4" markerWidth="14" markerHeight="14" markerUnits="userSpaceOnUse" orient="auto">
        <path d="M0 0 8 4 0 8z" style={{ fill: "var(--fl-data)" }} />
      </marker>
      <marker id="fl-arrow-hl" viewBox="0 0 8 8" refX="6" refY="4" markerWidth="14" markerHeight="14" markerUnits="userSpaceOnUse" orient="auto">
        <path d="M0 0 8 4 0 8z" style={{ fill: "var(--fl-hl)" }} />
      </marker>
      <marker id="fl-arrow-ctl" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" orient="auto">
        <path d="M0 0 8 4 0 8z" style={{ fill: "var(--fl-control)" }} />
      </marker>
    </defs>
  );
}

export function Line({ points, kind, lit, dim = false, back = false }: { points: Point[]; kind: LinkStyle | "belt"; lit: boolean; dim?: boolean; back?: boolean }) {
  const path = points.map((p, i) => `${i ? "L" : "M"}${p.x} ${p.y}`).join(" ");
  // The particle runs the way the data goes: backwards on a line drawn the other way (an answer coming back).
  const run = (back ? [...points].reverse() : points).map((p, i) => `${i ? "L" : "M"}${p.x} ${p.y}`).join(" ");
  const style = STROKE[kind];
  const colour = lit ? "var(--fl-hl)" : style.colour;
  const marker = kind === "control" || kind === "lookup" ? "url(#fl-arrow-ctl)" : lit ? "url(#fl-arrow-hl)" : "url(#fl-arrow-data)";
  return (
    <g opacity={dim && !lit ? 0.55 : 1}>
      {kind === "belt" && <path d={path} fill="none" stroke="var(--fl-belt-edge)" strokeWidth={style.width + 4} strokeLinejoin="round" />}
      <path d={path} fill="none" stroke={colour} strokeWidth={lit ? style.width + 1 : style.width} strokeDasharray={style.dash} strokeLinejoin="round" markerEnd={marker} />
      {/* The belt's slats (V11): short dark marks along the yellow band, like a conveyor. */}
      {kind === "belt" && <path d={path} fill="none" stroke="var(--fl-belt-slat)" strokeWidth={2} strokeDasharray="2 12" opacity={0.75} />}
      {lit && !STILL && (
        <circle r="5" style={{ fill: "var(--fl-hl)" }}>
          <animateMotion dur="1.6s" repeatCount="indefinite" path={run} />
        </circle>
      )}
    </g>
  );
}
