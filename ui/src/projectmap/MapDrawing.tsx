import type { FocusEvent, MouseEvent } from "react";
import type { Proof, SystemMap } from "../api";
import { aroundText, type DrawnBox, type Geometry } from "./geometry";
import { viewBoxWith, type Callout } from "./lit";
import { CalloutRows } from "./MapCallout";

/** What a hover or a keyboard focus shows: what it is, in a sentence, and the lines that prove it. */
export interface Hint {
  title: string;
  text: string;
  proofs: Proof[];
  guess: boolean; // « supposé »: deduced, not read in the code
  opens?: boolean; // a click shows its inside: « clic : voir dedans → »
}

export type Pointer = MouseEvent<SVGGElement> | FocusEvent<SVGGElement>;

interface Props {
  map: SystemMap;
  drawn: Geometry;
  selected: string | null;
  onSelect: (id: string) => void;
  onHint: (hint: Hint | null, at?: Pointer) => void;
  onAround: (at: Pointer) => void;
  onAroundLeave: () => void;
  lit?: { boxes: Set<string>; callouts: Callout[]; current: number | null } | null; // a path Claude lit (#104)
}

/** The Level 0 map as SVG, drawn as the mock: ENTRÉE left, boxes left → right, ◉ SORTIES right. */
export function MapDrawing({ map, drawn, selected, onSelect, onHint, onAround, onAroundLeave, lit = null }: Props) {
  const titles = Object.fromEntries(map.boxes.map((b) => [b.id, b.title]));
  const hover = (hint: Hint) => ({
    onMouseEnter: (e: Pointer) => onHint(hint, e),
    onMouseMove: (e: Pointer) => onHint(hint, e),
    onMouseLeave: () => onHint(null),
    onFocus: (e: Pointer) => onHint(hint, e),
    onBlur: () => onHint(null),
  });
  return (
    <svg
      className={`pm-map${lit ? " pathmode" : ""}`}
      viewBox={lit ? viewBoxWith(drawn.viewBox, lit.callouts) : drawn.viewBox}
      preserveAspectRatio="xMidYMid meet"
      role="group"
      aria-label={`Carte de ${map.name}`}
    >
      <defs>
        <marker id="pm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,1 L9,5 L0,9 z" />
        </marker>
        <marker id="pm-ahe" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0,1 L9,5 L0,9 z" />
        </marker>
      </defs>
      {drawn.entries.map((entry, i) => (
        <g key={entry.y} className={i > 0 ? "pm-dimmable" : undefined} aria-hidden="true">
          <text className="pm-entry" x={24} y={entry.y + 18}>
            ENTRÉE
          </text>
          <path className="pm-entry-l" d={`M24,${entry.y + 40} L${entry.arrowEnd},${entry.y + 40}`} markerEnd="url(#pm-ahe)" />
        </g>
      ))}
      {drawn.sorties && (
        <text className="pm-colhead" x={drawn.sorties.x} y={drawn.sorties.y} aria-hidden="true">
          SORTIES
        </text>
      )}
      {drawn.arrows.map(({ key, link, path, label, back }) => {
        const [from, to] = back ? [link.target, link.source] : [link.source, link.target];
        const hint = { title: `${titles[from]} → ${titles[to]}`, text: link.detail, proofs: link.proofs, guess: link.inferred };
        return (
          <g key={key} className={`pm-arrow pm-dimmable${link.inferred ? " dash" : ""}`} tabIndex={0} aria-label={`${titles[from]} ${label.text} ${titles[to]}`} {...hover(hint)}>
            <path className="hitp" d={path} />
            <path className="l" d={path} markerEnd="url(#pm-ah)" />
            <text className="pm-lbl" x={label.x} y={label.y} textAnchor={label.anchor}>
              {label.text}
            </text>
          </g>
        );
      })}
      {drawn.boxes.map((drawnBox) => (
        <Box key={drawnBox.box.id} drawn={drawnBox} selected={selected === drawnBox.box.id} lit={!!lit?.boxes.has(drawnBox.box.id)} onSelect={onSelect} hover={hover} />
      ))}
      {drawn.outputs.map(({ output, path, at: [x, y] }) => {
        const hint = { title: `${titles[output.box]} → ${output.label}`, text: "Ce qui sort du projet.", proofs: output.proofs, guess: false };
        return (
          <g key={output.id} className="pm-out pm-dimmable" tabIndex={0} aria-label={`Sortie : ${output.label}`} {...hover(hint)}>
            <path d={path} />
            <circle className="o" cx={x} cy={y} r={8} />
            <circle className="i" cx={x} cy={y} r={3.2} />
            <text x={x + 14} y={y + 5}>
              {output.label}
            </text>
            {output.detail && (
              <text className="d" x={x + 14} y={y + 23}>
                {output.detail}
              </text>
            )}
          </g>
        );
      })}
      {drawn.around && (
        <g
          className="pm-around pm-dimmable"
          tabIndex={0}
          role="button"
          aria-label={`${aroundText(map)} : ne font pas tourner l'appli`}
          onMouseEnter={onAround}
          onFocus={onAround}
          onClick={onAround}
          onMouseLeave={onAroundLeave}
        >
          <rect x={drawn.around.x} y={drawn.around.y} width={drawn.around.w} height={36} rx={18} />
          <text x={drawn.around.x + drawn.around.w / 2} y={drawn.around.y + 23} textAnchor="middle">
            {aroundText(map)}
          </text>
        </g>
      )}
      {lit?.callouts.map((callout) => <CalloutRows key={callout.box} callout={callout} current={lit.current} hover={hover} />)}
    </svg>
  );
}

