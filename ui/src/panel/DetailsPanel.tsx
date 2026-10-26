import { X } from "lucide-react";
import type { MapEdge, MapNode, MapStatus } from "../api";
import { KIND_LABEL, STATUS_LABEL, childrenLabel } from "../map/ElementNode";
import type { Selection } from "../map/MapCanvas";
import { Button } from "../ui";
import { ElementUnderstanding } from "./ElementUnderstanding";
import { EvidenceItem } from "./EvidenceItem";

const STATUS_MEANING: Record<MapStatus, string> = {
  fact: "Lu directement dans le code : chaque partie s'appuie sur les lignes citées.",
  hypothesis: "Déduit, pas prouvé : Umbra a rapproché des noms ou des chemins sans pouvoir confirmer la cible.",
  declaration: "Ce que la configuration déclare. Ce n'est pas la preuve que cela tourne, ni de cette façon.",
};
const MODULE_PREVIEW_LINES = 30;

interface Props {
  projectId: string;
  selection: Selection;
  /** The element whose inside is shown: what the panel explains when nothing is selected. */
  level: MapNode;
  labelOf: (key: string) => string;
  onOpen: (node: MapNode) => void;
  onClose: () => void;
  cited?: { file: string; start: number; end: number } | null; // opened from a file:line link: those lines, shown first
}

export function DetailsPanel({ projectId, selection, level, labelOf, onOpen, onClose, cited = null }: Props) {
  return (
    <div className="relative px-6 pt-5 pb-10">
      {cited && (
        <section className="mb-5" aria-label="Les lignes citées">
          <p className="text-[12px] text-faint">Les lignes que vous avez ouvertes</p>
          <EvidenceItem projectId={projectId} source={cited} />
        </section>
      )}
      {selection !== null && (
        <button type="button" className="absolute top-4 right-4 rounded p-1 text-faint hover:bg-raised hover:text-ink" onClick={onClose} aria-label="Fermer le détail">
          <X size={16} />
        </button>
      )}
      {selection === null ? (
        <>
          <p className="text-[12px] text-faint">Vous êtes ici : {KIND_LABEL[level.kind].toLowerCase()}</p>
          <h1 className="text-[19px] font-semibold tracking-[-0.01em]">{level.label}</h1>
          <ElementUnderstanding key={level.key} projectId={projectId} node={level} />
          <p className="mt-6 text-[12.5px] text-faint">Cliquez un bloc pour son rôle, double-cliquez pour entrer dedans.</p>
        </>
      ) : selection.type === "node" ? (
        <NodeDetails key={selection.node.key} projectId={projectId} node={selection.node} onOpen={onOpen} />
      ) : (
        <EdgeDetails projectId={projectId} edge={selection.edge} labelOf={labelOf} />
      )}
    </div>
  );
}

function NodeDetails({ projectId, node, onOpen }: { projectId: string; node: MapNode; onOpen: (n: MapNode) => void }) {
  const details = Object.entries(node.details).filter(([, values]) => values.length > 0);
  const location = node.path && node.lines ? `${node.path}:${node.lines[0]}–${node.lines[1]}` : node.path;
  return (
    <>
      <p className="text-[12px] text-faint">{KIND_LABEL[node.kind]}</p>
      <h1 className="pr-8 text-[19px] font-semibold tracking-[-0.01em] break-words">{node.label}</h1>
      {location && <p className="mt-1 font-mono text-[12px] break-all text-faint">{location}</p>}
      {node.children > 0 && (
        <Button variant="primary" className="mt-3" onClick={() => onOpen(node)}>
          Entrer : {childrenLabel(node)}
        </Button>
      )}
      <ElementUnderstanding projectId={projectId} node={node} />
      <details className="mt-6 border-t border-line-soft pt-3 text-[13px]">
        <summary className="cursor-pointer text-muted hover:text-ink">Détails techniques et preuves</summary>
        <p className="mt-2 text-muted">
          <span className="mr-1.5 rounded border border-line px-1.5 py-px">{STATUS_LABEL[node.status]}</span>
          {STATUS_MEANING[node.status]}
        </p>
        {details.length > 0 && (
          <dl className="mt-2 space-y-1">
            {details.map(([name, values]) => (
              <div key={name} className="grid grid-cols-[110px_1fr] gap-2">
                <dt className="text-faint">{name}</dt>
                <dd className="break-words">{values.map((value) => (value === "" ? "(racine du projet)" : value)).join(", ")}</dd>
              </div>
            ))}
          </dl>
        )}
        {node.evidence.map((key) => (
          <EvidenceItem key={key} projectId={projectId} source={{ claim: key }} />
        ))}
        {node.evidence.length === 0 && node.kind === "module" && node.path && (
          <EvidenceItem projectId={projectId} source={{ file: node.path, start: 1, end: MODULE_PREVIEW_LINES }} />
        )}
      </details>
    </>
  );
}

function EdgeDetails({ projectId, edge, labelOf }: { projectId: string; edge: MapEdge; labelOf: (k: string) => string }) {
  return (
    <>
      <p className="text-[12px] text-faint">Lien</p>
      <h1 className="pr-8 text-[19px] font-semibold tracking-[-0.01em] break-words">
        {labelOf(edge.source)} → {labelOf(edge.target)}
      </h1>
      <p className="mt-2 text-[13px] text-muted">
        <span className="mr-1.5 rounded border border-line px-1.5 py-px">{STATUS_LABEL[edge.status]}</span>
        {STATUS_MEANING[edge.status]}
      </p>
      <p className="mt-2 text-[13px]">
        <code className="font-mono">{edge.relation}</code>, {edge.count} preuve{edge.count > 1 ? "s" : ""}
        {edge.count > edge.evidence.length ? ` (${edge.evidence.length} montrées)` : ""}
      </p>
      {edge.evidence.map((key) => (
        <EvidenceItem key={key} projectId={projectId} source={{ claim: key }} />
      ))}
    </>
  );
}
