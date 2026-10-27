import { useEffect, useState } from "react";
import { ApiError, api, type PartCard } from "../../api";
import { useLive } from "../../live";

export type CardState =
  | { kind: "closed" }
  | { kind: "loading" }
  | { kind: "none" } // the part or file is not drawn there any more (404): the card closes
  | { kind: "failed"; message: string }
  | { kind: "ready"; card: PartCard };

/** The card of one part (or one file of it), read again when the engine says the project changed. */
export function useCard(projectId: string, box: string, part: string | null, file: string | null): CardState {
  const { revision } = useLive();
  const key = part ? `${box}\n${part}\n${file ?? ""}` : "";
  const [state, setState] = useState<{ key: string; state: CardState }>({ key: "", state: { kind: "closed" } });

  useEffect(() => {
    if (!part) return;
    let current = true;
    const done = (next: CardState) => current && setState((shown) => (next.kind === "failed" && shown.key === key && shown.state.kind === "ready" ? shown : { key, state: next }));
    api.card(projectId, box, part, file).then(
      (card) => done({ kind: "ready", card }),
      (error: ApiError) => {
        if (error.needsLogin) return;
        done(error.status === 404 ? { kind: "none" } : { kind: "failed", message: error.message });
      },
    );
    return () => {
      current = false;
    };
  }, [projectId, box, part, file, key, revision]);

  if (!part) return { kind: "closed" };
  return state.key === key ? state.state : { kind: "loading" };
}
