import { ActivityView } from "./ActivityView";
import type { Project } from "./api";
import { Explorer } from "./explorer/Explorer";
import { ModelContext, useProjectModel } from "./model";
import { ACTIVITY_VIEW, type Route } from "./route";
import { CommandPalette } from "./shell/CommandPalette";
import type { Theme } from "./theme";

interface Props {
  project: Project;
  route: Route;
  theme: Theme;
  narrow: boolean;
  searching: boolean;
  onSearching: (open: boolean) => void;
}

/** One Project: the explorer (its map, from the context down to the code) and Claude's activity. */
export function ProjectPage({ project, route, theme, narrow, searching, onSearching }: Props) {
  const state = useProjectModel(project.id);
  return (
    <ModelContext.Provider value={state}>
      <main className="min-h-0 flex-1">
        {route.node === ACTIVITY_VIEW ? (
          <ActivityView project={project} />
        ) : (
          <Explorer project={project} route={route} theme={theme} narrow={narrow} />
        )}
      </main>
      <CommandPalette projectId={project.id} model={state?.model ?? null} open={searching} onOpenChange={onSearching} />
    </ModelContext.Provider>
  );
}
