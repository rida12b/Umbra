import type { InsideMap } from "../../api";
import type { Hint, Pointer } from "../MapDrawing";
import { insideAroundText, type DrawnPart, type InsideGeometry } from "./insideGeometry";

interface Props {
  inside: InsideMap;
  drawn: InsideGeometry;
  selected: string | null;
  onSelect: (id: string) => void;
  onStub: (neighbour: string) => void;
  onHint: (hint: Hint | null, at?: Pointer) => void;
  onAround: (at: Pointer) => void;
  onAroundLeave: () => void;
}

/** Level 1 as SVG, drawn as the mock: ENTRÉE over the stub on the left, parts left → right, SORTIES over the stubs on the right. */
export function InsideDrawing({ inside, drawn, selected, onSelect, onStub, onHint, onAround, onAroundLeave }: Props) {
  const names = Object.fromEntries(inside.parts.map((p) => [p.id, p.kind === "stub" ? stubName(p.title, p.detail) : p.title]));
  const hover = (hint: Hint) => ({
    onMouseEnter: (e: Pointer) => onHint(hint, e),
    onMouseMove: (e: Pointer) => onHint(hint, e),
    onMouseLeave: () => onHint(null),
    onFocus: (e: Pointer) => onHint(hint, e),
    onBlur: () => onHint(null),
  });
  return (
    <svg className="pm-map pm-inside" viewBox={drawn.viewBox} preserveAspectRatio="xMidYMid meet" role="group" aria-label={`Dans ${inside.title}`}>
      <defs>
        <marker id="pm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,1 L9,5 L0,9 z" />
        </marker>
      </defs>
      {drawn.entry && (
        <text className="pm-entry" x={drawn.entry.x} y={drawn.entry.y} aria-hidden="true">
          ENTRÉE
        </text>
      )}
      {drawn.sorties && (
        <text className="pm-colhead" x={drawn.sorties.x} y={drawn.sorties.y} aria-hidden="true">
          SORTIES
        </text>
      )}
      {drawn.arrows.map(({ key, link, path, label }) => {
        const hint = { title: `${names[link.source]} → ${names[link.target]}`, text: link.detail, proofs: link.proofs, guess: link.inferred };
        return (
          <g key={key} className={`pm-arrow${link.inferred ? " dash" : ""}`} tabIndex={0} aria-label={`${names[link.source]} ${label.text} ${names[link.target]}`} {...hover(hint)}>
            <path className="hitp" d={path} />
            <path className="l" d={path} markerEnd="url(#pm-ah)" />
            <text className="pm-lbl" x={label.x} y={label.y} textAnchor={label.anchor}>
              {label.text}
            </text>
          </g>
        );
      })}
      {drawn.parts.map((part) => (
        <Part key={part.part.id} drawn={part} selected={selected === part.part.id} onSelect={onSelect} onStub={onStub} hover={hover} />
      ))}
      {drawn.outputs.map(({ output, path, at: [x, y] }) => {
        const hint = { title: `${names[output.box]} → ${output.label}`, text: "Ce qui sort du projet.", proofs: output.proofs, guess: false };
        return (
          <g key={output.id} className="pm-out" tabIndex={0} aria-label={`Sortie : ${output.label}`} {...hover(hint)}>
            <path d={path} />
            <circle className="o" cx={x} cy={y} r={8} />
            <circle className="i" cx={x} cy={y} r={3.2} />
            <text x={x + 14} y={y + 5}>
              {output.label}
            </text>
          </g>
        );
      })}
      {drawn.around && (
        <g className="pm-around" tabIndex={0} role="button" aria-label={`${insideAroundText(inside)} : ne font pas tourner l'appli`} onMouseEnter={onAround} onFocus={onAround} onClick={onAround} onMouseLeave={onAroundLeave}>
          <rect x={drawn.around.x} y={drawn.around.y} width={drawn.around.w} height={40} rx={20} />
          <text x={drawn.around.x + drawn.around.w / 2} y={drawn.around.y + 25} textAnchor="middle">
            {insideAroundText(inside)}
          </text>
        </g>
      )}
    </svg>
  );
}

