import { createContext, useContext, useEffect, useState } from "react";
import { readSessionHeader } from "./api";

// What the engine reports while it watches the Project: files that just changed, cards rewritten.
export interface Live {
  connected: boolean;
  revision: number; // bumps on every event: views read their data again
  changed: Map<string, number>; // path -> when it changed (ms), kept a few minutes
  rewriting: number;
  lastEvent: number | null;
}

const KEEP_MS = 5 * 60_000;
const RETRY_MS = 3000;
const IDLE: Live = { connected: false, revision: 0, changed: new Map(), rewriting: 0, lastEvent: null };

export const LiveContext = createContext<Live>(IDLE);
export const useLive = () => useContext(LiveContext);

type Event = { type: "indexed"; changed: string[]; count: number } | { type: "rewriting"; count: number } | { type: "card"; key: string };

/** Follows `/events` with fetch (an EventSource could not send the session header). */
export function useLiveEvents(projectId: string | null): Live {
  const [live, setLive] = useState<Live>(IDLE);

  useEffect(() => {
    if (!projectId) return;
    let stopped = false;
    let controller = new AbortController();
    setLive(IDLE);

    const apply = (event: Event) =>
      setLive((previous) => {
        const now = Date.now();
        const changed = new Map([...previous.changed].filter(([, at]) => now - at < KEEP_MS));
        let rewriting = previous.rewriting;
        if (event.type === "indexed") event.changed.forEach((path) => changed.set(path, now));
        if (event.type === "rewriting") rewriting += event.count;
        if (event.type === "card") rewriting = Math.max(0, rewriting - 1);
        return { connected: true, revision: previous.revision + 1, changed, rewriting, lastEvent: now };
      });

    const connect = async () => {
      while (!stopped) {
        try {
          const response = await fetch(`/v1/projects/${encodeURIComponent(projectId)}/events`, {
            headers: readSessionHeader(),
            credentials: "omit",
            signal: controller.signal,
          });
          if (!response.ok || !response.body) throw new Error(String(response.status));
          setLive((previous) => ({ ...previous, connected: true }));
          const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
          let buffer = "";
          for (;;) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += value;
            const blocks = buffer.split("\n\n");
            buffer = blocks.pop() ?? "";
            for (const block of blocks) {
              const data = block.split("\n").find((line) => line.startsWith("data: "));
              if (data) apply(JSON.parse(data.slice(6)) as Event);
            }
          }
        } catch {
          // engine restarted or network hiccup: try again below
        }
        if (stopped) return;
        setLive((previous) => ({ ...previous, connected: false }));
        await new Promise((resolve) => setTimeout(resolve, RETRY_MS));
        controller = new AbortController();
      }
    };
    connect();
    return () => {
      stopped = true;
      controller.abort();
    };
  }, [projectId]);

  return live;
}

/** Was this path (or anything under it, for a folder) changed in the last minutes? */
export function changedUnder(live: Live, path: string | null | undefined): boolean {
  if (path === null || path === undefined) return false;
  for (const changed of live.changed.keys()) {
    if (path === "" || changed === path || changed.startsWith(`${path}/`)) return true;
  }
  return false;
}
