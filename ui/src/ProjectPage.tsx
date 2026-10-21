import { ActivityView } from "./ActivityView";
import type { Project } from "./api";
import { ArchitectureView } from "./arch/ArchitectureView";
import { ModelContext, useProjectModel } from "./model";
import { ProjectView } from "./ProjectView";
import { ACTIVITY_VIEW, APPLICATION, ARCHITECTURE_VIEW, MAP_VIEW, type Route } from "./route";
import { CommandPalette } from "./shell/CommandPalette";
import { Sidebar, type View } from "./shell/Sidebar";
import type { Theme } from "./theme";

interface Props {
  project: Project;
  route: Route;
  theme: Theme;
  narrow: boolean;
  searching: boolean;
  onSearching: (open: boolean) => void;
}

/** One Project: its model (written by Claude Code), shown as the architecture, the code, and Claude's activity. */
export function ProjectPage({ project, route, theme, narrow, searching, onSearching }: Props) {
  const state = useProjectModel(project.id);
  const view: View =
    route.node === ARCHITECTURE_VIEW || route.node === MAP_VIEW || route.node === ACTIVITY_VIEW ? route.node : APPLICATION;

  return (
    <ModelContext.Provider value={state}>
      <div className={`grid min-h-0 flex-1 ${narrow ? "grid-cols-[minmax(0,1fr)] grid-rows-[auto_minmax(0,1fr)]" : "grid-cols-[248px_minmax(0,1fr)]"}`}>
        <Sidebar project={project} route={route} view={view} model={state?.model ?? null} narrow={narrow} />
        <main className="min-h-0 min-w-0">
          {(view === ARCHITECTURE_VIEW || view === MAP_VIEW) && (
            <ArchitectureView project={project} route={route} theme={theme} narrow={narrow} />
          )}
          {view === ACTIVITY_VIEW && <ActivityView project={project} />}
          {view === APPLICATION && (
            <ProjectView
              key={`${project.id}|${route.node}|${route.expand}|${route.select ?? ""}`} // a new view starts with nothing selected
              project={project}
              route={route}
              theme={theme}
              narrow={narrow}
            />
          )}
        </main>
      </div>
      <CommandPalette projectId={project.id} model={state?.model ?? null} open={searching} onOpenChange={onSearching} />
    </ModelContext.Provider>
  );
}
