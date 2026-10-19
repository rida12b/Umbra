import { useEffect, useState } from "react";
import { api, type Explanation } from "../api";

const POLL_MS = 2500;

/**
 * The card of one element. Asks Claude Code to write it when there is none, or when the code
 * changed since; then follows the background work until the card is there.
 */
export function useExplanation(projectId: string, node: string): Explanation | null {
  const [explanation, setExplanation] = useState<Explanation | null>(null);

  useEffect(() => {
    let current = true;
    let timer: number | undefined;
    setExplanation(null);

    const follow = (found: Explanation) => {
      if (!current) return;
      setExplanation(found);
      if (found.state === "queued" || found.state === "working") {
        timer = window.setTimeout(() => api.explanation(projectId, node).then(follow, fail), POLL_MS);
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
      .then(follow, fail);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [projectId, node]);

  return explanation;
}
