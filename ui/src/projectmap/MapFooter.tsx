import { useEffect, useState } from "react";
import { HelpCard } from "./MapCards";

interface Props {
  actions: number;
  open: boolean; // the « Ce qu'on peut faire » panel is open: its button hides, as in the mock
  onActions: () => void;
  toast: string | null;
  onToast: (text: string | null) => void;
}

/** The band under the map on every level: « Ce qu'on peut faire (N) », « ? » with how to read it, and one toast. */
export function MapFooter({ actions, open, onActions, toast, onToast }: Props) {
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
        {actions > 0 && !open && (
          <button type="button" className="pm-btn" aria-expanded={false} onClick={onActions}>
            Ce qu'on peut faire <b>({actions})</b>
          </button>
        )}
        <button type="button" className="pm-btn round" aria-label="Aide : comment lire la carte" aria-expanded={help} onClick={() => setHelp((shown) => !shown)}>
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
