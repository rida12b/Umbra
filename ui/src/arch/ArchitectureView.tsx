import { Background, Controls, MarkerType, ReactFlow, type Edge } from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";
import type { ArchBlock, ArchFlow, Project, ProjectModel } from "../api";
import { changedUnder, useLive } from "../live";
import { layoutBoxes } from "../map/layout";
import { useModel } from "../model";
import { JOURNEYS_VIEW, navigate } from "../route";
import type { Theme } from "../theme";
import { BLOCK_LABEL, BlockIcon, BlockNode, type BlockFlowNode } from "./BlockNode";
import { CitedCode } from "./CitedCode";
import { ModelPending, ModelStatusLine } from "./ModelStatus";

const BLOCK_SIZE = { width: 260, height: 132 };
const nodeTypes = { block: BlockNode };
type Picked = { block: ArchBlock } | { flow: ArchFlow } | null;

interface Props {
  project: Project;
  theme: Theme;
  narrow: boolean;
  /** Blocks and flows of one journey to light up (from the journeys view). */
  highlight?: { blocks: Set<string>; flows: Set<string> } | null;
}

/** The Project's landing view: its architecture, from the model Claude Code wrote after studying it. */
export function ArchitectureView({ project, theme, narrow, highlight = null }: Props) {
  const state = useModel();
  const [picked, setPicked] = useState<Picked>(null);
  const model = state?.model ?? null;
  if (!model) return <ModelPending state={state} />;

  const names = new Map(model.blocs.map((block) => [block.id, block.nom]));
  return (
    <div className="map-body">
      {narrow ? (
        <BlockList model={model} onPick={setPicked} />
      ) : (
        <ArchitectureCanvas model={model} theme={theme} picked={picked} onPick={setPicked} highlight={highlight} />
      )}
      <aside className="panel" aria-label="Architecture">
        {picked && "block" in picked ? (
          <BlockDetails block={picked.block} model={model} project={project} onBack={() => setPicked(null)} />
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
          <Overview model={model} project={project} />
        )}
      </aside>
    </div>
  );
}

function Overview({ model, project }: { model: ProjectModel; project: Project }) {
  return (
    <>
      <p className="panel-kind">Architecture · {project.name}</p>
      <p className="card-role">{model.resume}</p>
      <h3 className="card-title">Ce que fait le système, de bout en bout</h3>
      <ul className="journey-links">
        {model.parcours.map((journey) => (
          <li key={journey.id}>
            <button
              className="link-button"
              onClick={() => navigate({ projectId: project.id, node: JOURNEYS_VIEW, expand: false, journey: journey.id })}
            >
              {journey.nom} →
            </button>
            <span className="muted"> {journey.etapes.length} étapes</span>
          </li>
        ))}
      </ul>
      {model.incertitudes.length > 0 && (
        <>
          <h3 className="card-title">Ce qu'on ne peut pas savoir d'ici</h3>
          <ul className="card-list muted">
            {model.incertitudes.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </>
      )}
      <ModelStatusLine />
      <p className="muted hint">Cliquez un bloc pour ses composants et son code, un flux pour ce qui y passe.</p>
    </>
  );
}

function ArchitectureCanvas({ model, theme, picked, onPick, highlight }: {
  model: ProjectModel; theme: Theme; picked: Picked; onPick: (p: Picked) => void;
  highlight: Props["highlight"];
}) {
  const [nodes, setNodes] = useState<BlockFlowNode[] | null>(null);
  const live = useLive();
  useEffect(() => {
    let current = true;
    const links = model.flux.map((flow) => [flow.de, flow.vers] as [string, string]);
    layoutBoxes(model.blocs.map((block) => block.id), links, BLOCK_SIZE, false)
      .then((positions) => {
        if (!current) return;
        setNodes(
          model.blocs.map((block) => ({
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
  }, [model]);

  const pickedId = picked && "block" in picked ? picked.block.id : null;
  const edges: Edge[] = useMemo(
    () =>
      model.flux.map((flow, index) => {
        const active =
          (pickedId !== null && (flow.de === pickedId || flow.vers === pickedId)) ||
          (highlight?.flows.has(`${flow.de}>${flow.vers}`) ?? false);
        return {
          id: `f${index}`,
          source: flow.de,
          target: flow.vers,
          label: flow.quoi.length > 42 ? `${flow.quoi.slice(0, 40)}…` : flow.quoi,
          className: `flow${active ? " flow-active" : ""}`,
          markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
        };
      }),
    [model.flux, pickedId, highlight],
  );

  if (nodes === null) return <div className="state">Mise en place du schéma…</div>;
  return (
    <ReactFlow
      nodes={nodes.map((node) => ({
        ...node,
        selected: node.id === pickedId,
        className: highlight && !highlight.blocks.has(node.id) ? "dimmed" : undefined,
        data: { ...node.data, changed: node.data.block.code.some((code) => changedUnder(live, code.chemin)) },
      }))}
      edges={edges}
      nodeTypes={nodeTypes}
      colorMode={theme}
      onNodeClick={(_, node) => onPick({ block: node.data.block })}
      onEdgeClick={(_, edge) => {
        const flow = model.flux[Number(edge.id.slice(1))];
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

function BlockList({ model, onPick }: { model: ProjectModel; onPick: (p: Picked) => void }) {
  return (
    <ul className="element-list">
      {model.blocs.map((block) => (
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

function BlockDetails({ block, model, project, onBack }: {
  block: ArchBlock; model: ProjectModel; project: Project; onBack: () => void;
}) {
  const components = model.composants.filter((component) => component.bloc === block.id);
  return (
    <>
      <button className="link-button back" onClick={onBack}>← Vue d'ensemble</button>
      <p className="panel-kind">{BLOCK_LABEL[block.type]}</p>
      <h2 className="panel-title">{block.nom}</h2>
      <p className="card-role">{block.role}</p>
      {block.techno && <p className="muted">{block.techno}</p>}
      {components.length > 0 && <h3 className="card-title">Ses composants</h3>}
      {components.map((component) => (
        <section key={component.id} className="component">
          <p className="component-name">{component.nom}</p>
          <p>{component.role}</p>
          {component.expose.length > 0 && (
            <ul className="card-list">
              {component.expose.map((item, index) => (
                <li key={index}>
                  {item.quoi} <CitedCode projectId={project.id} cited={item} />
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}
      <h3 className="card-title">Son code</h3>
      {block.code.length === 0 ? (
        <p className="muted">Pas de code dans ce projet : c'est un élément extérieur (personne, service, base).</p>
      ) : (
        <ul className="card-list">
          {block.code.map((code) => (
            <li key={code.chemin}>
              <button
                className="link-button code-link"
                onClick={() => navigate({ projectId: project.id, node: code.element, expand: false })}
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
