import type { MapEdge, MapNode, MapStatus } from "../api";
import { KIND_LABEL, STATUS_LABEL, childrenLabel } from "../map/ElementNode";
import type { Selection } from "../map/MapCanvas";
import { EvidenceItem } from "./EvidenceItem";

const STATUS_MEANING: Record<MapStatus, string> = {
  fact: "Read directly from the code: each part is backed by the cited lines.",
  hypothesis: "Inferred, not proven: Umbra matched names or paths but could not confirm the target.",
  declaration: "What configuration declares. It is not proof that this runs, or runs this way.",
};
const MODULE_PREVIEW_LINES = 30;

interface Props {
  projectId: string;
  selection: NonNullable<Selection>;
  labelOf: (key: string) => string;
  onOpen: (node: MapNode) => void;
  onClose: () => void;
}

export function DetailsPanel({ projectId, selection, labelOf, onOpen, onClose }: Props) {
  return (
    <aside className="panel" aria-label="Details and evidence">
      <button className="panel-close" onClick={onClose} aria-label="Close details">
        ×
      </button>
      {selection.type === "node" ? (
        <NodeDetails projectId={projectId} node={selection.node} onOpen={onOpen} />
      ) : (
        <EdgeDetails projectId={projectId} edge={selection.edge} labelOf={labelOf} />
      )}
    </aside>
  );
}

function StatusLine({ status }: { status: MapStatus }) {
  return (
    <p className="status-line">
      <span className={`badge badge-${status}`}>{STATUS_LABEL[status]}</span> {STATUS_MEANING[status]}
    </p>
  );
}

function NodeDetails({ projectId, node, onOpen }: { projectId: string; node: MapNode; onOpen: (n: MapNode) => void }) {
  const details = Object.entries(node.details).filter(([, values]) => values.length > 0);
  const location = node.path && node.lines ? `${node.path}:${node.lines[0]}–${node.lines[1]}` : node.path;
  return (
    <>
      <p className="panel-kind">{KIND_LABEL[node.kind]}</p>
      <h2 className="panel-title">{node.label}</h2>
      <StatusLine status={node.status} />
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
      {node.children > 0 && (
        <button className="primary" onClick={() => onOpen(node)}>
          Open — {childrenLabel(node)}
        </button>
      )}
      <h3 className="panel-section">Evidence</h3>
      {node.evidence.map((key) => (
        <EvidenceItem key={key} projectId={projectId} source={{ claim: key }} />
      ))}
      {node.evidence.length === 0 && node.kind === "module" && node.path && (
        <EvidenceItem
          projectId={projectId}
          source={{ file: node.path, start: 1, end: MODULE_PREVIEW_LINES }}
        />
      )}
      {node.evidence.length === 0 && node.kind !== "module" && (
        <p className="muted">
          This element groups what is inside it; open it to see the Evidence of each part.
        </p>
      )}
    </>
  );
}

function EdgeDetails({ projectId, edge, labelOf }: { projectId: string; edge: MapEdge; labelOf: (k: string) => string }) {
  return (
    <>
      <p className="panel-kind">Link</p>
      <h2 className="panel-title">
        {labelOf(edge.source)} → {labelOf(edge.target)}
      </h2>
      <StatusLine status={edge.status} />
      <p>
        <code>{edge.relation}</code>, {edge.count} {edge.count > 1 ? "Claims" : "Claim"}
        {edge.count > edge.evidence.length ? ` (showing ${edge.evidence.length})` : ""}
      </p>
      <h3 className="panel-section">Evidence</h3>
      {edge.evidence.map((key) => (
        <EvidenceItem key={key} projectId={projectId} source={{ claim: key }} />
      ))}
    </>
  );
}
