import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api, type MapNode, type MapView } from "../api";
import { useLive } from "../live";
import { MapCanvas, type Selection } from "../map/MapCanvas";
import { roleOf, useModel } from "../model";
import { DetailsPanel } from "../panel/DetailsPanel";
import type { Theme } from "../theme";
import { PanelResizer, usePanelWidth } from "../shell/PanelWidth";
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
  onDrill: (node: string) => void; // a cited line sits inside an element: go into it, keeping the same « line:N » selection
}

/** The deepest levels: the code itself (folders, files, functions, calls), read from the index. */
export function CodeLevel({ projectId, node, expand, select, theme, narrow, onView, onOpen, onDrill }: Props) {
  const [view, setView] = useState<MapView | ApiError | null>(null);
  const [selection, setSelection] = useState<Selection>(null);
  const selectApplied = useRef(false);
  const grid = useRef<HTMLDivElement>(null);
  const panelWidth = usePanelWidth();
  // The parent passes a new function on each render: kept in a ref so the map is not fetched again for it.
  const drill = useRef(onDrill);
  drill.current = onDrill;
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
        const cited = select ? citedLines(select) : null;
        const picked = select && !selectApplied.current ? (pickLine(found.nodes, cited) ?? found.nodes.find((n) => n.key === select)) : undefined;
        // The line is inside a class or a module's part: go down to the smallest element that holds it (#79 review).
        if (picked && cited && picked.children > 0) {
          selectApplied.current = true;
          drill.current(picked.key);
          return;
        }
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
    <div
      ref={grid}
      className={narrow ? "grid h-full min-h-0 grid-rows-[minmax(0,3fr)_minmax(0,2fr)]" : "relative grid h-full min-h-0"}
      style={narrow ? undefined : { gridTemplateColumns: `minmax(0,1fr) ${panelWidth}px` }}
    >
      {!narrow && <PanelResizer grid={grid} />}
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
          cited={citedLines(select) && view.parent.path ? { file: view.parent.path, ...citedLines(select)! } : null}
        />
      </aside>
    </div>
  );
}

/** « line:33 » or « line:35-38 » (a plate's or the player's file:line link): the lines a reader came to see. */
export function citedLines(select: string | null): { start: number; end: number } | null {
  const m = select ? /^line:(\d+)(?:-(\d+))?$/.exec(select) : null;
  return m ? { start: Number(m[1]), end: Number(m[2] ?? m[1]) } : null;
}

/** The smallest element of this level that holds the first cited line. */
function pickLine(nodes: MapNode[], cited: { start: number } | null): MapNode | undefined {
  if (!cited) return undefined;
  const size = (x: MapNode) => (x.lines ? x.lines[1] - x.lines[0] : Infinity);
  return nodes.filter((x) => x.lines && x.lines[0] <= cited.start && cited.start <= x.lines[1]).sort((a, b) => size(a) - size(b))[0];
}
