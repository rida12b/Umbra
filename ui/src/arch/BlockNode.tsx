import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import type { ArchBlock, BlockType } from "../api";

export type BlockData = { block: ArchBlock; changed: boolean };
export type BlockFlowNode = Node<BlockData, "block">;

export const BLOCK_WIDTH = 232;
export const BLOCK_HEIGHT = 124; // kind, a name on two lines at most, a few words on two lines at most

export const BLOCK_LABEL: Record<BlockType, string> = {
  user: "Personne",
  frontend: "Interface",
  backend: "Serveur",
  worker: "Tâche de fond",
  database: "Base de données",
  storage: "Stockage",
  queue: "File de messages",
  external: "Service externe",
  ml_model: "Modèle IA",
  device: "Appareil",
  cli: "Script / CLI",
  library: "Bibliothèque",
  docs: "Documentation",
  tests: "Tests",
  infra: "Infrastructure",
};

export function BlockNode({ data, selected }: NodeProps<BlockFlowNode>) {
  const { block, changed } = data;
  return (
    <div
      className={`flex flex-col rounded-lg border border-line bg-panel px-3 py-2.5 ${selected ? "ring-2 ring-lamp-line" : ""}`}
      style={{ width: BLOCK_WIDTH, height: BLOCK_HEIGHT }}
      title={block.role}
    >
      <Handle type="target" position={Position.Top} />
      <span className="flex items-center gap-1.5 text-[12px] text-faint">
        {changed && <span className="size-1.5 rounded-full bg-ok" title="Code modifié à l'instant" />}
        {BLOCK_LABEL[block.type]}
      </span>
      <span className="line-clamp-2 text-[15px] leading-snug font-semibold text-ink">{block.nom}</span>
      <span className="mt-0.5 line-clamp-2 text-[13px] leading-snug text-muted">{block.en_bref || block.role}</span>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
