import { useCallback, useEffect, useState } from "react";
import { api, type Card, type Explanation } from "../api";
import { useLive } from "../live";

const POLL_MS = 2500;

/**
 * The deeper card of one element (a zoom beyond the Project model). It is read if it exists and
 * written only on `request()`, then followed until ready. Live mode rewrites out-of-date cards.
 */
export function useExplanation(projectId: string, node: string): [Explanation<Card> | null, () => void] {
  const [explanation, setExplanation] = useState<Explanation<Card> | null>(null);
  const [requested, setRequested] = useState(0);
  const { revision } = useLive(); // the code changed or a card was rewritten: read again

  useEffect(() => {
    let current = true;
    let timer: number | undefined;
    const follow = (found: Explanation<Card>) => {
      if (!current) return;
      setExplanation(found);
      if (found.state === "queued" || found.state === "working") {
        timer = window.setTimeout(() => api.explanation(projectId, node).then(follow, fail), POLL_MS);
      }
    };
    const fail = (error: Error) =>
      current &&
      setExplanation({ state: "error", card: null, producer: null, created_at: null, message: error.message });
    (requested > 0 ? api.explain(projectId, node) : api.explanation(projectId, node)).then(follow, fail);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [projectId, node, revision, requested]);

  const request = useCallback(() => setRequested((n) => n + 1), []);
  return [explanation, request];
}
