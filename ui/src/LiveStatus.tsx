import { useEffect, useState } from "react";
import { useLive } from "./live";

/** "En direct · main.py modifié il y a 12 s": Umbra follows the code as it changes. */
export function LiveStatus() {
  const live = useLive();
  const [, tick] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => tick((n) => n + 1), 5000);
    return () => window.clearInterval(timer);
  }, []);

  const recent = [...live.changed].sort((a, b) => b[1] - a[1]);
  const last = recent[0];
  const detail = [
    last && `${last[0].split("/").pop()}${recent.length > 1 ? ` (+${recent.length - 1})` : ""} modifié il y a ${ago(last[1])}`,
    live.rewriting > 0 && `${live.rewriting} explication(s) en mise à jour`,
  ].filter(Boolean);
  return (
    <span
      className="flex min-w-0 items-center gap-2 text-[13px] text-muted"
      title="Umbra relit le projet à chaque modification"
    >
      <span
        className={`size-[7px] shrink-0 rounded-full ${live.connected ? "bg-ok shadow-[0_0_0_3px_color-mix(in_srgb,var(--u-ok)_22%,transparent)]" : "bg-faint"}`}
      />
      <span className="shrink-0 max-sm:sr-only">{live.connected ? "Suivi en direct" : "Hors ligne"}</span>
      {detail.length > 0 && <span className="hidden truncate text-faint lg:inline">{detail.join(", ")}</span>}
    </span>
  );
}

function ago(at: number): string {
  const seconds = Math.max(0, Math.round((Date.now() - at) / 1000));
  return seconds < 60 ? `${seconds} s` : `${Math.round(seconds / 60)} min`;
}
