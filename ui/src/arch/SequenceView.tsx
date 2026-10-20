import { useEffect, useRef } from "react";
import { BLOCK_LABEL } from "./BlockNode";
import type { Sequence } from "./sequence";

const LANE = 220; // width of one block's column
const HEADER = 116; // the block cards at the top
const ROW = 68; // one step

interface Props {
  sequence: Sequence;
  activeStep: number | null;
  onStep: (number: number) => void;
  onPickBlock: (id: string) => void;
}

/** A journey drawn as a sequence: the blocks across the top, the steps in order down the page. */
export function SequenceView({ sequence, activeStep, onStep, onPickBlock }: Props) {
  const { lanes, rows } = sequence;
  const lane = new Map(lanes.map((block, index) => [block.id, index]));
  const x = (id: string | null) => (id !== null && lane.has(id) ? (lane.get(id) ?? 0) * LANE + LANE / 2 : null);
  const width = Math.max(lanes.length, 1) * LANE;
  const height = rows.length * ROW + 24;

  const active = useRef<HTMLButtonElement | null>(null);
  useEffect(() => {
    // Recent browsers return a Promise from scrollIntoView: an effect must return nothing but a clean-up.
    active.current?.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
  }, [activeStep]);

  return (
    <div className="h-full overflow-auto">
      <div className="mx-auto px-6 pb-20" style={{ width: width + 48 }}>
        <div className="relative sticky top-0 z-10 bg-bg" style={{ height: HEADER }}>
          {lanes.map((block, index) => (
            <button
              key={block.id}
              type="button"
              onClick={() => onPickBlock(block.id)}
              className="absolute top-4 flex h-[88px] flex-col rounded-lg border border-lamp-line bg-panel px-3 py-2 text-left hover:bg-raised"
              style={{ left: index * LANE + 8, width: LANE - 16 }}
              title={block.role}
            >
              <span className="text-[12px] text-faint">{BLOCK_LABEL[block.type]}</span>
              <span className="truncate text-[15px] font-semibold text-ink">{block.nom}</span>
              <span className="line-clamp-2 text-[12.5px] leading-snug text-muted">{block.en_bref || block.role}</span>
            </button>
          ))}
        </div>

        <div className="relative" style={{ width, height }}>
          <svg className="absolute inset-0 overflow-visible" width={width} height={height} aria-hidden="true">
            <defs>
              <marker id="seq-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="8" markerHeight="8" orient="auto">
                <path d="M0 0 8 4 0 8z" style={{ fill: "var(--u-lamp-line)" }} />
              </marker>
            </defs>
            {lanes.map((block, index) => (
              <line
                key={block.id}
                x1={index * LANE + LANE / 2}
                x2={index * LANE + LANE / 2}
                y1={0}
                y2={height}
                style={{ stroke: "var(--u-line)" }}
                strokeDasharray="4 5"
              />
            ))}
            {rows.map((row, index) => {
              const y = index * ROW + ROW / 2 + 10;
              const from = x(row.from);
              const to = x(row.to);
              const on = row.number === activeStep;
              if (from === null) return null;
              if (to === null) {
                return <rect key={row.number} x={from - 7} y={y - 7} width={14} height={14} rx={3} style={{ fill: "var(--u-lamp-line)" }} />;
              }
              const gap = from < to ? 6 : -6;
              return (
                <line
                  key={row.number}
                  x1={from + gap}
                  x2={to - gap * 1.6}
                  y1={y}
                  y2={y}
                  markerEnd="url(#seq-arrow)"
                  style={{ stroke: "var(--u-lamp-line)", strokeWidth: on ? 2.6 : 1.6 }}
                />
              );
            })}
          </svg>

          {rows.map((row, index) => {
            const y = index * ROW;
            const from = x(row.from);
            const to = x(row.to);
            const on = row.number === activeStep;
            const left = from === null ? 8 : to === null ? from + 16 : Math.min(from, to);
            const span = from !== null && to !== null ? Math.abs(to - from) : null;
            return (
              <button
                key={row.number}
                ref={on ? active : undefined}
                type="button"
                aria-label={`Étape ${row.number} : ${row.label}`}
                aria-current={on ? "step" : undefined}
                onClick={() => onStep(row.number)}
                className={`absolute left-0 rounded-md ${on ? "bg-lamp-soft" : "hover:bg-raised/60"}`}
                style={{ top: y + 2, height: ROW - 4, width }}
              >
                <span
                  className={`absolute flex items-center gap-1.5 rounded-full border bg-bg py-0.5 pr-2.5 pl-0.5 text-[13px] font-medium whitespace-nowrap text-ink ${
                    on ? "border-lamp-line" : "border-line"
                  } ${span !== null ? "-translate-x-1/2" : ""}`}
                  style={{ top: span !== null ? 4 : ROW / 2 - 12 + 8, left: span !== null ? left + span / 2 : left }}
                >
                  <span className="step-number" data-on={on}>
                    {row.number}
                  </span>
                  {row.label}
                  {from === null && <span className="text-faint"> (hors schéma)</span>}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
