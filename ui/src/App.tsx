import { useEffect, useState } from "react";
import { ApiError, api, type Project } from "./api";
import { ProjectView } from "./ProjectView";
import { takeLoginCode, useRoute } from "./route";
import { useTheme } from "./theme";

type Projects = { list: Project[] } | { error: ApiError } | null;
const NARROW = "(max-width: 720px)";

// Done once per page load, before any API call: a login code works only once.
const sessionReady: Promise<void> = (() => {
  const code = takeLoginCode();
  return code ? api.openSession(code).catch(() => undefined) : Promise.resolve();
})();

function useNarrow(): boolean {
  const [narrow, setNarrow] = useState(() => window.matchMedia(NARROW).matches);
  useEffect(() => {
    const media = window.matchMedia(NARROW);
    const update = () => setNarrow(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return narrow;
}

export function App() {
  const [theme, toggleTheme] = useTheme();
  const route = useRoute();
  const narrow = useNarrow();
  const [projects, setProjects] = useState<Projects>(null);

  useEffect(() => {
    sessionReady
      .then(() => api.projects())
      .then((list) => setProjects({ list }))
      .catch((error: ApiError) => setProjects({ error }));
  }, []);

  const project =
    projects && "list" in projects ? projects.list.find((p) => p.id === route.projectId) : undefined;

  return (
    <div className="app">
      <header className="topbar">
        <a className="brand" href="#/">
          Umbra
        </a>
        {project && <span className="topbar-project">{project.name}</span>}
        <button className="theme-toggle" onClick={toggleTheme} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>
          {theme === "dark" ? "Light" : "Dark"}
        </button>
      </header>
      <main className="main">
        {projects === null && <div className="state">Connecting to the local engine…</div>}
        {projects && "error" in projects && <ConnectionProblem error={projects.error} />}
        {projects && "list" in projects && !route.projectId && <ProjectList projects={projects.list} />}
        {projects && "list" in projects && route.projectId && !project && (
          <div className="state">
            <p>Unknown Project: {route.projectId}</p>
            <a href="#/">All Projects</a>
          </div>
        )}
        {project && (
          <ProjectView
            key={`${project.id}|${route.node}|${route.expand}`} // a new view starts with nothing selected
            project={project}
            route={route}
            theme={theme}
            narrow={narrow}
          />
        )}
      </main>
    </div>
  );
}

function ConnectionProblem({ error }: { error: ApiError }) {
  if (error.needsLogin)
    return (
      <div className="state">
        <h1>Sign in from your terminal</h1>
        <p>This page needs a one-time link from the engine. In a terminal, run:</p>
        <pre className="command">umbra-engine open</pre>
        <p className="muted">The link works once and expires after 2 minutes. Your API token never goes in a URL.</p>
      </div>
    );
  return (
    <div className="state error-text">
      <p>{error.message}</p>
    </div>
  );
}

function ProjectList({ projects }: { projects: Project[] }) {
  if (projects.length === 0)
    return (
      <div className="state">
        <h1>No Project yet</h1>
        <p>Register and index a folder from a terminal:</p>
        <pre className="command">umbra-engine index C:\path\to\your\project</pre>
        <p className="muted">Then reload this page.</p>
      </div>
    );
  return (
    <section className="projects">
      <h1>Projects</h1>
      <ul>
        {projects.map((project) => (
          <li key={project.id}>
            <a href={`#/p/${encodeURIComponent(project.id)}`}>
              <span className="project-name">{project.name}</span>
              <span className="project-root">{project.root}</span>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
