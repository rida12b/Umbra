import type { Project, ProjectModel } from "../api";
import { ACTIVITY_VIEW, APPLICATION, ARCHITECTURE_VIEW, MAP_VIEW, navigate, type Route } from "../route";
import { steps } from "../ui";

export type View = typeof ARCHITECTURE_VIEW | typeof MAP_VIEW | typeof APPLICATION | typeof ACTIVITY_VIEW;

const VIEWS: { node: View; label: string; short: string }[] = [
  { node: ARCHITECTURE_VIEW, label: "Accueil du projet", short: "Accueil" },
  { node: MAP_VIEW, label: "Toutes les pièces", short: "Pièces" },
  { node: APPLICATION, label: "Code", short: "Code" },
  { node: ACTIVITY_VIEW, label: "Activité de Claude", short: "Activité" },
];

interface Props {
  project: Project;
  route: Route;
  view: View;
  model: ProjectModel | null;
  narrow: boolean;
}

/** Where to look (the views) and what to follow (the journeys), always one click away. */
export function Sidebar({ project, route, view, model, narrow }: Props) {
  const openView = (node: View) => navigate({ projectId: project.id, node, expand: false });
  const openJourney = (journey: string) =>
    navigate({ projectId: project.id, node: ARCHITECTURE_VIEW, expand: false, journey, step: 1 });
  const chosen = view === ARCHITECTURE_VIEW ? route.journey : null;
  // « Accueil » is the current page only on the home itself, not on a story or a part.
  const current = (node: View) => view === node && (node !== ARCHITECTURE_VIEW || (!route.journey && !route.select));

  if (narrow)
    return (
      <nav className="flex flex-col gap-2 border-b border-line-soft px-4 py-2.5" aria-label="Vues">
        <div className="flex gap-1 overflow-x-auto [scrollbar-width:none]">
          {VIEWS.map((item) => (
            <button
              key={item.node}
              type="button"
              aria-current={current(item.node) ? "page" : undefined}
              className={`shrink-0 rounded-md px-2.5 py-1 text-[13px] ${view === item.node ? "bg-raised text-ink" : "text-muted"}`}
              onClick={() => openView(item.node)}
            >
              {item.short}
            </button>
          ))}
        </div>
        {model && model.parcours.length > 0 && (
          <select
            aria-label="Lire une histoire"
            className="w-full min-w-0 truncate rounded-md border border-line bg-panel px-2 py-1.5 text-[13px] text-ink"
            value={chosen ?? ""}
            onChange={(event) => (event.target.value ? openJourney(event.target.value) : openView(ARCHITECTURE_VIEW))}
          >
            <option value="">Accueil du projet</option>
            {model.parcours.map((journey) => (
              <option key={journey.id} value={journey.id}>
                {journey.nom}
              </option>
            ))}
          </select>
        )}
      </nav>
    );

  return (
    <aside className="flex min-h-0 flex-col gap-6 overflow-y-auto border-r border-line-soft px-2.5 py-3.5">
      <nav className="flex flex-col gap-0.5" aria-label="Vues">
        {VIEWS.map((item) => (
          <button
            key={item.node}
            type="button"
            aria-current={current(item.node) ? "page" : undefined}
            className={`rounded-md px-2.5 py-1.5 text-left ${view === item.node ? "bg-raised text-ink" : "text-muted hover:text-ink"}`}
            onClick={() => openView(item.node)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {model && model.parcours.length > 0 && (
        <section aria-labelledby="journeys-title">
          <h2 id="journeys-title" className="px-2.5 pb-1.5 text-[12px] font-medium text-faint">
            Comment ça marche
          </h2>
          <ul className="flex flex-col gap-0.5">
            {model.parcours.map((journey) => {
              const on = journey.id === chosen;
              const manual = journey.etapes.filter((step) => step.manuel).length;
              return (
                <li key={journey.id}>
                  <button
                    type="button"
                    aria-current={on ? "true" : undefined}
                    className={`w-full rounded-md px-2.5 py-1.5 text-left leading-snug ${
                      on ? "bg-lamp-soft text-ink shadow-[inset_2px_0_0_var(--u-lamp)]" : "text-muted hover:text-ink"
                    }`}
                    onClick={() => openJourney(journey.id)}
                  >
                    {journey.nom}
                    <span className="mt-0.5 block text-[12px] text-faint">
                      {steps(journey.etapes.length)}{manual > 0 ? `, dont ${manual} à faire vous-même` : ""}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      )}

    </aside>
  );
}
