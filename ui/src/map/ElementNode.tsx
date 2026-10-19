import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import type { MapNode, MapStatus, NodeKind } from "../api";

export type ElementData = { element: MapNode; vertical: boolean };
export type ElementFlowNode = Node<ElementData, "element">;

export const KIND_LABEL: Record<NodeKind, string> = {
  application: "Application",
  service: "Service",
  component: "Component",
  module: "Module",
  function: "Function",
  class: "Class",
  method: "Method",
  type: "Type",
  group: "Group",
};

export const STATUS_LABEL: Record<MapStatus, string> = {
  fact: "Fact",
  hypothesis: "Hypothesis",
  declaration: "Declared",
};

export function childrenLabel(element: MapNode): string {
  if (element.kind === "group") return `${element.children} hidden — show all`;
  if (element.children === 0) return "";
  return `${element.children} inside`;
}

export function ElementNode({ data, selected }: NodeProps<ElementFlowNode>) {
  const { element, vertical } = data;
  const inside = childrenLabel(element);
  return (
    <div
      className={`element kind-${element.kind} status-${element.status}${selected ? " selected" : ""}`}
      title={element.path ?? element.label}
    >
      <Handle type="target" position={vertical ? Position.Top : Position.Left} />
      <div className="element-top">
        <span className="element-kind">{KIND_LABEL[element.kind]}</span>
        {element.kind !== "group" && (
          <span className={`badge badge-${element.status}`}>{STATUS_LABEL[element.status]}</span>
        )}
      </div>
      <div className="element-label">{element.label}</div>
      {inside && <div className="element-inside">{inside}</div>}
      <Handle type="source" position={vertical ? Position.Bottom : Position.Right} />
    </div>
  );
}
