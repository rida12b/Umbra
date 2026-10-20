import {
  Controls,
  MarkerType,
  ReactFlow,
  type Edge,
  type EdgeMouseHandler,
  type NodeMouseHandler,
} from "@xyflow/react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { MapEdge, MapNode, MapView } from "../api";
import type { Theme } from "../theme";
import { ElementNode, type ElementFlowNode } from "./ElementNode";
import { layout } from "./layout";
import { changedUnder, useLive } from "../live";
import { StateMessage } from "../ui";

export type Selection = { type: "node"; node: MapNode } | { type: "edge"; edge: MapEdge } | null;

interface Props {
  view: MapView;
  roles: Record<string, string>;
  theme: Theme;
  vertical: boolean;
  selection: Selection;
  onSelect: (selection: Selection) => void;
  onOpen: (node: MapNode) => void;
}

const nodeTypes = { element: ElementNode };
const DOUBLE_CLICK_MS = 400;

/** The code an element stands for: its file or folder, or a service's code folder. */
export function nodePath(element: MapNode): string | null {
  return element.path ?? element.details.code?.[0] ?? null;
}

export function edgeId(edge: MapEdge): string {
  return `${edge.source}->${edge.target}:${edge.relation}`;
}

export function MapCanvas({ view, roles, theme, vertical, selection, onSelect, onOpen }: Props) {
  const [nodes, setNodes] = useState<ElementFlowNode[] | null>(null);
  const live = useLive();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let current = true;
    setNodes(null);
    setFailed(false);
    layout(view.nodes, view.edges, vertical)
      .then((placed) => {
        if (!current) return;
        setNodes(
          placed.map(({ node, x, y }) => ({
            id: node.key,
            type: "element",
            position: { x, y },
            data: { element: node, vertical },
          })),
        );
      })
      .catch(() => current && setFailed(true));
    return () => {
      current = false;
    };
  }, [view, vertical]);

  const selectedKey =
    selection?.type === "node" ? selection.node.key : selection ? edgeId(selection.edge) : null;

  const shownNodes = useMemo(
    () =>
      nodes?.map((node) => ({
        ...node,
        selected: node.id === selectedKey,
        data: { ...node.data, role: roles[node.id], changed: changedUnder(live, nodePath(node.data.element)) },
      })) ?? [],
    [nodes, selectedKey, roles, live],
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

  // A second click on the same block soon after opens it. Not the browser's dblclick: the first
  // click selects the block and redraws it, so the second lands on a new element and no dblclick fires.
  const lastClick = useRef<{ id: string; at: number } | null>(null);
  const clickNode: NodeMouseHandler<ElementFlowNode> = (_, node) => {
    const element = node.data.element;
    const now = Date.now();
    const again = lastClick.current?.id === node.id && now - lastClick.current.at < DOUBLE_CLICK_MS;
    lastClick.current = again ? null : { id: node.id, at: now };
    if (element.kind === "group" || again) onOpen(element);
    else onSelect({ type: "node", node: element });
  };
  const clickEdge: EdgeMouseHandler = (_, edge) => {
    const found = view.edges.find((candidate) => edgeId(candidate) === edge.id);
    if (found) onSelect({ type: "edge", edge: found });
  };

  if (failed) return <StateMessage title="Cette vue n'a pas pu être placée.">Essayez un autre niveau du code.</StateMessage>;
  if (nodes === null) return <StateMessage>Mise en place des éléments…</StateMessage>;
  return (
    <ReactFlow
      key={view.parent.key}
      nodes={shownNodes}
      edges={edges}
      nodeTypes={nodeTypes}
      colorMode={theme}
      onNodeClick={clickNode}
      onNodeDoubleClick={(_, node) => onOpen(node.data.element)}
      onEdgeClick={clickEdge}
      onPaneClick={() => onSelect(null)}
      nodesDraggable={false}
      nodesConnectable={false}
      zoomOnDoubleClick={false}
      fitView
      fitViewOptions={{ padding: 0.15, maxZoom: 1.1 }}
      minZoom={0.1}
    >
      <Controls showInteractive={false} position="top-right" />
    </ReactFlow>
  );
}