/** The round « › » top right of a box that has an inside, and « voir dedans → » above it on hover (mock). */
function OpenMark({ rect }: { rect: DrawnBox["rect"] }) {
  const [mx, my] = [rect.x + rect.w - 16, rect.y + 16];
  return (
    <>
      <g className="om" aria-hidden="true">
        <circle cx={mx} cy={my} r={9} />
        <path d={`M${mx - 2},${my - 4} L${mx + 2},${my} L${mx - 2},${my + 4}`} />
      </g>
      <text className="hov" x={rect.x + rect.w} y={rect.y - 9} textAnchor="end" aria-hidden="true">
        voir dedans →
      </text>
    </>
  );
}

function Box({ drawn: { box, rect }, selected, lit, onSelect, hover }: { drawn: DrawnBox; selected: boolean; lit: boolean; onSelect: (id: string) => void; hover: (hint: Hint) => object }) {
  const cx = rect.x + rect.w / 2;
  const hint = { title: [box.title, box.detail].filter(Boolean).join(" · "), text: box.role, proofs: box.proofs, guess: box.inferred, opens: box.opens };
  const common = {
    tabIndex: 0,
    role: "button",
    "aria-pressed": selected,
    "aria-label": [box.title, box.detail, box.folder].filter(Boolean).join(", "),
    "data-box": box.id,
    onClick: () => onSelect(box.id),
    onKeyDown: (e: { key: string; preventDefault: () => void }) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onSelect(box.id);
      }
    },
    ...hover(hint),
  };
  const dash = box.inferred ? " dash" : "";
  // A person is never read in the code: always deduced, said on hover; drawn plain as in the mock.
  if (box.kind === "actor")
    return (
      <g className={`pm-box pm-actor pm-dimmable${lit ? " lit" : ""}${selected ? " sel" : ""}`} {...common}>
        <rect className="hit" x={rect.x} y={rect.y} width={rect.w} height={rect.h} />
        <circle className="head" cx={cx} cy={rect.y + 18} r={12} />
        <path className="body" d={`M${cx - 22},${rect.y + 60} C${cx - 22},${rect.y + 36} ${cx + 22},${rect.y + 36} ${cx + 22},${rect.y + 60}`} />
        <text className="tt" x={cx} y={rect.y + 86} textAnchor="middle">
          {box.title}
        </text>
        <text className="st" x={cx} y={rect.y + 106} textAnchor="middle">
          {box.detail}
        </text>
      </g>
    );
  const titleY = rect.h <= 100 ? rect.y + (box.detail ? 32 : 40) : rect.y + 42;
  const detailY = titleY + 23;
  const folderY = box.detail ? detailY + 22 : titleY + 26;
  return (
    <g className={`pm-box pm-dimmable${dash}${box.opens ? " open" : ""}${lit ? " lit" : ""}${selected ? " sel" : ""}`} {...common}>
      <rect className="b" x={rect.x} y={rect.y} width={rect.w} height={rect.h} rx={10} />
      <text className="tt" x={cx} y={titleY} textAnchor="middle">
        {box.title}
      </text>
      {box.detail && (
        <text className="st" x={cx} y={detailY} textAnchor="middle">
          {box.detail}
        </text>
      )}
      {box.folder && (
        <text className="ft" x={cx} y={folderY} textAnchor="middle">
          {box.folder}
        </text>
      )}
      {box.opens && <OpenMark rect={rect} />}
    </g>
  );
}
