import type { CSSProperties } from "react";
import type { ProjectModel } from "../api";

/** The project's settings card (V18): on the floor, under a room and in the phone list. A click opens its plate (#79). */
export function ProjectSettingsCard({ model, selected, onOpen, className = "", style }: {
  model: ProjectModel; selected: boolean; onOpen: () => void; className?: string; style?: CSSProperties;
}) {
  const settings = model.reglages_projet ?? [];
  if (settings.length === 0) return null;
  const files = [...new Set(settings.map((r) => r.fichier).filter(Boolean))].join(", ");
  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        onOpen();
      }}
      aria-pressed={selected}
      className={`flex flex-col justify-center rounded-lg border border-dashed border-fl-code bg-panel px-2.5 py-1.5 text-left hover:bg-raised ${selected ? "ring-2 ring-fl-service" : ""} ${className}`}
      style={style}
    >
      <span className="text-[14px] font-semibold text-ink">Réglages du projet</span>
      <span className="line-clamp-2 text-[12px] text-muted" title={files}>
        {settings.length} réglage{settings.length > 1 ? "s" : ""} · {files}
      </span>
    </button>
  );
}
