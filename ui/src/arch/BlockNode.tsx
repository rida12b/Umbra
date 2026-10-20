import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import type { ArchBlock, BlockType } from "../api";
import type { StepMark } from "./journeyPath";

export type BlockLook = "plain" | "lit" | "dim";
export type BlockData = {
  block: ArchBlock;
  look: BlockLook;
  inside: StepMark[]; // journey steps that happen inside this block
  activeStep: number | null;
  changed: boolean;
  onStep: (number: number) => void;
};
export type BlockFlowNode = Node<BlockData, "block">;

export const BLOCK_WIDTH = 232;
const BASE_HEIGHT = 112; // kind, a name on two lines at most, a role on two lines at most
const STEP_ROW = 30;

export function blockHeight(inside: number): number {
  return BASE_HEIGHT + (inside > 0 ? 10 + inside * STEP_ROW : 0);
}

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

const LOOK = {
  plain: "border-line bg-panel",
  lit: "border-lamp-ink/55 bg-panel",
  dim: "border-line-soft bg-panel opacity-35",
};

export function BlockNode({ data, selected }: NodeProps<BlockFlowNode>) {
  const { block, look, inside, activeStep, changed, onStep } = data;
  const height = blockHeight(inside.length);
  return (
    <div
      className={`flex flex-col rounded-lg border px-3 py-2.5 transition-opacity ${LOOK[look]} ${
        selected ? "ring-2 ring-ink/70" : ""
      }`}
      style={{ width: BLOCK_WIDTH, height }}
      title={block.role}
    >
      <Handle type="target" position={Position.Top} />
      <span className="flex items-center gap-1.5 text-[11.5px] text-faint">
        {changed && <span className="size-1.5 rounded-full bg-ok" title="Code modifié à l'instant" />}
        {BLOCK_LABEL[block.type]}
      </span>
      <span className="line-clamp-2 text-[13.5px] leading-snug font-semibold text-ink">{block.nom}</span>
      <span className="mt-0.5 line-clamp-2 text-[12px] leading-snug text-muted">{block.role}</span>
      {inside.length > 0 && (
        <span className="mt-auto flex flex-col gap-1 border-t border-line-soft pt-2">
          {inside.map((mark) => (
            <button
              key={mark.number}
              type="button"
              className="nodrag flex items-center gap-2 text-left text-[12px] text-ink"
              onClick={(event) => {
                event.stopPropagation();
                onStep(mark.number);
              }}
            >
              <span className="step-number" data-on={mark.number === activeStep}>
                {mark.number}
              </span>
              <span className="truncate">{mark.label}</span>
            </button>
          ))}
        </span>
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
