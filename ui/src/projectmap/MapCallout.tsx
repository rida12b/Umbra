import { ROW_H, type Callout } from "./lit";
import type { Hint } from "./MapDrawing";

/** Under a lit box: its numbered steps, the place on the left, Claude's 2-4 words on the right (mock). */
export function CalloutRows({ callout, current, hover }: { callout: Callout; current: number | null; hover: (hint: Hint) => object }) {
  const [x1, y1, x2, y2] = callout.connector;
  return (
    <g className="pm-callout">
      <line x1={x1} y1={y1} x2={x2} y2={y2} />
      <rect className="cb" x={callout.x} y={callout.y} width={callout.w} height={callout.h} rx={10} />
      {callout.rows.map(({ step, y }) => {
        const proofs = step.path ? [{ file: step.path, start: 0, end: 0 }] : [];
        const hint = { title: "Pourquoi ici", text: step.why, proofs, guess: false };
        const cur = current === step.n;
        return (
          <g key={step.n} className={`row${cur ? " cur" : ""}`} tabIndex={0} data-step={step.n} aria-label={`${step.n} ${step.label}${step.note ? ` : ${step.note}` : ""}`} {...hover(hint)}>
            <rect className="rh" x={callout.x + 4} y={y} width={callout.w - 8} height={ROW_H} rx={6} />
            <Badge n={step.n} x={callout.x + 22} y={y + 16} cur={cur} />
            <text className="fn" x={callout.x + 44} y={y + 21}>
              {step.label}
            </text>
            {step.note && (
              <text className="why" x={callout.x + callout.w - 14} y={y + 21} textAnchor="end">
                {step.note}
              </text>
            )}
          </g>
        );
      })}
    </g>
  );
}

function Badge({ n, x, y, cur }: { n: number; x: number; y: number; cur: boolean }) {
  return (
    <g className={`pm-badge${cur ? " cur" : ""}`} aria-hidden="true">
      <circle cx={x} cy={y} r={cur ? 15 : 12} />
      <text x={x} y={y + 4.5}>
        {n}
      </text>
    </g>
  );
}
