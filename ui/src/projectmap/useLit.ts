import { useCallback, useEffect, useState } from "react";
import { api, type Highlight } from "../api";
import { useLive } from "../live";
import { copyText, nextStep } from "./lit";

/** What is lit on the map, shared by the whole map and the inside of a box: a question from Claude Code
 * (`show`, #104) or an action's traced path (#107). « effacer » hides it here at once and on every tab. */
export interface Lit {
  highlight: Highlight | null;
  step: number | null; // the step ← → are on; an action's path starts on 1, a question on none
  move: (forward: boolean) => void;
  clear: () => void;
  copy: () => void; // « copier pour Claude »
}

export function useLit(projectId: string): Lit {
  const shown = useLive().highlight;
  const [hidden, setHidden] = useState<number | null>(null);
  const highlight = shown && shown.serial !== hidden ? shown : null;
  const [step, setStep] = useState<number | null>(null);
  const serial = highlight?.serial;
  const kind = highlight?.kind;
  useEffect(() => setStep(kind === "path" ? 1 : null), [serial, kind]);
  const count = highlight?.steps.length ?? 0;
  const move = useCallback((forward: boolean) => setStep((n) => nextStep(n, count, forward)), [count]);
  const clear = useCallback(() => {
    if (serial === undefined) return;
    setHidden(serial);
    api.clearShown(projectId).catch(() => undefined); // the other tabs go back to the plain map too
  }, [projectId, serial]);
  const copy = useCallback(() => highlight && copyToClipboard(copyText(highlight)), [highlight]);

  useEffect(() => {
    if (!count) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "ArrowRight" || event.key === "ArrowLeft") move(event.key === "ArrowRight");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [count, move]);

  return { highlight, step, move, clear, copy };
}

/** The clipboard API, or the old way when the page is not allowed to use it. */
function copyToClipboard(text: string): void {
  const fallback = () => {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  };
  if (navigator.clipboard) navigator.clipboard.writeText(text).catch(fallback);
  else fallback();
}
