import { Controls, ReactFlow, useReactFlow } from "@xyflow/react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ProjectModel } from "../api";
import { changedUnder, useLive } from "../live";
import type { Theme } from "../theme";
import { StateMessage } from "../ui";
import { placeArchitecture, textWidth, type LayoutArrow, type Placed } from "./archLayout";
import { BLOCK_WIDTH, BlockNode, blockHeight, type BlockFlowNode } from "./BlockNode";
import type { JourneyPath, StepMark } from "./journeyPath";
import { ArrowMarkers, FLOW_LABEL_HEIGHT, RoutedEdge, STEP_LABEL_HEIGHT, type RoutedFlowEdge } from "./RoutedEdge";

const nodeTypes = { block: BlockNode };
const edgeTypes = { routed: RoutedEdge };
const FLOW_TEXT_MAX = 34;

interface Props {
  model: ProjectModel;
  theme: Theme;
  path: JourneyPath | null; // the journey lit on the map, if one is chosen
  shown: Set<string>; // the blocks drawn: a journey's blocks, or every block that has a flow
  pathKey: string; // changes when the journey (or the model) changes: lay out again
  activeStep: number | null;
  pickedBlock: string | null;
  onPickBlock: (id: string | null) => void;
  onPickFlow: (index: number) => void;
  onStep: (number: number) => void;
}

function stepLabelSize(mark: StepMark) {
  return { width: 38 + textWidth(mark.label, 6.8), height: STEP_LABEL_HEIGHT };
}

function flowText(text: string): string {
  return text.length > FLOW_TEXT_MAX ? `${text.slice(0, FLOW_TEXT_MAX - 1)}…` : text;
}

const READABLE_ZOOM = 0.95;

/** Where the active step is written: the middle of its label on an arrow, or of its block. */
function stepCentre(layout: Placed, path: JourneyPath | null, step: number | null) {
  if (!path || step === null) return null;
  for (const [key, marks] of path.onEdges) {
    const index = marks.findIndex((mark) => mark.number === step);
    const at = layout.arrows.get(key)?.labels[index];
    if (index >= 0 && at) return { x: at.x + 60, y: at.y + STEP_LABEL_HEIGHT / 2 };
  }
  for (const [block, marks] of path.inBlocks) {
    const at = layout.boxes.get(block);
    if (at && marks.some((mark) => mark.number === step))
      return { x: at.x + BLOCK_WIDTH / 2, y: at.y + blockHeight(marks.length) / 2 };
  }
  return null;
}

/** When the person picks another step, the map glides to it at a readable size (not on first show). */
function StepFocus({ target }: { target: { x: number; y: number } | null }) {
  const flow = useReactFlow();
  const first = useRef(true);
  const key = target ? `${Math.round(target.x)},${Math.round(target.y)}` : "";
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    if (!target) return;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    void flow.setCenter(target.x, target.y, { zoom: Math.max(flow.getZoom(), READABLE_ZOOM), duration: still ? 0 : 400 });
  }, [key]); // `target` is a new object on each render: `key` says when it really moved
  return null;
}

/** The model's flows between two drawn blocks, with their stable keys (`f<index>` in the model). */
function flows(model: ProjectModel, shown: Set<string>) {
  return model.flux
    .map((flow, index) => ({ flow, key: `f${index}` }))
    .filter(({ flow }) => shown.has(flow.de) && shown.has(flow.vers));
}

