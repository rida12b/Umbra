import { Controls, ReactFlow, type ReactFlowInstance } from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";
import type { ArchBlock, ProjectModel } from "../api";
import { changedUnder, useLive } from "../live";
import type { Theme } from "../theme";
import { StateMessage } from "../ui";
import { placeArchitecture, textWidth, type LayoutArrow, type Placed } from "./archLayout";
import { BLOCK_HEIGHT, BLOCK_WIDTH, BlockNode, type BlockFlowNode } from "./BlockNode";
import { ArrowMarker, FLOW_LABEL_HEIGHT, RoutedEdge, type RoutedFlowEdge } from "./RoutedEdge";
import { flowWords } from "./story";

const nodeTypes = { block: BlockNode };
const edgeTypes = { routed: RoutedEdge };
const LABEL_MAX = 36;
const READABLE_ZOOM = 0.65; // below this the text of a block is too small: scroll instead of shrinking

interface Props {
  model: ProjectModel;
  theme: Theme;
  blocks: ArchBlock[]; // the blocks drawn, with the flows between them
  onPickBlock: (id: string) => void;
}

function label(flow: { verbe?: string; quoi: string }): string {
  const words = flowWords(flow);
  return words.length > LABEL_MAX ? `${words.slice(0, LABEL_MAX - 1)}…` : words;
}

/** Fit the whole drawing, but never below a readable size: then show its top and let the person scroll. */
function frame(flow: ReactFlowInstance<BlockFlowNode, RoutedFlowEdge>, size: { width: number; height: number }) {
  void flow.fitBounds({ x: 0, y: 0, ...size }, { padding: 0.04 }).then(() => {
    if (flow.getZoom() < READABLE_ZOOM) void flow.setViewport({ x: 24, y: 24, zoom: READABLE_ZOOM });
  });
}

/** Blocks and the flows between them, each arrow labelled with what one block does to the other. */
export function ArchCanvas({ model, theme, blocks, onPickBlock }: Props) {
  const [placed, setPlaced] = useState<Placed | null>(null);
  const [failed, setFailed] = useState(false);
  const live = useLive();
  const shown = useMemo(() => new Set(blocks.map((b) => b.id)), [blocks]);
  const flows = useMemo(
    () =>
      model.flux
        .map((flow, index) => ({ flow, key: `f${index}` }))
        .filter(({ flow }) => shown.has(flow.de) && shown.has(flow.vers)),
    [model.flux, shown],
  );

  useEffect(() => {
    let current = true;
    setFailed(false);
    const arrows: LayoutArrow[] = flows.map(({ flow, key }) => ({
      key,
      source: flow.de,
      target: flow.vers,
      labels: [{ width: textWidth(label(flow), 7.8) + 14, height: FLOW_LABEL_HEIGHT }],
    }));
    placeArchitecture(
      blocks.map((block) => ({ id: block.id, width: BLOCK_WIDTH, height: BLOCK_HEIGHT })),
      arrows,
    )
      .then((layout) => current && setPlaced(layout))
      .catch(() => current && setFailed(true));
    return () => {
      current = false;
    };
  }, [blocks, flows]);

  const nodes: BlockFlowNode[] = useMemo(() => {
    if (!placed) return [];
    return blocks.flatMap((block) => {
      const position = placed.boxes.get(block.id);
      if (!position) return [];
      const changed = block.code.some((code) => changedUnder(live, code.chemin));
      return [{ id: block.id, type: "block" as const, position, focusable: false, data: { block, changed, onPick: onPickBlock } }];
    });
  }, [placed, blocks, live, onPickBlock]);

  const edges: RoutedFlowEdge[] = useMemo(() => {
    if (!placed) return [];
    return flows.flatMap(({ flow, key }) => {
      const route = placed.arrows.get(key);
      if (!route) return [];
      const data = { points: route.points, labelAt: route.labels[0] ?? null, text: label(flow), full: flow.quoi };
      return [{ id: key, type: "routed" as const, source: flow.de, target: flow.vers, data }];
    });
  }, [placed, flows]);

  if (failed) return <StateMessage title="Le schéma n'a pas pu être placé.">Le reste de la page reste utilisable.</StateMessage>;
  if (!placed) return <StateMessage>Mise en place du schéma…</StateMessage>;
  return (
    <>
      <ArrowMarker />
      <ReactFlow
        key={`${placed.size.width}x${placed.size.height}`} // a new drawing (live update) is framed again
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        colorMode={theme}
        onNodeClick={(_, node) => onPickBlock(node.id)}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        onInit={(flow) => frame(flow, placed.size)}
        minZoom={0.3}
        maxZoom={1.5}
        preventScrolling={false} // the page scrolls over the diagram; zoom with the buttons or ctrl + wheel
        zoomOnScroll={false}
        panOnScroll={false}
      >
        <Controls showInteractive={false} position="top-right" fitViewOptions={{ padding: 0.04 }} />
      </ReactFlow>
    </>
  );
}
