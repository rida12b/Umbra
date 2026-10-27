import { ActivityView } from "./ActivityView";
import type { Project } from "./api";
import { ProjectMap } from "./projectmap/ProjectMap";
import { ACTIVITY_VIEW, type Route } from "./route";

/** One Project: its map (ADR-0007), or what Claude Code did in it. */
export function ProjectPage({ project, route }: { project: Project; route: Route }) {
  return <main className="min-h-0 flex-1">{route.node === ACTIVITY_VIEW ? <ActivityView project={project} /> : <ProjectMap project={project} />}</main>;
}
