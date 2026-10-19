import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import type { ArchBlock, BlockType } from "../api";

export type BlockData = { block: ArchBlock };
export type BlockFlowNode = Node<BlockData, "block">;

export const BLOCK_LABEL: Record<BlockType, string> = {
  user: "Utilisateur",
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

// One simple pictogram per kind of block (24×24, stroke only), so the role reads before the text.
const ICON: Record<BlockType, string> = {
  user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0",
  frontend: "M3 5h18v12H3zM8 21h8M12 17v4",
  backend: "M4 4h16v6H4zM4 14h16v6H4zM8 7h.01M8 17h.01",
  worker: "M12 3v3M12 18v3M3 12h3M18 12h3M6 6l2 2M16 16l2 2M6 18l2-2M16 8l2-2M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6",
  database: "M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3Zm0 0v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3",
  storage: "M3 7h18v13H3zM3 7l3-4h12l3 4",
  queue: "M3 6h4v12H3zM10 6h4v12h-4zM17 6h4v12h-4z",
  external: "M7 18a5 5 0 0 1 0-10 6 6 0 0 1 11 2 4 4 0 0 1 0 8z",
  ml_model: "M9 3h6v4H9zM5 9h14v12H5zM9 13h.01M15 13h.01M9 17h6",
  device: "M7 3h10v18H7zM11 18h2",
  cli: "M4 5h16v14H4zM7 9l3 3-3 3M12 15h5",
  library: "M5 4h5v16H5zM12 4h5v16h-5zM10 8h2M10 16h2",
  docs: "M6 3h9l3 3v15H6zM9 9h6M9 13h6M9 17h4",
  tests: "M9 3v6l-5 9a2 2 0 0 0 2 3h12a2 2 0 0 0 2-3l-5-9V3M8 3h8",
  infra: "M12 3l8 4.5v9L12 21l-8-4.5v-9z",
};

export function BlockIcon({ type }: { type: BlockType }) {
  return (
    <svg className={`block-icon tone-${type}`} viewBox="0 0 24 24" aria-hidden="true">
      <path d={ICON[type]} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function BlockNode({ data, selected }: NodeProps<BlockFlowNode>) {
  const { block } = data;
  return (
    <div className={`arch-block tone-${block.type}${selected ? " selected" : ""}`}>
      <Handle type="target" position={Position.Left} />
      <div className="arch-head">
        <BlockIcon type={block.type} />
        <div>
          <div className="arch-kind">{BLOCK_LABEL[block.type]}</div>
          <div className="arch-name">{block.nom}</div>
        </div>
      </div>
      <div className="arch-role">{block.role}</div>
      {block.techno && <div className="arch-techno">{block.techno}</div>}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
