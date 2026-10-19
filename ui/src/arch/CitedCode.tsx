import { useState } from "react";
import type { Cited } from "../api";
import { EvidenceItem } from "../panel/EvidenceItem";

/** "file:lines" that opens the guarded excerpt; a citation Umbra could not find is marked as such. */
export function CitedCode({ projectId, cited }: { projectId: string; cited: Cited }) {
  const [open, setOpen] = useState(false);
  if (!cited.fichier) return null;
  const where = cited.lignes ? `${cited.fichier}:${cited.lignes[0]}–${cited.lignes[1]}` : cited.fichier;
  if (!cited.verifie || !cited.lignes) {
    return (
      <span className="cited unverified" title="Umbra n'a pas trouvé ce fichier ou ces lignes">
        {where} (citation non vérifiée)
      </span>
    );
  }
  return (
    <>
      <button className="link-button cited" onClick={() => setOpen(!open)}>
        {open ? "masquer le code" : where}
      </button>
      {open && (
        <EvidenceItem projectId={projectId} source={{ file: cited.fichier, start: cited.lignes[0], end: cited.lignes[1] }} />
      )}
    </>
  );
}
