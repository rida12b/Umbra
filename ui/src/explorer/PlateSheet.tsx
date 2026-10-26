import { useLayoutEffect, useRef, type ReactNode } from "react";

/** On a phone a plate is a bottom sheet over the list (#79): focus moves into it, « Fermer » is at hand, and on close
 * the keyboard is back on the item it was opened from. Échap closes it too (the explorer's Esc clears the selection). */
export function PlateSheet({ from, onClose, children }: { from: string; onClose: () => void; children: ReactNode }) {
  const close = useRef<HTMLButtonElement>(null);
  useLayoutEffect(() => {
    close.current?.focus();
    return () => document.querySelector<HTMLElement>(`[data-narrow-id="${CSS.escape(from)}"] button`)?.focus({ preventScroll: true });
  }, [from]);
  return (
    <div className="fixed inset-x-0 bottom-0 z-30 flex max-h-[78dvh] flex-col rounded-t-2xl border-t border-line bg-panel shadow-2xl" role="dialog" aria-modal="true" aria-label="Fiche">
      <div className="flex shrink-0 justify-end px-3 pt-2">
        <button ref={close} type="button" onClick={onClose} className="rounded-lg border border-line px-3 py-1.5 text-[14px]" aria-label="Fermer la fiche">
          Fermer
        </button>
      </div>
      <div className="min-h-0 overflow-x-hidden overflow-y-auto pb-[env(safe-area-inset-bottom,0px)]">{children}</div>
    </div>
  );
}
