import { useState } from "react";
import type { Cited } from "../api";
import { EvidenceItem } from "../panel/EvidenceItem";

/** "file:lines" that opens the guarded excerpt; a citation Umbra could not find is marked as such. */
export function CitedCode({ projectId, cited, open: openAtFirst = false }: { projectId: string; cited: Cited; open?: boolean }) {
  const [open, setOpen] = useState(openAtFirst);
  if (!cited.fichier) return null;
  const where = cited.lignes ? `${cited.fichier}:${cited.lignes[0]}–${cited.lignes[1]}` : cited.fichier;
  if (!cited.verifie || !cited.lignes) {
    return (
      <span className="mt-1 block font-mono text-[12px] text-faint" title="Umbra n'a pas trouvé ce fichier ou ces lignes">
        {where} · citation non vérifiée
      </span>
    );
  }
  if (open)
    return (
      <EvidenceItem
        projectId={projectId}
        source={{ file: cited.fichier, start: cited.lignes[0], end: cited.lignes[1] }}
        onClose={() => setOpen(false)}
      />
    );
  return (
    <button
      type="button"
      className="mt-1 block max-w-full truncate font-mono text-[12px] text-faint hover:text-ink"
      onClick={(event) => {
        event.stopPropagation();
        setOpen(true);
      }}
    >
      {where}
    </button>
  );
}
