import { ActivityView } from "./ActivityView";
import type { Project } from "./api";
import { ProjectMap } from "./projectmap/ProjectMap";
import { ACTIVITY_VIEW, type Route } from "./route";

/** One Project: its map (ADR-0007, Level 0 or inside a box), or what Claude Code did in it. */
export function ProjectPage({ project, route, onCrumb }: { project: Project; route: Route; onCrumb: (title: string | null) => void }) {
  return (
    <main className="min-h-0 flex-1">
      {route.node === ACTIVITY_VIEW ? <ActivityView project={project} /> : <ProjectMap project={project} box={route.box ?? null} onCrumb={onCrumb} />}
    </main>
  );
}
