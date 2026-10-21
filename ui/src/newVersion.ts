import { useEffect, useState } from "react";

const CHECK_MS = 60_000;
const ENTRY = /\/assets\/index-[\w-]+\.js/;

/** The built entry script this page runs (`/assets/index-<hash>.js`); none in development. */
function runningEntry(): string | null {
  for (const script of document.querySelectorAll<HTMLScriptElement>('script[type="module"]')) {
    const match = ENTRY.exec(script.src);
    if (match) return match[0];
  }
  return null;
}

/**
 * True once the engine serves another build than the one this page runs. The app never reloads by
 * itself (moving between pages only changes the URL fragment), so an open tab could show an old
 * version for days: the page checks every minute and offers to reload.
 */
export function useNewVersion(): boolean {
  const [outdated, setOutdated] = useState(false);
  useEffect(() => {
    const running = runningEntry();
    if (!running) return;
    const check = () => {
      fetch("/", { cache: "no-store", credentials: "omit" })
        .then((response) => response.text())
        .then((page) => {
          const served = ENTRY.exec(page)?.[0];
          if (served && served !== running) setOutdated(true);
        })
        .catch(() => undefined); // engine stopped: the live status already says so
    };
    const timer = window.setInterval(check, CHECK_MS);
    return () => window.clearInterval(timer);
  }, []);
  return outdated;
}
