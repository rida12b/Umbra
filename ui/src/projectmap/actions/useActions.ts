import { useEffect, useState } from "react";
import { ApiError, api, type ActionList } from "../../api";
import { useLive } from "../../live";

export type ActionsState = { kind: "loading" } | { kind: "failed"; message: string } | { kind: "ready"; list: ActionList };

/** « Ce qu'on peut faire »: read when the panel opens, and again when the engine says the project changed. */
export function useActions(projectId: string, open: boolean): ActionsState {
  const { revision } = useLive();
  const [state, setState] = useState<ActionsState>({ kind: "loading" });

  useEffect(() => {
    if (!open) return;
    let current = true;
    api.actions(projectId).then(
      (list) => current && setState({ kind: "ready", list }),
      (error: ApiError) => current && !error.needsLogin && setState((shown) => (shown.kind === "ready" ? shown : { kind: "failed", message: error.message })),
    );
    return () => {
      current = false;
    };
  }, [projectId, open, revision]);

  return state;
}
