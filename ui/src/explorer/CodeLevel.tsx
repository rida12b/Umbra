import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api, type MapNode, type MapView } from "../api";
import { useLive } from "../live";
import { MapCanvas, type Selection } from "../map/MapCanvas";
import { roleOf, useModel } from "../model";
import { DetailsPanel } from "../panel/DetailsPanel";
import type { Theme } from "../theme";
import { StateMessage } from "../ui";

interface Props {
  projectId: string;
  node: string; // a code map key: a service, folder, file or function
  expand: boolean;
  select: string | null;
  theme: Theme;
  narrow: boolean; // a phone: the map above its explanation
  onView: (view: MapView | null) => void; // its breadcrumbs, for the explorer's trail
  onOpen: (node: string, expand: boolean) => void; // a group of small elements opens expanded, in place
}

/** The deepest levels: the code itself (folders, files, functions, calls), read from the index. */
export function CodeLevel({ projectId, node, expand, select, theme, narrow, onView, onOpen }: Props) {
  const [view, setView] = useState<MapView | ApiError | null>(null);
  const [selection, setSelection] = useState<Selection>(null);
  const selectApplied = useRef(false);
  const live = useLive();
  const model = useModel()?.model ?? null;

  useEffect(() => {
    let current = true; // on a live refresh the current map stays on screen until the new one arrives
    api
      .map(projectId, node, expand)
      .then((found) => {
        if (!current) return;
        setView(found);
        onView(found);
        const picked = select && !selectApplied.current ? found.nodes.find((n) => n.key === select) : undefined;
        if (picked) {
          selectApplied.current = true;
          setSelection({ type: "node", node: picked });
        }
      })
      .catch((error: ApiError) => {
        if (!current) return;
        setView(error);
        onView(null); // no trail of the element shown before
      });
    return () => {
      current = false;
    };
  }, [projectId, node, expand, select, live.revision, onView]);

  const open = useCallback(
    (element: MapNode) => {
      if (element.kind === "group") onOpen(node, true);
      else if (element.children > 0) onOpen(element.key, false);
    },
    [node, onOpen],
  );

  if (view === null) return <StateMessage>Lecture du code…</StateMessage>;
  if (view instanceof ApiError)
    return (
      <StateMessage title={view.status === 404 ? "Cet élément n'est plus dans le code" : "Le code n'a pas pu être lu"}>
        <p>{view.status === 404 ? "Le projet a changé depuis ce lien." : view.message}</p>
      </StateMessage>
    );
  const roles: Record<string, string> = {};
  // The model describes files and folders; a function would wrongly get its whole file's role.
  const described = new Set(["application", "service", "component", "module", "group"]);
  for (const element of view.nodes) {
    if (!described.has(element.kind)) continue;
    const role = roleOf(model, element.key, element.path);
    if (role) roles[element.key] = role;
  }
  const labels = new Map(view.nodes.map((element) => [element.key, element.label]));
  return (
    <div className={narrow ? "grid h-full min-h-0 grid-rows-[minmax(0,3fr)_minmax(0,2fr)]" : "grid h-full min-h-0 grid-cols-[minmax(0,1fr)_400px]"}>
      <div className="map-surface relative min-h-0">
        {view.nodes.length === 0 ? (
          <StateMessage>Rien n'a été trouvé à l'intérieur.</StateMessage>
        ) : (
          <MapCanvas view={view} roles={roles} theme={theme} vertical={false} selection={selection} onSelect={setSelection} onOpen={open} />
        )}
      </div>
      <aside className={`min-h-0 overflow-y-auto border-line-soft ${narrow ? "border-t" : "border-l"}`} aria-label="Explication et preuves">
        <DetailsPanel
          projectId={projectId}
          selection={selection}
          level={view.parent}
          labelOf={(key) => labels.get(key) ?? key}
          onOpen={open}
          onClose={() => setSelection(null)}
        />
      </aside>
    </div>
  );
}
