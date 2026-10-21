import { useMemo } from "react";
import type { ProjectModel } from "../api";
import type { Theme } from "../theme";
import { ArchCanvas } from "./ArchCanvas";

interface Props {
  model: ProjectModel;
  theme: Theme;
  onBlock: (id: string) => void;
}

/** Every part of the project and how they work together, at a readable size (scroll to see the rest). */
export function MapPage({ model, theme, onBlock }: Props) {
  const [drawn, apart] = useMemo(() => {
    const linked = new Set(model.flux.flatMap((flow) => [flow.de, flow.vers]));
    return [model.blocs.filter((block) => linked.has(block.id)), model.blocs.filter((block) => !linked.has(block.id))];
  }, [model]);
  return (
    <div className="flex h-full flex-col">
      <header className="flex flex-wrap items-baseline gap-x-6 gap-y-1 border-b border-line-soft px-6 py-3">
        <h1 className="text-[18px] font-semibold">Toutes les pièces</h1>
        <p className="text-[14px] text-muted">Cliquez une pièce pour son détail. Glissez pour vous déplacer.</p>
        {model.blocs.some((block) => block.importance === "ancien") && (
          <p className="text-[14px] text-faint">En pointillé : l'ancien outil, en cours de remplacement.</p>
        )}
      </header>
      <div className="map-surface relative min-h-0 flex-1">
        <ArchCanvas model={model} theme={theme} blocks={drawn} onPickBlock={onBlock} />
      </div>
      {apart.length > 0 && (
        <footer className="border-t border-line-soft px-6 py-3 text-[14px] text-muted">
          Sans lien avec les autres :{" "}
          {apart.map((block, index) => (
            <span key={block.id}>
              {index > 0 && ", "}
              <button type="button" className="text-ink underline decoration-line underline-offset-[3px]" onClick={() => onBlock(block.id)}>
                {block.nom}
              </button>
            </span>
          ))}
        </footer>
      )}
    </div>
  );
}
