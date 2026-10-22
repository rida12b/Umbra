import { Moon, Search, Sun } from "lucide-react";
import type { Project } from "../api";
import { LiveStatus } from "../LiveStatus";
import { ACTIVITY_VIEW, ARCHITECTURE_VIEW, navigate } from "../route";
import type { Theme } from "../theme";

interface Props {
  project: Project | undefined;
  activity: boolean; // which tab is open
  theme: Theme;
  onToggleTheme: () => void;
  onSearch: () => void;
}

/** Umbra, the Project, the search, whether Umbra follows the code live, and the theme. */
export function TopBar({ project, activity, theme, onToggleTheme, onSearch }: Props) {
  return (
    <header className="flex h-12 items-center gap-4 border-b border-line-soft px-4">
      <a href="#/" className="flex shrink-0 items-center gap-2.5 font-semibold tracking-[-0.01em] text-ink">
        <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
          <circle cx="9" cy="9" r="7.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
          <path d="M9 1.5a7.5 7.5 0 0 1 0 15z" fill="currentColor" />
        </svg>
        Umbra
      </a>
      {project && <span className="-ml-2 truncate text-muted">/ {project.name}</span>}
      {project && (
        <nav className="flex gap-1" aria-label="Vues">
          {[
            { node: ARCHITECTURE_VIEW, label: "Carte", on: !activity },
            { node: ACTIVITY_VIEW, label: "Activité de Claude", on: activity },
          ].map((tab) => (
            <button
              key={tab.node}
              type="button"
              aria-current={tab.on ? "page" : undefined}
              className={`rounded-md px-3 py-1 text-[14px] ${tab.on ? "bg-raised text-ink" : "text-muted hover:text-ink"}`}
              onClick={() => navigate({ projectId: project.id, node: tab.node, expand: false })}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      )}
      {project && (
        <button
          type="button"
          onClick={onSearch}
          className="ml-2 hidden h-[30px] max-w-[460px] flex-1 items-center gap-2 rounded-md border border-line bg-panel px-2.5 text-faint hover:text-muted sm:flex"
        >
          <Search size={14} aria-hidden="true" />
          <span className="truncate">Chercher un chemin, une pièce, un fichier</span>
          <kbd className="ml-auto rounded border border-line px-1.5 font-mono text-[11px] text-muted">Ctrl K</kbd>
        </button>
      )}
      <div className="ml-auto flex items-center gap-3">
        {project && (
          <button type="button" onClick={onSearch} className="text-muted sm:hidden" aria-label="Chercher">
            <Search size={16} />
          </button>
        )}
        {project && <LiveStatus />}
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
