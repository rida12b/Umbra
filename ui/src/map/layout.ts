import ELK from "elkjs/lib/elk.bundled.js";
import type { ElkNode } from "elkjs/lib/elk-api";
import type { MapEdge, MapNode } from "../api";

export const NODE_WIDTH = 216;
export const NODE_HEIGHT = 72;

export interface Placed {
  node: MapNode;
  x: number;
  y: number;
}

const elk = new ELK();

/**
 * Layered layout (ELK): links flow left to right, so a dependency sits to the right of what uses it.
 * Elements without links are packed in rows below, instead of one endless column.
 */
export async function layout(nodes: MapNode[], edges: MapEdge[], vertical: boolean): Promise<Placed[]> {
  const graph: ElkNode = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": vertical ? "DOWN" : "RIGHT",
      "elk.spacing.nodeNode": "28",
      "elk.layered.spacing.nodeNodeBetweenLayers": "72",
      "elk.layered.nodePlacement.strategy": "BRANDES_KOEPF",
      "elk.separateConnectedComponents": "true",
      "elk.spacing.componentComponent": "36",
      "elk.aspectRatio": vertical ? "0.6" : "1.6",
    },
    children: nodes.map((node) => ({ id: node.key, width: NODE_WIDTH, height: NODE_HEIGHT })),
    edges: edges.map((edge, index) => ({
      id: `e${index}`,
      sources: [edge.source],
      targets: [edge.target],
    })),
  };
  const result = await elk.layout(graph);
  const byKey = new Map(nodes.map((node) => [node.key, node]));
  return (result.children ?? []).flatMap((child) => {
    const node = byKey.get(child.id);
    return node ? [{ node, x: child.x ?? 0, y: child.y ?? 0 }] : [];
  });
}
