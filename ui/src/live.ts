import { createContext, useContext, useEffect, useState } from "react";
import { readSessionHeader, signedOut } from "./api";

// What the engine reports while it watches the Project: every event (a re-read, Claude's activity) bumps
// `revision`, and views read their data again.
export interface Live {
  connected: boolean;
  revision: number;
}

const RETRY_MS = 3000;
const IDLE: Live = { connected: false, revision: 0 };

export const LiveContext = createContext<Live>(IDLE);
export const useLive = () => useContext(LiveContext);

/** Follows `/events` with fetch (an EventSource could not send the session header). */
export function useLiveEvents(projectId: string | null): Live {
  const [live, setLive] = useState<Live>(IDLE);

  useEffect(() => {
    if (!projectId) return;
    let stopped = false;
    let controller = new AbortController();
    let lastId: string | null = null; // sent back on reconnect: the engine replays what was missed
    setLive(IDLE);

    const apply = () => setLive((previous) => ({ connected: true, revision: previous.revision + 1 }));

    const connect = async () => {
      while (!stopped) {
        try {
          const since = lastId ? `?since=${lastId}` : "";
          const response = await fetch(`/v1/projects/${encodeURIComponent(projectId)}/events${since}`, {
            headers: readSessionHeader(),
            credentials: "omit",
            signal: controller.signal,
          });
          if (response.status === 401) {
            signedOut(); // the engine restarted: retrying can never succeed, the page asks for a new link
            return;
          }
          if (!response.ok || !response.body) throw new Error(String(response.status));
          // (Re)connected: read everything again once, in case something changed while away.
          setLive((previous) => ({ ...previous, connected: true, revision: previous.revision + 1 }));
          const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
          let buffer = "";
          for (;;) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += value;
            const blocks = buffer.split("\n\n");
            buffer = blocks.pop() ?? "";
            for (const block of blocks) {
              const lines = block.split("\n");
              const id = lines.find((line) => line.startsWith("id: "));
              const data = lines.find((line) => line.startsWith("data: "));
              if (id) lastId = id.slice(4);
              if (data) apply();
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
