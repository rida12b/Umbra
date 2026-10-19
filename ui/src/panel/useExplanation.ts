import { useEffect, useState } from "react";
import { api, type Card, type Explanation } from "../api";
import { useLive } from "../live";

const POLL_MS = 2500;

/**
 * The card of one element. Asks Claude Code to write it when there is none, or when the code
 * changed since; then follows the background work until the card is there.
 */
export function useExplanation<T = Card>(projectId: string, node: string): Explanation<T> | null {
  const [explanation, setExplanation] = useState<Explanation<T> | null>(null);
  const { revision } = useLive(); // the code changed or a card was rewritten: read again

  useEffect(() => {
    let current = true;
    let timer: number | undefined;

    const follow = (found: Explanation<T>) => {
      if (!current) return;
      setExplanation(found);
      if (found.state === "queued" || found.state === "working") {
        const poll = () => api.explanation(projectId, node) as Promise<Explanation<T>>;
        timer = window.setTimeout(() => poll().then(follow, fail), POLL_MS);
      }
    };
    const fail = (error: Error) =>
      current &&
      setExplanation({ state: "error", card: null, producer: null, created_at: null, message: error.message });

    api
      .explanation(projectId, node)
      .then((found) =>
        found.state === "missing" || found.state === "stale" ? api.explain(projectId, node) : found,
      )
      .then((found) => follow(found as Explanation<T>), fail);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [projectId, node, revision]);

  return explanation;
}
