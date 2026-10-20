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
    <ul className="divide-y divide-line-soft">
      {view.nodes.map((node) => {
        const outgoing = view.edges.filter((edge) => edge.source === node.key);
        const selected = selection?.type === "node" && selection.node.key === node.key;
        return (
          <li key={node.key} className={`px-4 py-3 ${selected ? "bg-lamp-soft" : ""}`}>
            <button
              type="button"
              className="block w-full text-left"
              aria-pressed={selected}
              onClick={() => (node.kind === "group" ? onOpen(node) : onSelect({ type: "node", node }))}
            >
              <span className="flex text-[12px] text-faint">
                {KIND_LABEL[node.kind]}
                {node.kind !== "group" && <span className="ml-auto">{STATUS_LABEL[node.status]}</span>}
              </span>
              <span className="block text-[14px] font-medium">{node.label}</span>
              {roles[node.key] && <span className="block text-[13px] text-muted">{roles[node.key]}</span>}
              {childrenLabel(node) && <span className="block text-[12px] text-faint">{childrenLabel(node)}</span>}
            </button>
            {outgoing.length > 0 && (
              <ul className="mt-1.5 flex flex-col gap-0.5 pl-3">
                {outgoing.map((edge) => (
                  <li key={`${edge.target}:${edge.relation}`}>
                    <button
                      type="button"
                      className="text-left text-[12.5px] text-muted hover:text-ink"
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
