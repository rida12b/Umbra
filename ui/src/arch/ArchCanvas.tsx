import { Controls, ReactFlow } from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";
import type { ProjectModel } from "../api";
import { changedUnder, useLive } from "../live";
import type { Theme } from "../theme";
import { StateMessage } from "../ui";
import { placeArchitecture, textWidth, type LayoutArrow, type Placed } from "./archLayout";
import { BLOCK_HEIGHT, BLOCK_WIDTH, BlockNode, type BlockFlowNode } from "./BlockNode";
import { ArrowMarker, FLOW_LABEL_HEIGHT, RoutedEdge, type RoutedFlowEdge } from "./RoutedEdge";

const nodeTypes = { block: BlockNode };
const edgeTypes = { routed: RoutedEdge };
const FLOW_TEXT_MAX = 34;
const LEGEND_ROOM = 70; // the legend sits over the bottom of the map

interface Props {
  model: ProjectModel;
  theme: Theme;
  shown: Set<string>; // the blocks drawn: every block that has a flow
  pickedBlock: string | null;
  onPickBlock: (id: string | null) => void;
  onPickFlow: (index: number) => void;
}

function flowText(text: string): string {
  return text.length > FLOW_TEXT_MAX ? `${text.slice(0, FLOW_TEXT_MAX - 1)}…` : text;
}

/** The model's flows between two drawn blocks, with their stable keys (`f<index>` in the model). */
function flows(model: ProjectModel, shown: Set<string>) {
  return model.flux
    .map((flow, index) => ({ flow, key: `f${index}` }))
    .filter(({ flow }) => shown.has(flow.de) && shown.has(flow.vers));
}

/** The architecture overview: the blocks and the flows between them, from the model. */
export function ArchCanvas({ model, theme, shown, pickedBlock, onPickBlock, onPickFlow }: Props) {
  const [placed, setPlaced] = useState<Placed | null>(null);
  const [failed, setFailed] = useState(false);
  const live = useLive();

  useEffect(() => {
    let current = true;
    setFailed(false);
    const arrows: LayoutArrow[] = flows(model, shown).map(({ flow, key }) => ({
      key,
      source: flow.de,
      target: flow.vers,
      labels: [{ width: textWidth(flowText(flow.quoi), 6.6) + 10, height: FLOW_LABEL_HEIGHT }],
    }));
    const boxes = model.blocs
      .filter((block) => shown.has(block.id))
      .map((block) => ({ id: block.id, width: BLOCK_WIDTH, height: BLOCK_HEIGHT }));
    placeArchitecture(boxes, arrows)
      .then((layout) => current && setPlaced(layout))
      .catch(() => current && setFailed(true));
    return () => {
      current = false;
    };
  }, [model, shown]);

  const nodes: BlockFlowNode[] = useMemo(() => {
    if (!placed) return [];
    return model.blocs.flatMap((block) => {
      const position = placed.boxes.get(block.id);
      if (!position) return [];
      const changed = block.code.some((code) => changedUnder(live, code.chemin));
      return [{ id: block.id, type: "block" as const, position, selected: block.id === pickedBlock, data: { block, changed } }];
    });
  }, [placed, model.blocs, pickedBlock, live]);

  const edges: RoutedFlowEdge[] = useMemo(() => {
    if (!placed) return [];
    return flows(model, shown).flatMap(({ flow, key }) => {
      const route = placed.arrows.get(key);
      if (!route) return [];
      const data = { points: route.points, labelAt: route.labels[0] ?? null, text: flowText(flow.quoi) };
      return [{ id: key, type: "routed" as const, source: flow.de, target: flow.vers, data }];
    });
  }, [placed, model, shown]);

  if (failed) return <StateMessage title="Le schéma n'a pas pu être placé.">Les autres vues restent utilisables.</StateMessage>;
  if (!placed) return <StateMessage>Mise en place du schéma…</StateMessage>;
  return (
    <>
      <ArrowMarker />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        colorMode={theme}
        onNodeClick={(_, node) => onPickBlock(node.id)}
        onEdgeClick={(_, edge) => onPickFlow(Number(edge.id.slice(1)))}
        onPaneClick={() => onPickBlock(null)}
        nodesDraggable={false}
        nodesConnectable={false}
        onInit={(flow) =>
          flow.fitBounds({ x: 0, y: 0, width: placed.size.width, height: placed.size.height + LEGEND_ROOM }, { padding: 0.03 })
        }
        minZoom={0.15}
        maxZoom={1.6}
      >
        <Controls showInteractive={false} position="top-right" fitViewOptions={{ padding: 0.03 }} />
      </ReactFlow>
    </>
  );
}
