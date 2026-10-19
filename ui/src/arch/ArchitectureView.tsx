import { Background, Controls, MarkerType, ReactFlow, type Edge } from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";
import { ARCHITECTURE, type ArchBlock, type ArchFlow, type Architecture, type Project } from "../api";
import { changedUnder, useLive } from "../live";
import { layoutBoxes } from "../map/layout";
import { useExplanation } from "../panel/useExplanation";
import { navigate } from "../route";
import type { Theme } from "../theme";
import { BLOCK_LABEL, BlockIcon, BlockNode, type BlockFlowNode } from "./BlockNode";

const BLOCK_SIZE = { width: 260, height: 132 };
const nodeTypes = { block: BlockNode };
type Picked = { block: ArchBlock } | { flow: ArchFlow } | null;

interface Props {
  project: Project;
  theme: Theme;
  narrow: boolean;
}

/** The Project's landing view: its architecture as drawn by Claude Code from the indexed structure. */
export function ArchitectureView({ project, theme, narrow }: Props) {
  const explanation = useExplanation<Architecture>(project.id, ARCHITECTURE);
  const architecture = explanation?.card ?? null;
  const [picked, setPicked] = useState<Picked>(null);

  if (!architecture) {
    const failed = explanation?.state === "error";
    return (
      <div className="state">
        {failed ? (
          <p className="error-text">Le schéma n'a pas pu être dessiné : {explanation?.message}</p>
        ) : (
          <p className="writing">Claude Code lit la structure du projet et dessine son architecture (environ 40 s)…</p>
        )}
      </div>
    );
  }
  const names = new Map(architecture.blocs.map((block) => [block.id, block.nom]));
  return (
    <div className="map-body">
      {narrow ? (
        <BlockList architecture={architecture} onPick={setPicked} />
      ) : (
        <ArchitectureCanvas architecture={architecture} theme={theme} picked={picked} onPick={setPicked} />
      )}
      <aside className="panel" aria-label="Architecture">
        {picked && "block" in picked ? (
          <BlockDetails block={picked.block} projectId={project.id} onBack={() => setPicked(null)} />
        ) : picked && "flow" in picked ? (
          <>
            <button className="link-button back" onClick={() => setPicked(null)}>← Vue d'ensemble</button>
            <p className="panel-kind">Flux</p>
            <h2 className="panel-title">
              {names.get(picked.flow.de)} → {names.get(picked.flow.vers)}
            </h2>
            <p>{picked.flow.quoi}</p>
          </>
        ) : (
          <>
            <p className="panel-kind">Architecture · {project.name}</p>
            <p className="card-role">{architecture.resume}</p>
            <h3 className="card-title">Le parcours principal</h3>
            <ol className="card-steps">
              {architecture.parcours.map((step, index) => (
                <li key={index}>{step}</li>
              ))}
            </ol>
            {architecture.incertitudes.length > 0 && (
              <>
                <h3 className="card-title">Ce qu'on ne peut pas savoir d'ici</h3>
                <ul className="card-list muted">
                  {architecture.incertitudes.map((item, index) => (
                    <li key={index}>{item}</li>
                  ))}
                </ul>
              </>
            )}
            <p className="card-footer">
              <span className="badge badge-hypothesis">Hypothèse</span> Dessiné par Claude Code
              {explanation?.created_at ? ` le ${explanation.created_at.slice(0, 10)}` : ""} à partir de la
              structure du code.
              {explanation?.state === "working" || explanation?.state === "queued" ? " Mise à jour en cours…" : ""}
            </p>
            <p className="muted hint">Cliquez un bloc pour voir son code, un flux pour ce qui y passe.</p>
          </>
        )}
      </aside>
    </div>
  );
}

