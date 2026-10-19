import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  type Edge,
  type EdgeMouseHandler,
  type NodeMouseHandler,
} from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";
import type { MapEdge, MapNode, MapView } from "../api";
import type { Theme } from "../theme";
import { ElementNode, type ElementFlowNode } from "./ElementNode";
import { layout } from "./layout";

export type Selection = { type: "node"; node: MapNode } | { type: "edge"; edge: MapEdge } | null;

interface Props {
  view: MapView;
  theme: Theme;
  vertical: boolean;
  selection: Selection;
  onSelect: (selection: Selection) => void;
  onOpen: (node: MapNode) => void;
}

const nodeTypes = { element: ElementNode };

export function edgeId(edge: MapEdge): string {
  return `${edge.source}->${edge.target}:${edge.relation}`;
}

export function MapCanvas({ view, theme, vertical, selection, onSelect, onOpen }: Props) {
  const [nodes, setNodes] = useState<ElementFlowNode[] | null>(null);

  useEffect(() => {
    let current = true;
    setNodes(null);
    layout(view.nodes, view.edges, vertical).then((placed) => {
      if (!current) return;
      setNodes(
        placed.map(({ node, x, y }) => ({
          id: node.key,
          type: "element",
          position: { x, y },
          data: { element: node, vertical },
        })),
      );
    });
    return () => {
      current = false;
    };
  }, [view, vertical]);

  const selectedKey =
    selection?.type === "node" ? selection.node.key : selection ? edgeId(selection.edge) : null;

  const shownNodes = useMemo(
    () => nodes?.map((node) => ({ ...node, selected: node.id === selectedKey })) ?? [],
    [nodes, selectedKey],
  );

  const edges: Edge[] = useMemo(
    () =>
      view.edges.map((edge) => ({
        id: edgeId(edge),
        source: edge.source,
        target: edge.target,
        // Imports are the common case: the line style says enough, the label only counts them.
        label: edge.relation === "imports" ? (edge.count > 1 ? `×${edge.count}` : undefined) : edge.relation,
        className: `link link-${edge.status}`,
        selected: edgeId(edge) === selectedKey,
        markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
        data: { edge },
      })),
    [view.edges, selectedKey],
  );

  const clickNode: NodeMouseHandler<ElementFlowNode> = (_, node) => {
    const element = node.data.element;
    if (element.kind === "group") onOpen(element);
    else onSelect({ type: "node", node: element });
  };
  const openNode: NodeMouseHandler<ElementFlowNode> = (_, node) => onOpen(node.data.element);
  const clickEdge: EdgeMouseHandler = (_, edge) => {
    const found = view.edges.find((candidate) => edgeId(candidate) === edge.id);
    if (found) onSelect({ type: "edge", edge: found });
  };

  if (nodes === null) return <div className="state">Placing elements…</div>;
  return (
    <ReactFlow
      key={view.parent.key}
      nodes={shownNodes}
      edges={edges}
      nodeTypes={nodeTypes}
      colorMode={theme}
      onNodeClick={clickNode}
      onNodeDoubleClick={openNode}
      onEdgeClick={clickEdge}
      onPaneClick={() => onSelect(null)}
      nodesDraggable={false}
      nodesConnectable={false}
      zoomOnDoubleClick={false}
      fitView
      fitViewOptions={{ padding: 0.15, maxZoom: 1.1 }}
      minZoom={0.1}
    >
      <Background gap={24} size={1} />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}
