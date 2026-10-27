import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type SystemMap } from "../api";
import { useLive } from "../live";

export type SystemState =
  | { kind: "loading" }
  | { kind: "reading" } // the engine is reading the project (just added, never read): the map comes next
  | { kind: "failed"; message: string } // the read failed: « Réessayer » reads it again at once
  | { kind: "offline"; message: string }
  | { kind: "ready"; map: SystemMap };

const READING_POLL_MS = 3000; // besides the live « indexed » event, in case the stream is down

/** The Level 0 map of a Project, read again when the engine says the project changed. */
export function useSystem(projectId: string): [SystemState, () => void] {
  const { revision } = useLive();
  const [state, setState] = useState<SystemState>({ kind: "loading" });
  const [attempt, setAttempt] = useState({ n: 0, retry: false });

  useEffect(() => {
    let current = true;
    api.system(projectId, attempt.retry).then(
      (map) => current && setState({ kind: "ready", map }),
      (error: ApiError) => {
        if (!current || error.needsLogin) return; // signed out: the app asks for a new link
        const next: SystemState =
          error.status === 409
            ? { kind: "reading" }
            : error.status === 0
              ? { kind: "offline", message: error.message }
              : { kind: "failed", message: error.message };
        // A map already shown stays while the engine re-reads the project or restarts.
        setState((shown) => (shown.kind === "ready" && next.kind !== "failed" ? shown : next));
      },
    );
    return () => {
      current = false;
    };
  }, [projectId, revision, attempt]);

  useEffect(() => {
    if (state.kind !== "reading") return;
    const timer = window.setTimeout(() => setAttempt((a) => ({ n: a.n + 1, retry: false })), READING_POLL_MS);
    return () => window.clearTimeout(timer);
  }, [state]);

  const retry = useCallback(() => {
    setState({ kind: "reading" });
    setAttempt((a) => ({ n: a.n + 1, retry: true }));
  }, []);
  return [state, retry];
}
