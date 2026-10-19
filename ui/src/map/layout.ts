import ELK from "elkjs/lib/elk.bundled.js";
import type { ElkNode } from "elkjs/lib/elk-api";
import type { MapEdge, MapNode } from "../api";

export const NODE_WIDTH = 240;
export const NODE_HEIGHT = 112; // room for a two-line role under the name

export interface Placed {
  node: MapNode;
  x: number;
  y: number;
}

export interface Size {
  width: number;
  height: number;
}

const elk = new ELK();

/**
 * Layered layout (ELK): links flow left to right, so what is used sits to the right of what uses it.
 * Boxes without links are packed apart, instead of one endless column.
 */
export async function layoutBoxes(
  ids: string[],
  links: [string, string][],
  size: Size,
  vertical: boolean,
): Promise<Map<string, { x: number; y: number }>> {
  const graph: ElkNode = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": vertical ? "DOWN" : "RIGHT",
      "elk.spacing.nodeNode": "32",
      "elk.layered.spacing.nodeNodeBetweenLayers": "96",
      "elk.layered.nodePlacement.strategy": "BRANDES_KOEPF",
      "elk.separateConnectedComponents": "true",
      "elk.spacing.componentComponent": "40",
      "elk.aspectRatio": vertical ? "0.6" : "1.6",
    },
    children: ids.map((id) => ({ id, width: size.width, height: size.height })),
    edges: links.map(([source, target], index) => ({ id: `e${index}`, sources: [source], targets: [target] })),
  };
  const result = await elk.layout(graph);
  return new Map((result.children ?? []).map((child) => [child.id, { x: child.x ?? 0, y: child.y ?? 0 }]));
}

export async function layout(nodes: MapNode[], edges: MapEdge[], vertical: boolean): Promise<Placed[]> {
  const positions = await layoutBoxes(
    nodes.map((node) => node.key),
    edges.map((edge) => [edge.source, edge.target]),
    { width: NODE_WIDTH, height: NODE_HEIGHT },
    vertical,
  );
  return nodes.flatMap((node) => {
    const position = positions.get(node.key);
    return position ? [{ node, ...position }] : [];
  });
}
