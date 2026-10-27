import { Moon, Sun } from "lucide-react";
import type { Project } from "../api";
import { ACTIVITY_VIEW, MAP_VIEW, navigate } from "../route";
import type { Theme } from "../theme";

interface Props {
  project: Project | undefined;
  activity: boolean; // which view of the Project is open
  inside: string | null; // the box whose inside is shown (Level 1): « Vue d'ensemble › Serveur »
  card: string | null; // the part or file whose card is open (Level 2): « … › Serveur › items.py »
  box: string | null; // the box of `inside`: its crumb goes back to it when a card is open
  theme: Theme;
  onToggleTheme: () => void;
}

/** Umbra, where you are, Claude's activity and the theme (mock: `.top` of prototype.html). */
export function TopBar({ project, activity, inside, card, box, theme, onToggleTheme }: Props) {
  const open = (node: string) => project && navigate({ projectId: project.id, node });
  const crumb = "rounded-md px-1.5 py-1 hover:bg-raised hover:text-ink";
  return (
    <header className="flex h-12 flex-none items-center gap-3.5 border-b border-line bg-panel px-5">
      <a href="#/" className="flex shrink-0 items-center gap-2 text-[15px] font-bold tracking-[0.2px] text-ink">
        <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
          <rect x="1.5" y="5" width="6" height="10" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
          <rect x="12.5" y="5" width="6" height="10" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
          <path d="M7.5 10h5" stroke="currentColor" strokeWidth="1.6" />
        </svg>
        Umbra
      </a>
      {project && (
        <nav className={`flex min-w-0 items-center gap-1.5 whitespace-nowrap text-[14px] text-muted ${activity || inside ? "" : "max-sm:hidden"}`} aria-label="Où vous êtes">
          {activity || inside ? (
            <>
              <button type="button" className={crumb} onClick={() => open(MAP_VIEW)}>
                Vue d'ensemble
              </button>
              <span className="text-faint">›</span>
              {card && inside ? (
                <>
                  <button type="button" className={`${crumb} max-sm:hidden`} onClick={() => project && navigate({ projectId: project.id, node: MAP_VIEW, box })}>
                    {inside}
                  </button>
                  <span className="text-faint max-sm:hidden">›</span>
                  <span aria-current="page" className="truncate px-1.5 py-1 font-semibold text-ink">
                    {card}
                  </span>
                </>
              ) : (
                <span aria-current="page" className="truncate px-1.5 py-1 font-semibold text-ink">
                  {inside ?? "Activité de Claude"}
                </span>
              )}
            </>
          ) : (
            <span aria-current="page" className="px-1.5 py-1 font-semibold text-ink">
              Vue d'ensemble
            </span>
          )}
        </nav>
      )}
      <div className="ml-auto flex items-center gap-2">
        {project && !activity && (
          <button type="button" className={`whitespace-nowrap rounded-md px-2 py-1 text-[13px] text-muted hover:bg-raised hover:text-ink ${inside ? "max-sm:hidden" : ""}`} onClick={() => open(ACTIVITY_VIEW)}>
            Activité de Claude
          </button>
        )}
        <button
          type="button"
          onClick={onToggleTheme}
          className="rounded-md p-1.5 text-muted hover:bg-raised hover:text-ink"
          aria-label={theme === "dark" ? "Passer au thème clair" : "Passer au thème sombre"}
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </div>
    </header>
  );
}
