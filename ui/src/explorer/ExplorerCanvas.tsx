import { Controls, ReactFlow, type ReactFlowInstance } from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";
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
import type { StepOnMap } from "./track";

const nodeTypes = { box: BoxNode, zone: ZoneNode };
const edgeTypes = { arrow: ArrowEdge };
const READABLE_ZOOM = 0.6;
const LARGEST_FIT = 1.1; // a small level is not blown up past this
const FEW_LINKS = 8; // up to this many arrows, their words show all the time
const ZONE_TITLE_GAP = 44;

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

/** Fit the level on screen (zone titles included), never past LARGEST_FIT nor below a readable size. */
function frame(flow: ReactFlowInstance<AnyNode, ArrowFlowEdge>) {
  void flow.fitView({ padding: 0.08, maxZoom: LARGEST_FIT }).then(() => {
    if (flow.getZoom() < READABLE_ZOOM) void flow.setViewport({ x: 32, y: 32 + ZONE_TITLE_GAP, zoom: READABLE_ZOOM });
  });
}

/** One level of the explorer: boxes in their zones, arrows between them, the played step moving. */
export function ExplorerCanvas({ level, theme, selected, play, onSelect, onEnter }: Props) {
  const [placed, setPlaced] = useState<Placed | null>(null);
  const [failed, setFailed] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    setFailed(false);
    setPlaced(null);
    placeArchitecture(
      level.boxes.map((box) => ({
        id: box.id,
        width: BOX_WIDTH,
        height: BOX_HEIGHT,
        column: level.zoned && box.zone ? ZONES.indexOf(box.zone) : undefined,
      })),
      // Room for each arrow's words between the columns, so they never sit on a box.
      level.links.map((link) => ({
        key: link.id,
        source: link.from,
        target: link.to,
        labels: [{ width: textWidth(link.verb || shorten(link.full), 8) + 24, height: 26 }],
      })),
    )
      .then((layout) => current && setPlaced(layout))
      .catch(() => current && setFailed(true));
    return () => {
      current = false;
    };
  }, [level]);

  const lookOf = (box: Box): Look => (play ? (play.step.boxes.includes(box.id) ? "lit" : play.boxes.has(box.id) ? "normal" : "dim") : "normal");

  const nodes: AnyNode[] = useMemo(() => {
    if (!placed) return [];
    const boxes: AnyNode[] = level.boxes.flatMap((box) => {
      const position = placed.boxes.get(box.id);
      if (!position) return [];
      return [{ id: box.id, type: "box" as const, position, data: { box, look: lookOf(box), selected: box.id === selected, onSelect, onEnter } }];
    });
    if (!level.zoned) return boxes;
    // A title over each zone that has boxes, spanning its column.
    const zones: AnyNode[] = ZONES.flatMap((zone) => {
      const xs = level.boxes.filter((b) => b.zone === zone).flatMap((b) => {
        const at = placed.boxes.get(b.id);
        return at ? [at.x] : [];
      });
      if (xs.length === 0) return [];
      const left = Math.min(...xs);
      return [
        {
          id: `zone:${zone}`,
          type: "zone" as const,
          position: { x: left, y: -ZONE_TITLE_GAP },
          data: { title: ZONE_TITLE[zone], width: Math.max(...xs) - left + BOX_WIDTH },
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
      const look: Look = play ? (moving || play.links.has(link.id) ? "lit" : "dim") : "normal";
      const touched = focus !== null && (link.from === focus || link.to === focus);
      const always = level.links.length <= FEW_LINKS && !play; // few arrows: their words never crowd
      const label = moving || touched || always ? link.verb || shorten(link.full) : null;
      return [{ id: link.id, type: "arrow" as const, source: link.from, target: link.to, data: { points: route.points, label, look, moving } }];
    });
    // A played step between two boxes the level has no arrow for: drawn for the time of the step.
    const step = play?.step;
    const [from, to] = step?.boxes ?? [];
    if (step && !step.link && from && to)
      arrows.push({ id: "step", type: "arrow", source: from, target: to, data: { points: null, label: null, look: "lit", moving: true } });
    return arrows;
  }, [placed, level, hovered, selected, play]);

  if (failed) return <StateMessage title="Cette carte n'a pas pu être placée.">Le panneau de droite reste utilisable.</StateMessage>;
  if (!placed) return <StateMessage>Mise en place de la carte…</StateMessage>;
  return (
    <>
      <ArrowHeads />
      <ReactFlow
        key={`${level.key}|${placed.size.width}x${placed.size.height}`} // a new level or drawing is framed again
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
        onInit={frame}
        minZoom={0.25}
        maxZoom={1.6}
        zoomOnScroll={false}
        panOnScroll
      >
        <Controls showInteractive={false} position="top-right" fitViewOptions={{ padding: 0.08 }} />
      </ReactFlow>
    </>
  );
}

function shorten(text: string): string {
  return text.length > 40 ? `${text.slice(0, 39)}…` : text;
}
