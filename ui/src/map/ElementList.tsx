import type { MapNode, MapView } from "../api";
import { KIND_LABEL, STATUS_LABEL, childrenLabel } from "./ElementNode";
import type { Selection } from "./MapCanvas";

interface Props {
  view: MapView;
  roles: Record<string, string>;
  selection: Selection;
  onSelect: (selection: Selection) => void;
  onOpen: (node: MapNode) => void;
}

/**
 * The same view as the graph, for narrow screens where a graph of 12 boxes is unreadable:
 * one row per element, with the links it starts listed under it.
 */
export function ElementList({ view, roles, selection, onSelect, onOpen }: Props) {
  const labels = new Map(view.nodes.map((node) => [node.key, node.label]));
  return (
    <ul className="element-list">
      {view.nodes.map((node) => {
        const outgoing = view.edges.filter((edge) => edge.source === node.key);
        const selected = selection?.type === "node" && selection.node.key === node.key;
        return (
          <li key={node.key}>
            <button
              className={`element-row status-${node.status} kind-${node.kind}${selected ? " selected" : ""}`}
              onClick={() => (node.kind === "group" ? onOpen(node) : onSelect({ type: "node", node }))}
            >
              <span className="element-top">
                <span className="element-kind">{KIND_LABEL[node.kind]}</span>
                {node.kind !== "group" && (
                  <span className={`badge badge-${node.status}`}>{STATUS_LABEL[node.status]}</span>
                )}
              </span>
              <span className="element-label">{node.label}</span>
              {roles[node.key] && <span className="element-role">{roles[node.key]}</span>}
              {childrenLabel(node) && <span className="element-inside">{childrenLabel(node)}</span>}
            </button>
            {outgoing.length > 0 && (
              <ul className="row-links">
                {outgoing.map((edge) => (
                  <li key={`${edge.target}:${edge.relation}`}>
                    <button
                      className={`row-link link-${edge.status}`}
                      onClick={() => onSelect({ type: "edge", edge })}
                    >
                      {edge.relation} → {labels.get(edge.target) ?? edge.target}
                      {edge.count > 1 ? ` ×${edge.count}` : ""}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </li>
        );
      })}
    </ul>
  );
}
