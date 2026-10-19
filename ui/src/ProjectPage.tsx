import type { Project } from "./api";
import { ArchitectureView } from "./arch/ArchitectureView";
import { JourneysView, journeyHighlight } from "./arch/JourneysView";
import { LiveStatus } from "./LiveStatus";
import { SearchBox } from "./SearchBox";
import { ModelContext, useProjectModel } from "./model";
import { ProjectView } from "./ProjectView";
import { ActivityView } from "./ActivityView";
import { ACTIVITY_VIEW, APPLICATION, ARCHITECTURE_VIEW, JOURNEYS_VIEW, navigate, type Route } from "./route";
import type { Theme } from "./theme";

const TABS = [
  { node: ARCHITECTURE_VIEW, label: "Architecture" },
  { node: JOURNEYS_VIEW, label: "Parcours" },
  { node: APPLICATION, label: "Code" },
  { node: ACTIVITY_VIEW, label: "Activité de Claude" },
];

/** One Project: its model (written by Claude Code) shared by three views of the same understanding. */
export function ProjectPage({ project, route, theme, narrow }: { project: Project; route: Route; theme: Theme; narrow: boolean }) {
  const model = useProjectModel(project.id);
  const view = [ARCHITECTURE_VIEW, JOURNEYS_VIEW, ACTIVITY_VIEW].includes(route.node) ? route.node : APPLICATION;
  const highlight =
    view === ARCHITECTURE_VIEW && route.journey && model?.model ? journeyHighlight(model.model, route.journey) : null;

  return (
    <ModelContext.Provider value={model}>
      <nav className="tabs" aria-label="Views">
        {TABS.map((tab) => (
          <button
            key={tab.node}
            className={view === tab.node ? "tab active" : "tab"}
            onClick={() => navigate({ projectId: project.id, node: tab.node, expand: false })}
          >
            {tab.label}
          </button>
        ))}
        <SearchBox projectId={project.id} />
        <LiveStatus />
      </nav>
      {view === ARCHITECTURE_VIEW && (
        <ArchitectureView key={project.id} project={project} theme={theme} narrow={narrow} highlight={highlight} />
      )}
      {view === JOURNEYS_VIEW && <JourneysView project={project} route={route} />}
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
    </ModelContext.Provider>
  );
}
