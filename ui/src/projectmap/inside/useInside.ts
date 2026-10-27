import { useEffect, useState } from "react";
import { ApiError, api, type InsideMap } from "../../api";
import { useLive } from "../../live";

export type InsideState =
  | { kind: "loading" }
  | { kind: "none" } // the box has no inside (404): the map stays on Level 0
  | { kind: "failed"; message: string }
  | { kind: "ready"; inside: InsideMap };

/** Level 1 of one box, read again when the engine says the project changed. */
export function useInside(projectId: string, box: string): InsideState {
  const { revision } = useLive();
  const [state, setState] = useState<InsideState>({ kind: "loading" });

  useEffect(() => {
    let current = true;
    api.inside(projectId, box).then(
      (inside) => current && setState({ kind: "ready", inside }),
      (error: ApiError) => {
        if (!current || error.needsLogin) return;
        const next: InsideState = error.status === 404 ? { kind: "none" } : { kind: "failed", message: error.message };
        setState((shown) => (shown.kind === "ready" && shown.inside.box === box && next.kind === "failed" ? shown : next));
      },
    );
    return () => {
      current = false;
    };
  }, [projectId, box, revision]);

  return state.kind === "ready" && state.inside.box !== box ? { kind: "loading" } : state;
}
