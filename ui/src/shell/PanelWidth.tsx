import { useEffect, useSyncExternalStore, type RefObject } from "react";

// The side panel's width (#92): the reader drags the edge between the map and the panel, or moves it with ←/→;
// a double-click puts it back. Remembered in this browser, shared by the explorer and the code level.

export const PANEL_DEFAULT = 400;
const PANEL_MIN = 320;
const MAX_SHARE = 0.7; // the map always keeps at least 30 % of the width
const STEP = 32; // one arrow key press
const KEY = "umbra-panel-width";

const clamp = (w: number) => Math.round(Math.min(Math.max(w, PANEL_MIN), Math.max(PANEL_MIN, window.innerWidth * MAX_SHARE)));
function read(): number {
  try {
    const saved = Number(window.localStorage.getItem(KEY));
    return saved ? clamp(saved) : PANEL_DEFAULT;
  } catch {
    return PANEL_DEFAULT; // storage blocked: the default, every time
  }
}

let width = typeof window === "undefined" ? PANEL_DEFAULT : read();
const listeners = new Set<() => void>();
function setWidth(next: number, save: boolean) {
  width = clamp(next);
  listeners.forEach((l) => l());
  if (!save) return;
  try {
    window.localStorage.setItem(KEY, String(width));
  } catch {
    // not remembered: it still works for this visit
  }
}
const subscribe = (l: () => void) => {
  listeners.add(l);
  return () => listeners.delete(l);
};

/** The panel's width in pixels; a smaller window pulls it back inside its bounds. */
export function usePanelWidth(): number {
  useEffect(() => {
    const fit = () => setWidth(width, false);
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, []);
  return useSyncExternalStore(subscribe, () => width, () => PANEL_DEFAULT);
}

/** The draggable edge, placed on the panel's left border inside `grid` (a relative container). */
export function PanelResizer({ grid }: { grid: RefObject<HTMLElement | null> }) {
  const current = usePanelWidth();
  const fromPointer = (x: number) => {
    const box = grid.current?.getBoundingClientRect();
    if (box) setWidth(box.right - x, false);
  };
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Largeur du panneau d'explication (← → pour la changer, double-clic pour revenir)"
      aria-valuenow={current}
      aria-valuemin={PANEL_MIN}
      aria-valuemax={clamp(Number.MAX_SAFE_INTEGER)}
      tabIndex={0}
      title="Glisser pour élargir le panneau · double-clic : taille normale"
      className="group absolute top-0 bottom-0 z-20 w-2.5 -translate-x-1/2 cursor-col-resize touch-none outline-none"
      style={{ right: current }}
      onPointerDown={(event) => {
        event.currentTarget.setPointerCapture(event.pointerId);
        event.preventDefault();
      }}
      onPointerMove={(event) => {
        if (event.currentTarget.hasPointerCapture(event.pointerId)) fromPointer(event.clientX);
      }}
      onPointerUp={(event) => {
        event.currentTarget.releasePointerCapture(event.pointerId);
        setWidth(width, true);
      }}
      onDoubleClick={() => setWidth(PANEL_DEFAULT, true)}
      onKeyDown={(event) => {
        if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
        event.preventDefault();
        event.stopPropagation(); // the arrows step a journey elsewhere on the page
        setWidth(width + (event.key === "ArrowLeft" ? STEP : -STEP), true);
      }}
    >
      {/* A thin line that shows on hover and on keyboard focus. */}
      <span className="absolute inset-y-0 left-1/2 w-0.5 -translate-x-1/2 bg-transparent transition-colors group-hover:bg-fl-service group-focus-visible:bg-fl-service" />
    </div>
  );
}
