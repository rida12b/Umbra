import type { Explanation, MapEdge, MapNode, MapStatus } from "../api";
import { KIND_LABEL, STATUS_LABEL, childrenLabel } from "../map/ElementNode";
import type { Selection } from "../map/MapCanvas";
import { EvidenceItem } from "./EvidenceItem";
import { ExplanationCard } from "./ExplanationCard";
import { useExplanation } from "./useExplanation";

const STATUS_MEANING: Record<MapStatus, string> = {
  fact: "Read directly from the code: each part is backed by the cited lines.",
  hypothesis: "Inferred, not proven: Umbra matched names or paths but could not confirm the target.",
  declaration: "What configuration declares. It is not proof that this runs, or runs this way.",
};
const MODULE_PREVIEW_LINES = 30;

interface Props {
  projectId: string;
  selection: Selection;
  /** The element whose inside is shown, and its card: what the panel shows when nothing is selected. */
  level: MapNode;
  levelExplanation: Explanation | null;
  labelOf: (key: string) => string;
  onOpen: (node: MapNode) => void;
  onClose: () => void;
}

export function DetailsPanel(props: Props) {
  const { projectId, selection, level, levelExplanation, labelOf, onOpen, onClose } = props;
  return (
    <aside className="panel" aria-label="Explanation and evidence">
      <button className="panel-close" onClick={onClose} aria-label="Close panel">
        ×
      </button>
      {selection === null ? (
        <>
          <p className="panel-kind">Vous êtes ici · {KIND_LABEL[level.kind]}</p>
          <h2 className="panel-title">{level.label}</h2>
          <ExplanationCard projectId={projectId} explanation={levelExplanation} defaultFile={level.path} />
          <p className="muted hint">Cliquez un bloc pour son explication, double-cliquez pour entrer dedans.</p>
        </>
      ) : selection.type === "node" ? (
        <NodeDetails key={selection.node.key} projectId={projectId} node={selection.node} onOpen={onOpen} />
      ) : (
        <EdgeDetails projectId={projectId} edge={selection.edge} labelOf={labelOf} />
      )}
    </aside>
  );
}

function NodeDetails({ projectId, node, onOpen }: { projectId: string; node: MapNode; onOpen: (n: MapNode) => void }) {
  const explanation = useExplanation(projectId, node.key);
  const details = Object.entries(node.details).filter(([, values]) => values.length > 0);
  const location = node.path && node.lines ? `${node.path}:${node.lines[0]}–${node.lines[1]}` : node.path;
  return (
    <>
      <p className="panel-kind">{KIND_LABEL[node.kind]}</p>
      <h2 className="panel-title">{node.label}</h2>
      {node.children > 0 && (
        <button className="primary" onClick={() => onOpen(node)}>
          Entrer — {childrenLabel(node)}
        </button>
      )}
      <ExplanationCard projectId={projectId} explanation={explanation} defaultFile={node.path} />
      <details className="technical">
        <summary>Détails techniques et preuves</summary>
        <p className="status-line">
          <span className={`badge badge-${node.status}`}>{STATUS_LABEL[node.status]}</span>{" "}
          {STATUS_MEANING[node.status]}
        </p>
        {location && <p className="panel-path">{location}</p>}
        {details.length > 0 && (
          <dl className="details">
            {details.map(([name, values]) => (
              <div key={name}>
                <dt>{name}</dt>
                <dd>{values.map((value) => (value === "" ? "(Project root)" : value)).join(", ")}</dd>
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
      <p className="panel-kind">Lien</p>
      <h2 className="panel-title">
        {labelOf(edge.source)} → {labelOf(edge.target)}
      </h2>
      <p className="status-line">
        <span className={`badge badge-${edge.status}`}>{STATUS_LABEL[edge.status]}</span>{" "}
        {STATUS_MEANING[edge.status]}
      </p>
      <p>
        <code>{edge.relation}</code>, {edge.count} {edge.count > 1 ? "Claims" : "Claim"}
        {edge.count > edge.evidence.length ? ` (showing ${edge.evidence.length})` : ""}
      </p>
      {edge.evidence.map((key) => (
        <EvidenceItem key={key} projectId={projectId} source={{ claim: key }} />
      ))}
    </>
  );
}