/** The architecture map: blocks and flows from the model; a chosen journey lit, its steps written on it. */
export function ArchCanvas(props: Props) {
  const { model, theme, path, shown, pathKey, activeStep, pickedBlock, onPickBlock, onPickFlow, onStep } = props;
  const [placed, setPlaced] = useState<{ key: string; layout: Placed } | null>(null);
  const [failed, setFailed] = useState(false);
  const live = useLive();

  useEffect(() => {
    let current = true;
    const arrows: LayoutArrow[] = flows(model, shown).map(({ flow, key }) => {
      const steps = path?.onEdges.get(key);
      const labels = path
        ? (steps ?? []).map(stepLabelSize)
        : [{ width: textWidth(flowText(flow.quoi), 6) + 8, height: FLOW_LABEL_HEIGHT }];
      return { key, source: flow.de, target: flow.vers, labels };
    });
    for (const extra of path?.extraEdges ?? [])
      arrows.push({ ...extra, labels: (path?.onEdges.get(extra.key) ?? []).map(stepLabelSize) });
    const boxes = model.blocs.filter((block) => shown.has(block.id)).map((block) => ({
      id: block.id,
      width: BLOCK_WIDTH,
      height: blockHeight(path?.inBlocks.get(block.id)?.length ?? 0),
    }));
    placeArchitecture(boxes, arrows)
      .then((layout) => current && setPlaced({ key: pathKey, layout }))
      .catch(() => current && setFailed(true));
    return () => {
      current = false;
    };
  }, [model, path, shown, pathKey]);

  const nodes: BlockFlowNode[] = useMemo(() => {
    if (!placed) return [];
    return model.blocs.flatMap((block) => {
      const position = placed.layout.boxes.get(block.id);
      if (!position) return [];
      const look = path ? (path.blocks.has(block.id) ? "lit" : "dim") : "plain";
      return [
        {
          id: block.id,
          type: "block" as const,
          position,
          selected: block.id === pickedBlock,
          data: {
            block,
            look,
            inside: path?.inBlocks.get(block.id) ?? [],
            activeStep,
            changed: block.code.some((code) => changedUnder(live, code.chemin)),
            onStep,
          },
        },
      ];
    });
  }, [placed, model.blocs, path, pickedBlock, activeStep, live, onStep]);

  const edges: RoutedFlowEdge[] = useMemo(() => {
    if (!placed) return [];
    const all = [
      ...flows(model, shown).map(({ flow, key }) => ({ key, source: flow.de, target: flow.vers, text: flow.quoi })),
      ...(path?.extraEdges ?? []).map((extra) => ({ ...extra, text: "" })),
    ];
    return all.flatMap((arrow) => {
      const route = placed.layout.arrows.get(arrow.key);
      if (!route) return [];
      const look = path ? (path.edges.has(arrow.key) ? "lit" : "dim") : "plain";
      return [
        {
          id: arrow.key,
          type: "routed" as const,
          source: arrow.source,
          target: arrow.target,
          data: {
            points: route.points,
            labelAt: route.labels,
            look,
            flowText: path ? null : flowText(arrow.text),
            steps: path?.onEdges.get(arrow.key) ?? [],
            activeStep,
            onStep,
          },
        },
      ];
    });
  }, [placed, model, shown, path, activeStep, onStep]);

  if (failed) return <StateMessage title="Le schéma n'a pas pu être placé.">Les autres vues restent utilisables.</StateMessage>;
  if (!placed) return <StateMessage>Mise en place du schéma…</StateMessage>;
  return (
    <>
      <ArrowMarkers />
      <ReactFlow
        key={placed.key} // a new journey is framed whole
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        colorMode={theme}
        onNodeClick={(_, node) => onPickBlock(node.id)}
        onEdgeClick={(_, edge) => edge.id.startsWith("f") && onPickFlow(Number(edge.id.slice(1)))}
        onPaneClick={() => onPickBlock(null)}
        nodesDraggable={false}
        nodesConnectable={false}
        onInit={(flow) => flow.fitBounds({ x: 0, y: 0, ...placed.layout.size }, { padding: 0.03 })}
        minZoom={0.15}
        maxZoom={1.6}
      >
        <Controls showInteractive={false} position="top-right" fitViewOptions={{ padding: 0.03 }} />
        <StepFocus target={stepCentre(placed.layout, path, activeStep)} />
      </ReactFlow>
    </>
  );
}
