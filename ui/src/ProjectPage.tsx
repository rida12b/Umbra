import { ActivityView } from "./ActivityView";
import type { Project } from "./api";
import { ProjectMap, type Crumbs } from "./projectmap/ProjectMap";
import { ACTIVITY_VIEW, type Route } from "./route";

/** One Project: its map (ADR-0007, Level 0 or inside a box), or what Claude Code did in it. */
export function ProjectPage({ project, route, onCrumb }: { project: Project; route: Route; onCrumb: (crumbs: Crumbs) => void }) {
  const card = route.part ? { part: route.part, file: route.file ?? null } : null;
  return (
    <main className="min-h-0 flex-1">
      {route.node === ACTIVITY_VIEW ? <ActivityView project={project} /> : <ProjectMap project={project} box={route.box ?? null} card={card} onCrumb={onCrumb} />}
    </main>
  );
}
