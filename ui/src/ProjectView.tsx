import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api, type MapNode, type MapView, type Project } from "./api";
import { useLive } from "./live";
import { ElementList } from "./map/ElementList";
import { MapCanvas, type Selection } from "./map/MapCanvas";
import { roleOf, useModel } from "./model";
import { DetailsPanel } from "./panel/DetailsPanel";
import { APPLICATION, navigate, type Route } from "./route";
import type { Theme } from "./theme";
import { Button, StateMessage } from "./ui";

type Loading = { view: MapView } | { error: ApiError } | null;

interface Props {
  project: Project;
  route: Route;
  theme: Theme;
  narrow: boolean;
}

/** The code, level by level: the application, its services, folders, files, then functions. */
export function ProjectView({ project, route, theme, narrow }: Props) {
  const [loading, setLoading] = useState<Loading>(null);
  const [selection, setSelection] = useState<Selection>(null);
  const [indexing, setIndexing] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const selectApplied = useRef(false);
  const live = useLive();
  const model = useModel()?.model ?? null;

  useEffect(() => {
    let current = true; // on a live refresh the current map stays on screen until the new one arrives
    api
      .map(project.id, route.node, route.expand)
      .then((view) => {
        if (!current) return;
        setLoading({ view });
        // A searched element is selected once; a live refresh must not select it again.
        const picked = route.select && !selectApplied.current ? view.nodes.find((n) => n.key === route.select) : undefined;
        if (picked) {
          selectApplied.current = true;
          setSelection({ type: "node", node: picked });
        }
      })
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

  if (loading === null) return <StateMessage>Lecture de la carte du code…</StateMessage>;
  if ("error" in loading) {
    const { error } = loading;
    if (error.staleIndex)
      return (
        <StateMessage title={`${project.name} n'est pas encore indexé`}>
          <p className="mb-3">Ou il l'a été par une version plus ancienne d'Umbra.</p>
          <Button variant="primary" onClick={reindex} disabled={indexing}>
            {indexing ? "Indexation…" : "Indexer maintenant"}
          </Button>
        </StateMessage>
      );
    if (error.status === 404)
      return (
        <StateMessage title="Cet élément n'est plus dans la carte">
          <p className="mb-3">Le code a peut-être changé.</p>
          <Button onClick={() => navigate({ projectId: project.id, node: APPLICATION, expand: false })}>
            Revenir à l'application
          </Button>
        </StateMessage>
      );
    return (
      <StateMessage title="La carte n'a pas pu être lue">
        <p className="mb-3 text-danger">{error.message}</p>
        <Button onClick={() => setAttempt((n) => n + 1)}>Réessayer</Button>
      </StateMessage>
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
  const panel = (
    <DetailsPanel
      projectId={project.id}
      selection={selection}
      level={view.parent}
      labelOf={(key) => labels.get(key) ?? key}
      onOpen={open}
      onClose={() => setSelection(null)}
    />
  );
  const body =
    view.nodes.length === 0 ? (
      <StateMessage>Rien n'a été trouvé à l'intérieur de cet élément.</StateMessage>
    ) : narrow ? (
      <ElementList view={view} roles={roles} selection={selection} onSelect={setSelection} onOpen={open} />
    ) : (
      <MapCanvas view={view} roles={roles} theme={theme} vertical={false} selection={selection} onSelect={setSelection} onOpen={open} />
    );

  return (
    <div className={`grid h-full min-h-0 ${narrow ? "grid-cols-1 overflow-y-auto" : "grid-cols-[1fr_minmax(340px,420px)]"}`}>
      <section className="flex min-h-0 flex-col" aria-label="Carte du code">
        <header className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-line-soft px-4 py-2 text-[13px]">
          <nav className="flex min-w-0 flex-wrap items-center gap-1.5" aria-label="Niveaux">
            {view.breadcrumbs.map((crumb, index) => {
              const last = index === view.breadcrumbs.length - 1;
              return (
                <span key={crumb.key} className="flex items-center gap-1.5">
                  {index > 0 && <span className="text-faint">/</span>}
                  {last ? (
                    <span aria-current="page" className="font-medium">
                      {crumb.label}
                    </span>
                  ) : (
                    <a className="text-muted hover:text-ink" href={`#/p/${encodeURIComponent(project.id)}?node=${encodeURIComponent(crumb.key)}`}>
                      {crumb.label}
                    </a>
                  )}
                </span>
              );
            })}
          </nav>
          <span className="text-faint">
            {view.total_children} élément{view.total_children > 1 ? "s" : ""}
          </span>
          {route.expand && view.total_children > 12 && (
            <Button variant="link" className="text-[13px] text-muted" onClick={() => navigate({ ...route, expand: false })}>
              Regrouper les petits
            </Button>
          )}
          <Legend />
        </header>
        <div className={`map-surface relative ${narrow ? "" : "min-h-0 flex-1"}`}>{body}</div>
      </section>
      <aside className={`overflow-y-auto ${narrow ? "border-t" : "min-h-0 border-l"} border-line-soft`} aria-label="Explication et preuves">
        {panel}
      </aside>
    </div>
  );
}

function Legend() {
  const line = (style: string) => <svg width="18" height="6" aria-hidden="true"><path d="M0 3h18" stroke="currentColor" strokeWidth="1.6" strokeDasharray={style} /></svg>;
  return (
    <span className="ml-auto hidden items-center gap-3 text-[12px] text-faint md:flex" aria-label="Légende des liens">
      <span className="flex items-center gap-1.5 text-muted">{line("")} Fait</span>
      <span className="flex items-center gap-1.5">{line("5 4")} Hypothèse</span>
      <span className="flex items-center gap-1.5">{line("1 4")} Déclaré</span>
    </span>
  );
}