/** « vers Base » + « ◉ ligne enregistrée » → « Base »; « depuis » + « Application web » → « Application web ». */
function stubName(title: string, detail: string): string {
  return title.startsWith("vers ") ? title.slice(5) : detail;
}

interface PartProps {
  drawn: DrawnPart;
  selected: boolean;
  onSelect: (id: string) => void;
  onStub: (neighbour: string) => void;
  hover: (hint: Hint) => object;
}

function Part({ drawn: { part, rect, chips }, selected, onSelect, onStub, hover }: PartProps) {
  const cx = rect.x + rect.w / 2;
  const stub = part.kind === "stub";
  const act = () => (stub ? onStub(part.neighbour) : onSelect(part.id));
  const hint = stub
    ? { title: stubName(part.title, part.detail), text: part.role, proofs: part.proofs, guess: part.inferred, action: part.opens ? "clic : voir dedans →" : "clic : revenir à la vue d'ensemble" }
    : { title: part.title, text: part.role, proofs: part.proofs, guess: part.inferred };
  const common = {
    tabIndex: 0,
    role: "button",
    "aria-pressed": stub ? undefined : selected,
    "aria-label": [part.title, part.detail.replace("◉ ", ""), ...part.folders].filter(Boolean).join(", "),
    "data-part": part.id,
    onClick: act,
    onKeyDown: (e: { key: string; preventDefault: () => void }) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        act();
      }
    },
    ...hover(hint),
  };
  const className = `pm-box${stub ? " pm-stub" : ""}${part.inferred ? " dash" : ""}${selected ? " sel" : ""}`;
  if (stub) {
    const y0 = rect.y + rect.h / 2 - 10 + 5;
    return (
      <g className={className} {...common}>
        <rect className="b" x={rect.x} y={rect.y} width={rect.w} height={rect.h} rx={10} />
        <text className="tt" x={cx} y={y0} textAnchor="middle">
          {part.title}
        </text>
        <text className="st" x={cx} y={y0 + 20} textAnchor="middle">
          {part.detail}
        </text>
      </g>
    );
  }
  const lines: { cls: string; text: string }[] = [];
  if (part.detail && !chips.length) lines.push({ cls: "st", text: part.detail });
  for (const folder of part.folders) lines.push({ cls: "ft", text: folder });
  const titleY = chips.length ? rect.y + 32 : rect.h <= 100 ? rect.y + (part.detail ? 32 : 40) : rect.y + 42;
  let y = titleY;
  return (
    <g className={className} {...common}>
      <rect className="b" x={rect.x} y={rect.y} width={rect.w} height={rect.h} rx={10} />
      <text className="tt" x={cx} y={titleY} textAnchor="middle">
        {part.title}
      </text>
      {lines.map((line, i) => {
        y += i === 0 ? (line.cls === "st" ? 23 : chips.length ? 22 : 26) : line.cls === "ft" && lines[i - 1]?.cls === "ft" ? 19 : 22;
        return (
          <text key={`${line.cls}${line.text}`} className={line.cls} x={cx} y={y} textAnchor="middle">
            {line.text}
          </text>
        );
      })}
      {chips.map((chip) => (
        <g
          key={chip.file}
          className="pm-chip"
          tabIndex={0}
          aria-label={chip.label}
          {...hover({ title: chip.label, text: "", proofs: [{ file: chip.file, start: 0, end: 0 }], guess: false })}
        >
          <rect x={chip.rect.x} y={chip.rect.y} width={chip.rect.w} height={chip.rect.h} rx={6} />
          <text x={chip.rect.x + chip.rect.w / 2} y={chip.rect.y + 18.5} textAnchor="middle">
            {chip.label}
          </text>
        </g>
      ))}
    </g>
  );
}
