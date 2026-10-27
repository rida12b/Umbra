import { useEffect, useState } from "react";
import { HelpCard } from "./MapCards";

/** The band under the map on every level: « Ce qu'on peut faire (N) », « ? » with how to read it, and one toast. */
export function MapFooter({ actions, toast, onToast }: { actions: number; toast: string | null; onToast: (text: string | null) => void }) {
  const [help, setHelp] = useState(false);

  useEffect(() => {
    if (!help) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.stopImmediatePropagation(); // Esc closes the card first, before it closes anything on the map
      setHelp(false);
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [help]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => onToast(null), 2600);
    return () => window.clearTimeout(timer);
  }, [toast, onToast]);

  return (
    <>
      <footer className="pm-bottom">
        {actions > 0 && (
          <button type="button" className="pm-btn" onClick={() => onToast("La liste arrive dans la prochaine version d'Umbra.")}>
            Ce qu'on peut faire <b>({actions})</b>
          </button>
        )}
        <button type="button" className="pm-btn round" aria-label="Aide : comment lire la carte" aria-expanded={help} onClick={() => setHelp((open) => !open)}>
          ?
        </button>
      </footer>
      {help && <HelpCard />}
      {toast && (
        <div role="status" className="pm-toast">
          {toast}
        </div>
      )}
    </>
  );
}
