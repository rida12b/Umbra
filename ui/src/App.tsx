import { useEffect, useState } from "react";
import { ApiError, api, whenSignedOut, type Project } from "./api";
import { LiveContext, useLiveEvents } from "./live";
import { useNewVersion } from "./newVersion";
import { ProjectPage } from "./ProjectPage";
import { takeLoginCode, useRoute } from "./route";
import { TopBar } from "./shell/TopBar";
import { useTheme } from "./theme";
import { Command, StateMessage } from "./ui";

type Projects = { list: Project[] } | { error: ApiError } | null;
const NARROW = "(max-width: 860px)";

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
  const [searching, setSearching] = useState(false);
  const outdated = useNewVersion();

  useEffect(() => {
    whenSignedOut(() => setProjects({ error: new ApiError(401, "signed out") }));
    sessionReady
      .then(() => api.projects())
      .then((list) => setProjects({ list }))
      .catch((error: ApiError) => setProjects({ error }));
  }, []);

  const project =
    projects && "list" in projects ? projects.list.find((p) => p.id === route.projectId) : undefined;
  const live = useLiveEvents(project?.id ?? null);

  return (
    <LiveContext.Provider value={live}>
      <div className="flex h-full flex-col">
        {outdated && (
          <div role="status" className="flex items-center justify-center gap-3 bg-lamp px-4 py-2 text-[14px] font-medium text-on-lamp">
            Une nouvelle version d'Umbra est prête.
            <button type="button" className="rounded-md bg-on-lamp px-3 py-1 text-lamp" onClick={() => window.location.reload()}>
              Recharger
            </button>
          </div>
        )}
        <TopBar project={project} theme={theme} onToggleTheme={toggleTheme} onSearch={() => setSearching(true)} />
        {projects === null && <StateMessage>Connexion au moteur local…</StateMessage>}
        {projects && "error" in projects && <ConnectionProblem error={projects.error} />}
        {projects && "list" in projects && !route.projectId && <ProjectList projects={projects.list} />}
        {projects && "list" in projects && route.projectId && !project && (
          <StateMessage title="Projet inconnu">
            <p className="font-mono text-[13px]">{route.projectId}</p>
            <a className="mt-3 inline-block text-ink underline underline-offset-[3px]" href="#/">
              Voir tous les projets
            </a>
          </StateMessage>
        )}
        {project && (
          <ProjectPage
            key={project.id}
            project={project}
            route={route}
            theme={theme}
            narrow={narrow}
            searching={searching}
            onSearching={setSearching}
          />
        )}
      </div>
    </LiveContext.Provider>
  );
}

function ConnectionProblem({ error }: { error: ApiError }) {
  if (error.needsLogin)
    return (
      <StateMessage title="Connectez-vous depuis votre terminal">
        <p>Cette page a besoin d'un lien à usage unique donné par le moteur. Dans un terminal :</p>
        <Command>umbra-engine open</Command>
        <p className="text-[13px] text-faint">Le lien marche une fois et expire après 2 minutes. Votre jeton d'API ne passe jamais dans une adresse.</p>
      </StateMessage>
    );
  return (
    <StateMessage title="Le moteur ne répond pas">
      <p className="text-danger">{error.message}</p>
      <p className="mt-2">Lancez-le avec :</p>
      <Command>umbra-engine serve</Command>
    </StateMessage>
  );
}

function ProjectList({ projects }: { projects: Project[] }) {
  if (projects.length === 0)
    return (
      <StateMessage title="Aucun projet pour l'instant">
        <p>Enregistrez et indexez un dossier depuis un terminal :</p>
        <Command>umbra-engine add C:\chemin\vers\le\projet{"\n"}umbra-engine index C:\chemin\vers\le\projet</Command>
        <p className="text-[13px] text-faint">Puis rechargez cette page.</p>
      </StateMessage>
    );
  return (
    <section className="mx-auto w-full max-w-3xl px-4 py-10">
      <h1 className="mb-4 text-[19px] font-semibold tracking-[-0.01em]">Projets</h1>
      <ul className="divide-y divide-line-soft border-y border-line-soft">
        {projects.map((project) => (
          <li key={project.id}>
            <a href={`#/p/${encodeURIComponent(project.id)}`} className="block px-1 py-3 hover:bg-raised">
              <span className="block font-medium text-ink">{project.name}</span>
              <span className="block truncate font-mono text-[12px] text-faint">{project.root}</span>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
