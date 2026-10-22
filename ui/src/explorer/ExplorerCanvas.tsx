import { Controls, ReactFlow, type ReactFlowInstance } from "@xyflow/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { placeArchitecture, textWidth, type Placed } from "../arch/archLayout";
import type { Theme } from "../theme";
import { StateMessage } from "../ui";
import { ZONE_TITLE, ZONES, type Box, type Level } from "./levels";
import {
  ArrowEdge,
  ArrowHeads,
  BOX_HEIGHT,
  BOX_WIDTH,
  BoxNode,
  ZoneNode,
  type ArrowFlowEdge,
  type BoxFlowNode,
  type Look,
  type ZoneFlowNode,
} from "./mapParts";
import { placeRows, ROW_TITLE_WIDTH, type RowLabel } from "./rowLayout";
import type { StepOnMap } from "./track";

const nodeTypes = { box: BoxNode, zone: ZoneNode };
const edgeTypes = { arrow: ArrowEdge };
const READABLE_ZOOM = 0.75; // below this, the boxes' words are too small to read
const LARGEST_FIT = 1.1; // a small level is not blown up past this
const MARGIN = 24;
const CONTROLS = 48;
const FEW_LINKS = 8; // up to this many arrows, their words show all the time

export interface Play {
  boxes: Set<string>; // every box of the journey (lit)
  links: Set<string>; // every arrow of the journey (lit)
  step: StepOnMap; // the step being played
}

interface Props {
  level: Level;
  theme: Theme;
  selected: string | null;
  play: Play | null;
  onSelect: (id: string | null) => void;
  onEnter: (box: Box) => void;
}

type AnyNode = BoxFlowNode | ZoneFlowNode;

/**
 * The whole level on screen when it fits at a readable size; otherwise its full width, from the top,
 * read by scrolling down (like a page). Never blown up past LARGEST_FIT.
 */
function frame(flow: ReactFlowInstance<AnyNode, ArrowFlowEdge>, size: { width: number; height: number }, screen: HTMLElement | null): boolean {
  const width = screen?.clientWidth ?? 1000;
  const height = screen?.clientHeight ?? 700;
  const across = (width - 2 * MARGIN - CONTROLS) / Math.max(size.width, 1); // the zoom buttons sit top right
  const whole = Math.min(LARGEST_FIT, across, (height - 2 * MARGIN) / Math.max(size.height, 1));
  if (whole >= READABLE_ZOOM) {
    void flow.setViewport({ x: (width - CONTROLS - size.width * whole) / 2, y: (height - size.height * whole) / 2, zoom: whole });
    return false;
  }
  const zoom = Math.max(READABLE_ZOOM, Math.min(LARGEST_FIT, across));
  void flow.setViewport({ x: Math.max(MARGIN, (width - CONTROLS - size.width * zoom) / 2), y: MARGIN, zoom });
  return size.height * zoom + MARGIN > height; // the bottom of the map is out of sight
}

