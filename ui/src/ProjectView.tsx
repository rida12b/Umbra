import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type MapNode, type MapView, type Project } from "./api";
import { ElementList } from "./map/ElementList";
import { MapCanvas, type Selection } from "./map/MapCanvas";
import { DetailsPanel } from "./panel/DetailsPanel";
import { useLive } from "./live";
import { roleOf, useModel } from "./model";
import { APPLICATION, navigate, type Route } from "./route";
import type { Theme } from "./theme";

type Loading = { view: MapView } | { error: ApiError } | null;

interface Props {
  project: Project;
  route: Route;
  theme: Theme;
  narrow: boolean;
}

export function ProjectView({ project, route, theme, narrow }: Props) {
  const [loading, setLoading] = useState<Loading>(null);
  const [selection, setSelection] = useState<Selection>(null);
  const [indexing, setIndexing] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [panelOpen, setPanelOpen] = useState(!narrow);
  const live = useLive();
  const model = useModel()?.model ?? null;

  useEffect(() => {
    let current = true; // on a live refresh the current map stays on screen until the new one arrives
    api
      .map(project.id, route.node, route.expand)
      .then((view) => current && setLoading({ view }))
      .catch((error: ApiError) => current && setLoading({ error }));
    return () => {
      current = false;
    };
  }, [project.id, route.node, route.expand, attempt, live.revision]);

  const open = useCallback(
    (node: MapNode) => {
      if (node.kind === "group") navigate({ ...route, expand: true });
      else if (node.children > 0) navigate({ projectId: project.id, node: node.key, expand: false });
    },
    [project.id, route],
  );

  const reindex = async () => {
    setIndexing(true);
    try {
      await api.index(project.id);
      setAttempt((n) => n + 1);
    } catch (error) {
      setLoading({ error: error as ApiError });
      setSelection(null);
    } finally {
      setIndexing(false);
    }
  };

  if (loading === null) return <div className="state">Loading the map…</div>;
  if ("error" in loading) {
    const { error } = loading;
    if (error.staleIndex)
      return (
        <div className="state">
          <p>{project.name} is not indexed yet, or was indexed by an older Umbra.</p>
          <button className="primary" onClick={reindex} disabled={indexing}>
            {indexing ? "Indexing…" : "Index now"}
          </button>
        </div>
      );
    if (error.status === 404)
      return (
        <div className="state">
          <p>This element is no longer in the map (the code may have changed).</p>
          <button onClick={() => navigate({ projectId: project.id, node: APPLICATION, expand: false })}>
            Back to the Application
          </button>
        </div>
      );
    return (
      <div className="state error-text">
        <p>{error.message}</p>
        <button onClick={() => setAttempt((n) => n + 1)}>Try again</button>
      </div>
    );
  }

  const { view } = loading;
  const labels = new Map(view.nodes.map((node) => [node.key, node.label]));
  // One sentence per block, from the Project model: no Claude call per element.
  const roles: Record<string, string> = {};
  for (const node of view.nodes) {
    const role = roleOf(model, node.key, node.path);
    if (role) roles[node.key] = role;
  }
  const showPanel = selection !== null || panelOpen;
  return (
    <div className={`project${showPanel ? " with-panel" : ""}`}>
      <div className="map-header">
        <nav className="breadcrumbs" aria-label="Zoom levels">
          {view.breadcrumbs.map((crumb, index) => {
            const last = index === view.breadcrumbs.length - 1;
            return (
              <span key={crumb.key}>
                {index > 0 && <span className="crumb-separator">/</span>}
                {last ? (
                  <span aria-current="page">{crumb.label}</span>
                ) : (
                  <a href={`#/p/${encodeURIComponent(project.id)}?node=${encodeURIComponent(crumb.key)}`}>
                    {crumb.label}
                  </a>
                )}
              </span>
            );
          })}
        </nav>
        <span className="muted count">
          {view.total_children} {view.total_children === 1 ? "element" : "elements"}
          {route.expand && view.total_children > 12 && (
            <button className="link-button" onClick={() => navigate({ ...route, expand: false })}>
              group small ones
            </button>
          )}
        </span>
        <Legend />
        {!showPanel && (
          <button className="explain-button" onClick={() => setPanelOpen(true)}>
            Expliquer ce niveau
          </button>
        )}
      </div>
      <div className="map-body">
        {view.nodes.length === 0 ? (
          <div className="state">Nothing inside this element was found in the code.</div>
        ) : narrow ? (
          <ElementList view={view} roles={roles} selection={selection} onSelect={setSelection} onOpen={open} />
        ) : (
          <MapCanvas
            view={view}
            roles={roles}
            theme={theme}
            vertical={false}
            selection={selection}
            onSelect={setSelection}
            onOpen={open}
          />
        )}
        {showPanel && (
          <DetailsPanel
            projectId={project.id}
            selection={selection}
            level={view.parent}
            labelOf={(key) => labels.get(key) ?? key}
            onOpen={open}
            onClose={() => {
              setSelection(null);
              setPanelOpen(false);
            }}
          />
        )}
      </div>
    </div>
  );
}

function Legend() {
  return (
    <div className="legend" aria-label="Legend">
      <span className="legend-item">
        <span className="legend-line link-fact" /> Fact
      </span>
      <span className="legend-item">
        <span className="legend-line link-hypothesis" /> Hypothesis
      </span>
      <span className="legend-item">
        <span className="legend-line link-declaration" /> Declared
      </span>
    </div>
  );
}