function ArchitectureCanvas({ architecture, theme, picked, onPick }: {
  architecture: Architecture; theme: Theme; picked: Picked; onPick: (p: Picked) => void;
}) {
  const [nodes, setNodes] = useState<BlockFlowNode[] | null>(null);
  const live = useLive();
  useEffect(() => {
    let current = true;
    const links = architecture.flux.map((flow) => [flow.de, flow.vers] as [string, string]);
    layoutBoxes(architecture.blocs.map((block) => block.id), links, BLOCK_SIZE, false)
      .then((positions) => {
        if (!current) return;
        setNodes(
          architecture.blocs.map((block) => ({
            id: block.id,
            type: "block",
            position: positions.get(block.id) ?? { x: 0, y: 0 },
            data: { block },
          })),
        );
      })
      .catch(() => current && setNodes([]));
    return () => {
      current = false;
    };
  }, [architecture]);

  const pickedId = picked && "block" in picked ? picked.block.id : null;
  const edges: Edge[] = useMemo(
    () =>
      architecture.flux.map((flow, index) => ({
        id: `f${index}`,
        source: flow.de,
        target: flow.vers,
        label: flow.quoi.length > 42 ? `${flow.quoi.slice(0, 40)}…` : flow.quoi,
        className: `flow${pickedId && (flow.de === pickedId || flow.vers === pickedId) ? " flow-active" : ""}`,
        markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
      })),
    [architecture.flux, pickedId],
  );

  if (nodes === null) return <div className="state">Mise en place du schéma…</div>;
  return (
    <ReactFlow
      nodes={nodes.map((node) => ({
        ...node,
        selected: node.id === pickedId,
        data: { ...node.data, changed: node.data.block.code.some((code) => changedUnder(live, code.chemin)) },
      }))}
      edges={edges}
      nodeTypes={nodeTypes}
      colorMode={theme}
      onNodeClick={(_, node) => onPick({ block: node.data.block })}
      onEdgeClick={(_, edge) => {
        const flow = architecture.flux[Number(edge.id.slice(1))];
        if (flow) onPick({ flow });
      }}
      onPaneClick={() => onPick(null)}
      nodesDraggable={false}
      nodesConnectable={false}
      fitView
      fitViewOptions={{ padding: 0.12, maxZoom: 1.1 }}
      minZoom={0.1}
    >
      <Background gap={24} size={1} />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}

function BlockList({ architecture, onPick }: { architecture: Architecture; onPick: (p: Picked) => void }) {
  return (
    <ul className="element-list">
      {architecture.blocs.map((block) => (
        <li key={block.id}>
          <button className={`element-row arch-row tone-${block.type}`} onClick={() => onPick({ block })}>
            <span className="arch-head">
              <BlockIcon type={block.type} />
              <span>
                <span className="arch-kind">{BLOCK_LABEL[block.type]}</span>
                <span className="arch-name">{block.nom}</span>
              </span>
            </span>
            <span className="element-role">{block.role}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function BlockDetails({ block, projectId, onBack }: { block: ArchBlock; projectId: string; onBack: () => void }) {
  return (
    <>
      <button className="link-button back" onClick={onBack}>← Vue d'ensemble</button>
      <p className="panel-kind">{BLOCK_LABEL[block.type]}</p>
      <h2 className="panel-title">{block.nom}</h2>
      <p className="card-role">{block.role}</p>
      {block.techno && (
        <>
          <h3 className="card-title">Technologies</h3>
          <p>{block.techno}</p>
        </>
      )}
      <h3 className="card-title">Son code</h3>
      {block.code.length === 0 ? (
        <p className="muted">Pas de code dans ce projet : c'est un élément extérieur (personne, service, base).</p>
      ) : (
        <ul className="card-list">
          {block.code.map((code) => (
            <li key={code.chemin}>
              <button
                className="link-button code-link"
                onClick={() => navigate({ projectId, node: code.element, expand: false })}
              >
                {code.chemin} →
              </button>
            </li>
          ))}
        </ul>
      )}
      {block.indices && (
        <>
          <h3 className="card-title">Pourquoi on le pense</h3>
          <p className="muted">{block.indices}</p>
        </>
      )}
    </>
  );
}
