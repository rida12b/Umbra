import { useEffect, useState } from "react";
import { useLive } from "./live";

/** "Live · app/main.py changed 12 s ago · 2 explanations being rewritten". */
export function LiveStatus() {
  const live = useLive();
  const [, tick] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => tick((n) => n + 1), 5000);
    return () => window.clearInterval(timer);
  }, []);

  const recent = [...live.changed].sort((a, b) => b[1] - a[1]);
  const last = recent[0];
  return (
    <span className={`live${live.connected ? " on" : ""}`} title="Umbra relit le projet à chaque modification">
      <span className="live-dot" />
      {live.connected ? "En direct" : "Hors ligne"}
      {last && (
        <span>
          · {last[0].split("/").pop()}
          {recent.length > 1 ? ` (+${recent.length - 1})` : ""} modifié il y a {ago(last[1])}
        </span>
      )}
      {live.rewriting > 0 && <span>· {live.rewriting} explication(s) en mise à jour</span>}
    </span>
  );
}

function ago(at: number): string {
  const seconds = Math.max(0, Math.round((Date.now() - at) / 1000));
  return seconds < 60 ? `${seconds} s` : `${Math.round(seconds / 60)} min`;
}