/** One level of the explorer: boxes in their zones, arrows between them, the played step moving. */
export function ExplorerCanvas({ level, theme, selected, play, onSelect, onEnter }: Props) {
  const [layout, setLayout] = useState<{ shape: string; key: string; placed: Drawing } | null>(null);
  const [failed, setFailed] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);
  const screen = useRef<HTMLDivElement>(null);
  const [below, setBelow] = useState(false); // part of the map is under the screen: say so
  const flowRef = useRef<ReactFlowInstance<AnyNode, ArrowFlowEdge> | null>(null);
  const [framed, setFramed] = useState(0); // counts framings: the step is followed after the first one
  // A live refresh rebuilds the level; only a change of its boxes or arrows is laid out again.
  const shape = useMemo(
    () => JSON.stringify([level.key, level.boxes.map((b) => [b.id, b.zone]), level.links.map((l) => [l.id, l.verb, l.full])]),
    [level],
  );
  // The previous drawing of the same level stays on screen (and its zoom) until the new one arrives.
  const placed = layout && layout.key === level.key ? layout.placed : null;

  const stepBoxes = play?.step.boxes.join("|") ?? "";

  // The step being played is brought into sight when it is out of it (the zoom stays the reader's).
  useEffect(() => {
    const flow = flowRef.current;
    const el = screen.current;
    if (!flow || !el || !placed || !stepBoxes) return;
    const at = stepBoxes.split("|").flatMap((id) => {
      const p = placed.boxes.get(id);
      return p ? [p] : [];
    });
    if (at.length === 0) return;
    const { x, y, zoom } = flow.getViewport();
    const top = Math.min(...at.map((p) => p.y));
    const bottom = Math.max(...at.map((p) => p.y)) + BOX_HEIGHT;
    const left = Math.min(...at.map((p) => p.x));
    const right = Math.max(...at.map((p) => p.x)) + BOX_WIDTH;
    const seen = top * zoom + y >= 0 && bottom * zoom + y <= el.clientHeight && left * zoom + x >= 0 && right * zoom + x <= el.clientWidth;
    if (seen) return;
    void flow.setCenter((left + right) / 2, (top + bottom) / 2, { zoom, duration: 400 });
  }, [stepBoxes, placed, framed]);

  useEffect(() => {
    let current = true;
    setFailed(false);
    const arrows = level.links.map((link) => ({ key: link.id, source: link.from, target: link.to }));
    const drawing: Promise<Drawing> = level.zoned
      ? Promise.resolve(
          placeRows(
            level.boxes.map((box) => ({ id: box.id, row: box.zone ? ZONES.indexOf(box.zone) : 0 })),
            arrows,
            { width: BOX_WIDTH, height: BOX_HEIGHT },
          ),
        )
      : placeArchitecture(
          level.boxes.map((box) => ({ id: box.id, width: BOX_WIDTH, height: BOX_HEIGHT })),
          // Room for each arrow's words between the columns, so they never sit on a box.
          arrows.map((arrow, i) => ({ ...arrow, labels: [{ width: textWidth(wordsOf(level.links[i]), 8) + 24, height: 26 }] })),
        );
    drawing
      .then((found) => current && setLayout({ shape, key: level.key, placed: found }))
      .catch(() => current && setFailed(true));
    return () => {
      current = false;
    };
  }, [shape]); // `shape` stands for `level`

  const lookOf = (box: Box): Look => (play ? (play.step.boxes.includes(box.id) ? "lit" : play.boxes.has(box.id) ? "normal" : "dim") : "normal");

  const nodes: AnyNode[] = useMemo(() => {
    if (!placed) return [];
    const boxes: AnyNode[] = level.boxes.flatMap((box) => {
      const position = placed.boxes.get(box.id);
      if (!position) return [];
      const data = { box, look: lookOf(box), selected: box.id === selected, vertical: level.zoned, onSelect, onEnter };
      return [{ id: box.id, type: "box" as const, position, data }];
    });
    if (!level.zoned) return boxes;
    // Each zone's title, left of its row.
    const zones: AnyNode[] = (placed.rows ?? []).flatMap(({ row, y, height }) => {
      const zone = ZONES[row];
      if (!zone) return [];
      return [
        {
          id: `zone:${zone}`,
          type: "zone" as const,
          position: { x: 0, y },
          data: { title: ZONE_TITLE[zone], width: ROW_TITLE_WIDTH - 24, height },
          selectable: false,
          draggable: false,
          focusable: false,
        },
      ];
    });
    return [...zones, ...boxes];
  }, [placed, level, selected, play, onSelect, onEnter]); // lookOf reads `play`

  const edges: ArrowFlowEdge[] = useMemo(() => {
    if (!placed) return [];
    const focus = hovered ?? selected;
    const arrows: ArrowFlowEdge[] = level.links.flatMap((link) => {
      const route = placed.arrows.get(link.id);
      if (!route) return [];
      const moving = play?.step.link === link.id;
      // Only the step being played is lit; the rest of its path stays plain, the others fade.
      const look: Look = play ? (moving ? "lit" : play.links.has(link.id) ? "normal" : "dim") : "normal";
      const touched = focus !== null && (link.from === focus || link.to === focus);
      const always = level.links.length <= FEW_LINKS && !play; // few arrows: their words never crowd
      const label = moving || touched || always ? wordsOf(link) : null;
      const data = { points: route.points, label, labelAt: placed.labels?.get(link.id) ?? null, look, moving };
      return [{ id: link.id, type: "arrow" as const, source: link.from, target: link.to, data }];
    });
    // A played step between two boxes the level has no arrow for: drawn for the time of the step.
    const step = play?.step;
    const [from, to] = step?.boxes ?? [];
    if (step?.arrow && !step.link && from && to)
      arrows.push({ id: "step", type: "arrow", source: from, target: to, data: { points: null, label: step.words, labelAt: null, look: "lit", moving: true } });
    return arrows;
  }, [placed, level, hovered, selected, play]);

  if (failed) return <StateMessage title="Cette carte n'a pas pu être placée.">Le panneau de droite reste utilisable.</StateMessage>;
  if (!placed) return <StateMessage>Mise en place de la carte…</StateMessage>;
  return (
    <div ref={screen} className="absolute inset-0">
      <ArrowHeads />
      <ReactFlow
        key={level.key} // a new level is framed again; a refresh keeps the reader's zoom
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        colorMode={theme}
        onNodeClick={(_, node) => node.type === "box" && onSelect(node.id)}
        onNodeMouseEnter={(_, node) => node.type === "box" && setHovered(node.id)}
        onNodeMouseLeave={() => setHovered(null)}
        onPaneClick={() => onSelect(null)}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        nodesFocusable={false} // the box's own buttons take the focus
        onInit={(flow) => {
          flowRef.current = flow;
          setBelow(frame(flow, placed.size, screen.current));
          setFramed((n) => n + 1);
        }}
        onMoveEnd={(_, view) => setBelow(placed.size.height * view.zoom + view.y > (screen.current?.clientHeight ?? 0) + 8)}
        minZoom={0.25}
        maxZoom={1.6}
        zoomOnScroll={false}
        panOnScroll
      >
        <Controls showInteractive={false} position="top-right" fitViewOptions={{ padding: 0.08 }} />
      </ReactFlow>
      {below && (
        <p className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-bg via-bg/90 to-transparent pt-10 pb-3 text-center text-[14px] font-medium text-muted">
          La suite de la carte est plus bas : faites défiler
        </p>
      )}
    </div>
  );
}

/** A drawing of a level: ELK's, or the rows of a zoned level with their titles and the arrows' words placed. */
type Drawing = Placed & { labels?: Map<string, RowLabel>; rows?: { row: number; y: number; height: number }[] };

/** An arrow's words: its verb, or (models without verbs) its description, cut. */
function wordsOf(link: { verb: string; full: string } | undefined): string {
  if (!link) return "";
  if (link.verb) return link.verb;
  return link.full.length > 40 ? `${link.full.slice(0, 39)}…` : link.full;
}
