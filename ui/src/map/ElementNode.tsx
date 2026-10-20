import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import type { MapNode, MapStatus, NodeKind } from "../api";
import { NODE_HEIGHT, NODE_WIDTH } from "./layout";

export type ElementData = { element: MapNode; vertical: boolean; role?: string; changed?: boolean };
export type ElementFlowNode = Node<ElementData, "element">;

export const KIND_LABEL: Record<NodeKind, string> = {
  application: "Application",
  service: "Service",
  component: "Composant",
  module: "Fichier",
  function: "Fonction",
  class: "Classe",
  method: "Méthode",
  type: "Type",
  group: "Groupe",
};

export const STATUS_LABEL: Record<MapStatus, string> = {
  fact: "Fait",
  hypothesis: "Hypothèse",
  declaration: "Déclaré",
};

export function childrenLabel(element: MapNode): string {
  if (element.kind === "group") return `${element.children} masqués : tout montrer`;
  if (element.children === 0) return "";
  return `${element.children} à l'intérieur`;
}

export function ElementNode({ data, selected }: NodeProps<ElementFlowNode>) {
  const { element, vertical, role, changed } = data;
  const inside = childrenLabel(element);
  const group = element.kind === "group";
  return (
    <div
      className={`flex flex-col rounded-lg border px-3 py-2.5 ${group ? "border-dashed border-line bg-transparent" : "border-line bg-panel"} ${
        selected ? "ring-2 ring-lamp" : ""
      }`}
      style={{ width: NODE_WIDTH, height: NODE_HEIGHT }}
      title={element.path ?? element.label}
    >
      <Handle type="target" position={vertical ? Position.Top : Position.Left} />
      <span className="flex items-center gap-1.5 text-[11.5px] text-faint">
        {changed && <span className="size-1.5 rounded-full bg-ok" title="Modifié à l'instant" />}
        {KIND_LABEL[element.kind]}
        {!group && <span className="ml-auto">{STATUS_LABEL[element.status]}</span>}
      </span>
      <span className="truncate text-[13.5px] font-semibold text-ink">{element.label}</span>
      {role && <span className="mt-0.5 line-clamp-2 text-[12px] leading-snug text-muted">{role}</span>}
      {inside && <span className="mt-auto text-[12px] text-faint">{inside}</span>}
      <Handle type="source" position={vertical ? Position.Bottom : Position.Right} />
    </div>
  );
}
